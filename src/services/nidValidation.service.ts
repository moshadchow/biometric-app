import type { DocumentSide } from "@/types";
import type { NIDDetectionResult, NIDFields, ImageQualityResult } from "@/types";
import { meanLuminance } from "@/utils/luminance";
import { laplacianVariance } from "@/utils/laplacianVariance";
import {
  NID_MIN_BRIGHTNESS,
  NID_MAX_BRIGHTNESS,
  NID_MIN_SHARPNESS,
} from "./nidFileValidation.service";

// Strips trailing OCR noise (|, spaces) and leading words that contain zero Bengali
// characters — handles cases like "Gi চৌধুরী" where a Bengali word was misread as ASCII.
function stripOCRNoise(raw: string | undefined): string {
  if (!raw) return '';
  const trimmed = raw.trim().replace(/[\s|]+$/g, '').trim();
  const words = trimmed.split(/\s+/);
  const firstBengali = words.findIndex(w => /[ঀ-৿]/u.test(w));
  return firstBengali >= 0 ? words.slice(firstBengali).join(' ') : trimmed;
}

// ── NID Detection ─────────────────────────────────────────────────────────────

interface MarkerDef {
  pattern: RegExp;
  weight: number;
  label: string;
}

const FRONT_MARKERS: MarkerDef[] = [
  { pattern: /জাতীয়\s*পরিচয়পত্র/u,                   weight: 30, label: "জাতীয় পরিচয়পত্র" },
  { pattern: /NATIONAL\s+ID\s+CARD/i,                   weight: 25, label: "NATIONAL ID CARD" },
  { pattern: /\bID\s*NO[\s:]+\d{10,17}/i,               weight: 25, label: "ID NO + digits" },
  { pattern: /\d{17}/,                                   weight: 15, label: "17-digit number" },
  { pattern: /Date\s+of\s+Birth\s*:/i,                  weight: 10, label: "Date of Birth" },
  { pattern: /গণপ্রজাতন্ত্রী\s*বাংলাদেশ/u,             weight: 20, label: "গণপ্রজাতন্ত্রী বাংলাদেশ" },
  { pattern: /People.s\s+Republic\s+of\s+Bangladesh/i,  weight: 10, label: "People's Republic of Bangladesh" },
  { pattern: /জন্ম\s*তারিখ/u,                           weight: 10, label: "জন্ম তারিখ" },
];

const BACK_MARKERS: MarkerDef[] = [
  { pattern: /ঠিকানা/u,  weight: 25, label: "ঠিকানা" },
  { pattern: /উপজেলা/u,  weight: 15, label: "উপজেলা" },
  { pattern: /জেলা/u,    weight: 10, label: "জেলা" },
  { pattern: /ডাকঘর/u,   weight: 10, label: "ডাকঘর" },
];

export function detectNIDCard(text: string, side: DocumentSide): NIDDetectionResult {
  const markers = side === "front" ? FRONT_MARKERS : BACK_MARKERS;
  const threshold = side === "front" ? 50 : 40;
  let score = 0;
  const matchedMarkers: string[] = [];

  for (const { pattern, weight, label } of markers) {
    if (pattern.test(text)) {
      score += weight;
      matchedMarkers.push(label);
    }
  }

  score = Math.min(score, 100);

  return {
    isNID: score >= threshold,
    score,
    matchedMarkers,
    side,
  };
}

// ── Field Extraction ──────────────────────────────────────────────────────────

export function extractNIDFields(frontText: string, backText?: string): NIDFields {
  const fields: NIDFields = {};

  // ID number — primary: with label, fallback: bare 17-digit, fallback: 13-16 digit
  const idWithLabel = frontText.match(
    /(?:ID\s*NO[\s:]*|ID\s*Number[\s:]*)\s*(\d[\d\s]{10,20}\d)/i
  );
  if (idWithLabel?.[1]) {
    fields.idNumber = idWithLabel[1].replace(/\s+/g, "");
  } else {
    const id17 = frontText.match(/\b(\d{17})\b/);
    if (id17?.[1]) {
      fields.idNumber = id17[1];
    } else {
      const id13 = frontText.match(/\b(\d{13,16})\b/);
      if (id13?.[1]) fields.idNumber = id13[1];
    }
  }

  // Bengali name — match নাম: label; capture stops at line boundary to avoid bleed
  const bengaliNameMatch = frontText.match(
    /নাম\s*[;:।ঃ]?\s*([ঀ-৿][^\n\r]{2,60})/u
  );
  if (bengaliNameMatch?.[1]) fields.nameBengali = bengaliNameMatch[1].trim();

  // English name — cascade: OCR variants of "Name" label, separator variants, structural title fallback
  const namePatterns: RegExp[] = [
    /(?:Name|Narne|Namne)\s*[;:,|/]\s*((?:Md|Mr|Mrs|Ms|Dr)\.?\s+[A-Z][A-Za-z\s.'-]{2,50})/i,
    /Name\s+([A-Z][A-Za-z\s.'-]{4,50})/,
    /(?:Name|Narne)\s*[;:,.|/\s]\s*([^\n\r]{4,60})/i,
    /((?:Md\.|Mr\.|Mrs\.|Ms\.|Dr\.)\s+(?:[A-Z][A-Za-z.'-]+\s+){1,5}[A-Z][A-Za-z.'-]+)/,
  ];
  for (const pat of namePatterns) {
    const m = frontText.match(pat);
    if (m?.[1]) {
      const v = m[1].trim();
      if (v.length >= 4 && !/[ঀ-৿]/u.test(v) && /[a-z]/i.test(v)) {
        fields.nameEnglish = v;
        break;
      }
    }
  }

  // Positional extraction: Bengali content between the নাম line and DOB line
  // Used as fallback when পিতা/মাতা labels are OCR-corrupted beyond recognition
  const _lines = frontText.split('\n');
  const _namLineIdx  = _lines.findIndex(l => /নাম/u.test(l));
  const _nameLineIdx = _namLineIdx >= 0 ? _namLineIdx
    : _lines.findIndex(l => /(?:Name|Narne)\s*[;:,|/]/i.test(l));
  // Loose DOB detection: "Date" anywhere (covers "Date Ne", "Date of Birth", etc.)
  const _dobLineIdx  = _lines.findIndex(l => /\bDate\b/i.test(l));
  // Collect Bengali character sequences from lines between নাম and Date,
  // strip all non-Bengali, join adjacent fragments from consecutive lines
  const _positionalBengali: string[] = (() => {
    if (_nameLineIdx < 0 || _dobLineIdx <= _nameLineIdx) return [];
    const betweenLines = _lines.slice(_nameLineIdx + 1, _dobLineIdx);
    // For each line, extract Bengali chars only; skip lines with zero Bengali chars
    const perLine = betweenLines.map(l => {
      const bengaliOnly = l.replace(/[^ঀ-৿\s]/gu, ' ').replace(/\s+/g, ' ').trim();
      return bengaliOnly;
    }).filter(l => l.length > 0);
    // Group consecutive non-empty fragments into at most 2 slots (father, mother)
    // by splitting on blank gaps or by line count
    const result: string[] = [];
    let current = '';
    for (const frag of perLine) {
      if (current === '') {
        current = frag;
      } else if (result.length === 0) {
        // First group complete when we see a new fragment after collecting one
        result.push(current);
        current = frag;
      } else {
        current += ' ' + frag;
      }
    }
    if (current) result.push(current);
    return result;
  })();

  // Father's name — Bengali label primary, English fallback, positional fallback
  // Capture starts with \S (not [ঀ-৿]) because Tesseract may OCR the first syllable as ASCII
  const fatherBengali = frontText.match(
    /পিতা\s*[;:।ঃ]?\s*(\S[^\n\r]{2,60})/u
  );
  const fatherVal = stripOCRNoise(fatherBengali?.[1]);
  if (fatherVal && (fatherVal.match(/[ঀ-৿]/gu) ?? []).length >= 2) {
    fields.fatherName = fatherVal;
  } else {
    const fatherEnglish = frontText.match(
      /(?:Father(?:'?s)?(?:\s+Name)?|পিতা)\s*[;:,]?\s*([A-Z][A-Za-z\s.'-]{2,40})/i
    );
    if (fatherEnglish?.[1]) fields.fatherName = fatherEnglish[1].trim();
    else if (_positionalBengali[0]) fields.fatherName = _positionalBengali[0];
  }

  // Mother's name — Bengali label primary, English fallback, positional fallback
  // Same \S anchor: handles cases where Tesseract OCRs leading syllable as ASCII (e.g. "Gi চৌধুরী")
  const motherBengali = frontText.match(
    /মাতা\s*[;:।ঃ]?\s*(\S[^\n\r]{2,60})/u
  );
  const motherVal = stripOCRNoise(motherBengali?.[1]);
  if (motherVal && (motherVal.match(/[ঀ-৿]/gu) ?? []).length >= 2) {
    fields.motherName = motherVal;
  } else {
    const motherEnglish = frontText.match(
      /(?:Mother(?:'?s)?(?:\s+Name)?|মাতা)\s*[;:,]?\s*([A-Z][A-Za-z\s.'-]{2,40})/i
    );
    if (motherEnglish?.[1]) fields.motherName = motherEnglish[1].trim();
    else if (_positionalBengali[1]) fields.motherName = _positionalBengali[1];
  }

  // Date of birth — cascade: same-line, cross-line, numeric formats, fuzzy Birth spelling
  const dobPatterns: RegExp[] = [
    /Date\s+of\s+Birth\s*[;:,]?\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})/i,
    /Date\s+of\s+Birth\s*[;:,]?\s*\n\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})/i,
    /Date\s+of\s+Birth\s*[;:,]?\s*[\n\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})/i,
    /Date\s+of\s+Birth\s*[;:,]?\s*[\n\s]*(\d{4}-\d{2}-\d{2})/i,
    /Date\s+of\s+Bi\w{1,3}h?\s*[;:,]?\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})/i,
    /(?:Date|DOB)\s*[\s\S]{0,30}?(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})/i,
  ];
  for (const pat of dobPatterns) {
    const m = frontText.match(pat);
    if (m?.[1]) { fields.dateOfBirth = m[1].trim(); break; }
  }

  // Back side fields
  if (backText) {
    // addressRaw — stop at Bengali landmark lines (issuer/date), not blank lines
    const addrMatch = backText.match(
      /ঠিকানা\s*[;:]?\s*([\s\S]{10,400}?)(?=\s*প্রদানকারী|\s*প্রদানের|$)/u
    );
    if (addrMatch?.[1]) fields.addressRaw = addrMatch[1].trim();

    // district — extracted from the address section only (between ঠিকানা/কানা and প্রদানকারী)
    // Strategy: find the address block, then take the last Bengali token after the last comma/quote
    const issuerIdx = backText.indexOf('প্রদানকারী');
    const addrSectionText = issuerIdx > 0
      ? backText.substring(0, issuerIdx)
      : (addrMatch?.[1] ?? backText);
    // Find the address block start: ঠিকানা or OCR variant কানা
    const addrBlockStart = addrSectionText.search(/(?:ঠিকানা|কানা)\s*[;:]/u);
    const addrBlockText = addrBlockStart >= 0
      ? addrSectionText.substring(addrBlockStart)
      : addrSectionText;
    // Explicit জেলা: label first
    const districtLabel = addrBlockText.match(/জেলা\s*[;:,]?\s*([ঀ-৿][^\n,،।]{1,40})/u);
    if (districtLabel?.[1]) {
      fields.district = districtLabel[1].trim();
    } else {
      // Last Bengali token after a comma or quote on any address line
      const commaMatches = [...addrBlockText.matchAll(/[,,’’"’]\s*[‘"’]?\s*([ঀ-৿][ঀ-৿\s]{0,20}[ঀ-৿])\s*(?:\n|$)/gu)];
      if (commaMatches.length > 0) {
        fields.district = commaMatches[commaMatches.length - 1][1].trim();
      } else {
        // Fallback: last Bengali word sequence before প্রদানকারী
        const allBengaliTokens = [...addrBlockText.matchAll(/([ঀ-৿]{2,}(?:\s[ঀ-৿]{2,}){0,2})/gu)];
        if (allBengaliTokens.length > 0) {
          fields.district = allBengaliTokens[allBengaliTokens.length - 1][1].trim();
        }
      }
    }

    // upazila — 2nd token after postal code in address line (no explicit উপজেলা: label)
    const upazilaMatch = backText.match(
      /[০-৯]{4,6}\s*,\s*([ঀ-৿][^\n,،।]{2,40})\s*,/u
    );
    if (upazilaMatch?.[1]) {
      fields.upazila = upazilaMatch[1].trim();
    } else {
      // OCR may render Bengali postal digits as ASCII
      const upazilaAscii = backText.match(
        /\d{4,6}\s*,\s*([ঀ-৿][^\n,،।]{2,40})\s*,/u
      );
      if (upazilaAscii?.[1]) {
        fields.upazila = upazilaAscii[1].trim();
      } else {
        const upazilaLabel = backText.match(/উপজেলা\s*[;:,]?\s*([ঀ-৿][^\n,،।]{1,40})/u);
        if (upazilaLabel?.[1]) fields.upazila = upazilaLabel[1].trim();
      }
    }
  }

  return fields;
}

// ── Image Quality Gate ────────────────────────────────────────────────────────

export function analyzeCardImageQuality(file: File): Promise<ImageQualityResult> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();

    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve({
        valid: false,
        brightness: 0,
        sharpness: 0,
        aspectRatio: 0,
        reason: "Could not load image for quality analysis.",
      });
    };

    img.onload = () => {
      URL.revokeObjectURL(url);
      try {
        const MAX_W = 800;
        const scale = img.naturalWidth > MAX_W ? MAX_W / img.naturalWidth : 1;
        const w = Math.round(img.naturalWidth * scale);
        const h = Math.round(img.naturalHeight * scale);

        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d")!;
        ctx.drawImage(img, 0, 0, w, h);

        // Center 60% crop for brightness (avoids dark card borders)
        const cropX = Math.round(w * 0.2);
        const cropY = Math.round(h * 0.2);
        const cropW = Math.round(w * 0.6);
        const cropH = Math.round(h * 0.6);
        const cropData = ctx.getImageData(cropX, cropY, cropW, cropH);
        const brightness = meanLuminance(cropData.data, cropW * cropH);

        // Sharpness on full image
        const fullData = ctx.getImageData(0, 0, w, h);
        const gray: number[] = new Array(w * h);
        for (let i = 0; i < w * h; i++) {
          const r = fullData.data[i * 4];
          const g = fullData.data[i * 4 + 1];
          const b = fullData.data[i * 4 + 2];
          gray[i] = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
        }
        const sharpness = laplacianVariance(gray, w, h);

        const aspectRatio = h > 0 ? w / h : 0;
        const isLandscape = aspectRatio >= 1.3 && aspectRatio <= 2.0;
        const isPortrait = aspectRatio >= 0.5 && aspectRatio <= 0.77;
        const warning =
          !isLandscape && !isPortrait
            ? "Unusual image proportions for an NID card — ensure the full card is visible."
            : undefined;

        if (brightness < NID_MIN_BRIGHTNESS) {
          resolve({
            valid: false,
            brightness,
            sharpness,
            aspectRatio,
            reason: "Image is too dark for reliable text recognition. Please take the photo in good lighting.",
          });
          return;
        }

        if (brightness > NID_MAX_BRIGHTNESS) {
          resolve({
            valid: false,
            brightness,
            sharpness,
            aspectRatio,
            reason: "Image is overexposed. Please reduce glare and avoid direct flash.",
          });
          return;
        }

        if (sharpness < NID_MIN_SHARPNESS) {
          resolve({
            valid: false,
            brightness,
            sharpness,
            aspectRatio,
            reason: "Image appears blurry. Hold the camera steady and ensure the card is in focus.",
          });
          return;
        }

        resolve({ valid: true, brightness, sharpness, aspectRatio, warning });
      } catch {
        resolve({
          valid: false,
          brightness: 0,
          sharpness: 0,
          aspectRatio: 0,
          reason: "Quality analysis failed.",
        });
      }
    };

    img.src = url;
  });
}
