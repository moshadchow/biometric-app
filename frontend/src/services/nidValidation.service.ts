import type { DocumentSide } from "@/types";
import type { NIDDetectionResult, NIDFieldMetaMap, NIDFields, ImageQualityResult } from "@/types";
import { meanLuminance } from "@/utils/luminance";
import { laplacianVariance } from "@/utils/laplacianVariance";
import {
  NID_MIN_BRIGHTNESS,
  NID_MAX_BRIGHTNESS,
  NID_MIN_SHARPNESS,
} from "./nidFileValidation.service";

function stripOCRNoise(raw: string | undefined): string {
  if (!raw) return "";
  const trimmed = raw.trim().replace(/[\s|]+$/g, "").trim();
  const words = trimmed.split(/\s+/);
  const firstBengali = words.findIndex((word) => /[\u0980-\u09FF]/u.test(word));
  return firstBengali >= 0 ? words.slice(firstBengali).join(" ") : trimmed;
}

function normalizeOCRText(raw: string | undefined): string {
  if (!raw) return "";
  return raw
    .replace(/\r\n?/g, "\n")
    .replace(/[|¦]/g, ":")
    .replace(/[“”„‟"]/g, "\"")
    .replace(/[‘’`]/g, "'")
    .replace(/[;,]+/g, ":")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function cleanInlineValue(raw: string | undefined): string {
  if (!raw) return "";
  return stripOCRNoise(
    raw
      .replace(/^[\s:;,.|/-]+/, "")
      .replace(/[\s:;,.|/-]+$/g, "")
      .replace(/\s{2,}/g, " ")
      .trim()
  );
}

function cleanBlockValue(raw: string | undefined): string {
  if (!raw) return "";
  return raw
    .replace(/\r\n?/g, "\n")
    .replace(/^[\s:;,.|/-]+/, "")
    .replace(/[\s:;,.|/-]+$/g, "")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function containsBengali(text: string | undefined): boolean {
  return Boolean(text && /[\u0980-\u09FF]/u.test(text));
}

function truncateAtKnownLabel(value: string): string {
  return cleanInlineValue(
    value.split(
      /(?:\b(?:Name|Father|Mother|Date|DOB|District|Upazila|Address)\b|\u09A8\u09BE\u09AE|\u09AA\u09BF\u09A4\u09BE|\u09AE\u09BE\u09A4\u09BE|\u099C\u09C7\u09B2\u09BE|\u0989\u09AA\u099C\u09C7\u09B2\u09BE|\u09A0\u09BF\u0995\u09BE\u09A8\u09BE|\u09AA\u09CD\u09B0\u09A6\u09BE\u09A8\u0995\u09BE\u09B0\u09C0)/u
    )[0]
  );
}

function isLikelyName(value: string | undefined): boolean {
  if (!value) return false;
  const cleaned = truncateAtKnownLabel(value);
  if (cleaned.length < 3 || cleaned.length > 60 || /\d/.test(cleaned)) return false;
  if (/(?:\bDate\b|\bDOB\b|\bDistrict\b|\bUpazila\b|\bAddress\b|\u099C\u09C7\u09B2\u09BE|\u0989\u09AA\u099C\u09C7\u09B2\u09BE|\u09A0\u09BF\u0995\u09BE\u09A8\u09BE)/iu.test(cleaned)) {
    return false;
  }
  return /[A-Za-z\u0980-\u09FF]/u.test(cleaned);
}

function getSafeNextLine(lines: string[], index: number): string {
  const nextLine = cleanInlineValue(lines[index + 1]);
  if (!nextLine || !isLikelyName(nextLine)) return "";
  if (/(?:\b(?:Father|Mother|Date|DOB|District|Upazila|Address)\b|\u09AA\u09BF\u09A4\u09BE|\u09AE\u09BE\u09A4\u09BE|\u099C\u09C7\u09B2\u09BE|\u0989\u09AA\u099C\u09C7\u09B2\u09BE|\u09A0\u09BF\u0995\u09BE\u09A8\u09BE)/iu.test(nextLine)) {
    return "";
  }
  return nextLine;
}

function collectNameContinuation(lines: string[], index: number, initialValue: string): string {
  const parts = [cleanInlineValue(initialValue)].filter(Boolean);
  for (let offset = 1; offset <= 2; offset += 1) {
    const nextLine = getSafeNextLine(lines, index + offset - 1);
    if (!nextLine) break;
    parts.push(nextLine);
  }
  return cleanInlineValue(parts.join(" "));
}

function extractLabeledField(
  text: string,
  patterns: Array<{ regex: RegExp; source: string }>
): { value: string; meta: NIDFieldMetaMap[keyof NIDFieldMetaMap] } | null {
  const lines = text.split("\n");
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    for (const pattern of patterns) {
      const match = line.match(pattern.regex);
      if (!match) continue;
      const inlineValue = truncateAtKnownLabel(match[1] ?? "");
      const baseValue = cleanInlineValue(inlineValue) || getSafeNextLine(lines, index);
      const value = collectNameContinuation(lines, index, baseValue);
      if (!isLikelyName(value)) continue;
      return {
        value,
        meta: {
          source: pattern.source,
          labelVerified: true,
          matchedText: cleanInlineValue(line),
        },
      };
    }
  }
  return null;
}

function extractPositionalParentNames(text: string): string[] {
  const lines = text.split("\n").map((line) => cleanInlineValue(line));
  const nameLineIndex = lines.findIndex((line) => /(?:\bName\b|\u09A8\u09BE\u09AE)/iu.test(line));
  const dobLineIndex = lines.findIndex((line) => /(?:\bDate\b|\bDOB\b|\u099C\u09A8\u09CD\u09AE)/iu.test(line));
  if (nameLineIndex < 0 || dobLineIndex <= nameLineIndex) return [];

  const candidates = lines
    .slice(nameLineIndex + 1, dobLineIndex)
    .map((line) => line.replace(/[^A-Za-z\u0980-\u09FF\s.'-]/gu, " ").replace(/\s+/g, " ").trim())
    .filter((line) => isLikelyName(line));

  const uniqueCandidates = [...new Set(candidates)];
  return uniqueCandidates.length === 2 ? uniqueCandidates : [];
}

function extractDistrictFromAddressBlock(backText: string): {
  addressRaw?: string;
  district?: string;
  meta?: NIDFieldMetaMap["district"];
} {
  const issuerSplit = backText.split(/\u09AA\u09CD\u09B0\u09A6\u09BE\u09A8\u0995\u09BE\u09B0\u09C0/u)[0] ?? backText;
  const addressMatch = issuerSplit.match(
    /(?:\u09A0\u09BF\u0995\u09BE\u09A8\u09BE|\u0995\u09BE\u09A8\u09BE)\s*[:.]?\s*([\s\S]{10,400})/u
  );
  const addressRaw = cleanBlockValue(addressMatch?.[1] ?? issuerSplit);
  const addressLines = addressRaw
    .split("\n")
    .map((line) => cleanInlineValue(line))
    .filter(Boolean);

  for (const line of addressLines) {
    const districtMatch = line.match(/\u099C\u09C7\u09B2\u09BE\s*[:.]?\s*([\u0980-\u09FF][^\n,.:]{1,40})/u);
    if (districtMatch?.[1]) {
      return {
        addressRaw,
        district: cleanInlineValue(districtMatch[1]),
        meta: {
          source: "district_label",
          labelVerified: true,
          matchedText: line,
        },
      };
    }
  }

  for (const line of addressLines) {
    if (!/[\u09E6-\u09EF0-9]{4,6}/u.test(line)) continue;
    const segments = line
      .split(/[:,]/)
      .map((segment) => cleanInlineValue(segment))
      .filter(Boolean);
    const districtCandidate = segments[segments.length - 1];
    if (containsBengali(districtCandidate) && !/\u0989\u09AA\u099C\u09C7\u09B2\u09BE/u.test(districtCandidate)) {
      return {
        addressRaw,
        district: districtCandidate,
        meta: {
          source: "address_structure",
          labelVerified: false,
          matchedText: line,
        },
      };
    }
  }

  return { addressRaw };
}

interface MarkerDef {
  pattern: RegExp;
  weight: number;
  label: string;
}

const FRONT_MARKERS: MarkerDef[] = [
  { pattern: /\u099C\u09BE\u09A4\u09C0\u09DF\s*\u09AA\u09B0\u09BF\u099A\u09DF\u09AA\u09A4\u09CD\u09B0/u, weight: 30, label: "জাতীয় পরিচয়পত্র" },
  { pattern: /NATIONAL\s+ID\s+CARD/i, weight: 25, label: "NATIONAL ID CARD" },
  { pattern: /\bID\s*NO[\s:]+\d{10,17}/i, weight: 25, label: "ID NO + digits" },
  { pattern: /\d{17}/, weight: 15, label: "17-digit number" },
  { pattern: /Date\s+of\s+Birth\s*:/i, weight: 10, label: "Date of Birth" },
  { pattern: /\u0997\u09A3\u09AA\u09CD\u09B0\u099C\u09BE\u09A4\u09A8\u09CD\u09A4\u09CD\u09B0\u09C0\s*\u09AC\u09BE\u0982\u09B2\u09BE\u09A6\u09C7\u09B6/u, weight: 20, label: "গণপ্রজাতন্ত্রী বাংলাদেশ" },
  { pattern: /People.s\s+Republic\s+of\s+Bangladesh/i, weight: 10, label: "People's Republic of Bangladesh" },
  { pattern: /\u099C\u09A8\u09CD\u09AE\s*\u09A4\u09BE\u09B0\u09BF\u0996/u, weight: 10, label: "জন্ম তারিখ" },
];

const BACK_MARKERS: MarkerDef[] = [
  { pattern: /\u09A0\u09BF\u0995\u09BE\u09A8\u09BE/u, weight: 25, label: "ঠিকানা" },
  { pattern: /\u0989\u09AA\u099C\u09C7\u09B2\u09BE/u, weight: 15, label: "উপজেলা" },
  { pattern: /\u099C\u09C7\u09B2\u09BE/u, weight: 10, label: "জেলা" },
  { pattern: /\u09A1\u09BE\u0995\u0998\u09B0/u, weight: 10, label: "ডাকঘর" },
];

export function detectNIDCard(text: string, side: DocumentSide): NIDDetectionResult {
  const normalizedText = normalizeOCRText(text);
  const markers = side === "front" ? FRONT_MARKERS : BACK_MARKERS;
  const threshold = side === "front" ? 50 : 40;
  let score = 0;
  const matchedMarkers: string[] = [];

  for (const { pattern, weight, label } of markers) {
    if (pattern.test(normalizedText)) {
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

export function extractNIDData(frontText: string, backText?: string): {
  fields: NIDFields;
  fieldMeta: NIDFieldMetaMap;
} {
  const normalizedFrontText = normalizeOCRText(frontText);
  const normalizedBackText = normalizeOCRText(backText);
  const fields: NIDFields = {};
  const fieldMeta: NIDFieldMetaMap = {};

  const idWithLabel = normalizedFrontText.match(
    /(?:ID\s*NO[\s:]*|ID\s*Number[\s:]*)\s*(\d[\d\s]{10,20}\d)/i
  );
  if (idWithLabel?.[1]) {
    fields.idNumber = idWithLabel[1].replace(/\s+/g, "");
  } else {
    const id17 = normalizedFrontText.match(/\b(\d{17})\b/);
    if (id17?.[1]) {
      fields.idNumber = id17[1];
    } else {
      const id13 = normalizedFrontText.match(/\b(\d{13,16})\b/);
      if (id13?.[1]) fields.idNumber = id13[1];
    }
  }

  const bengaliNameMatch = normalizedFrontText.match(
    /\u09A8\u09BE\u09AE\s*[;:\u0964\u0983]?\s*([\u0980-\u09FF][^\n\r]{2,60})/u
  );
  if (bengaliNameMatch?.[1]) fields.nameBengali = bengaliNameMatch[1].trim();

  const namePatterns: RegExp[] = [
    /(?:Name|Narne|Namne)\s*[;:,|/]\s*((?:Md|Mr|Mrs|Ms|Dr)\.?\s+[A-Z][A-Za-z\s.'-]{2,50})/i,
    /Name\s+([A-Z][A-Za-z\s.'-]{4,50})/,
    /(?:Name|Narne)\s*[;:,.|/\s]\s*([^\n\r]{4,60})/i,
    /((?:Md\.|Mr\.|Mrs\.|Ms\.|Dr\.)\s+(?:[A-Z][A-Za-z.'-]+\s+){1,5}[A-Z][A-Za-z.'-]+)/,
  ];
  for (const pattern of namePatterns) {
    const match = normalizedFrontText.match(pattern);
    if (!match?.[1]) continue;
    const value = match[1].trim();
    if (value.length >= 4 && !containsBengali(value) && /[a-z]/i.test(value)) {
      fields.nameEnglish = value;
      break;
    }
  }

  const positionalNames = extractPositionalParentNames(normalizedFrontText);
  const fatherMatch = extractLabeledField(normalizedFrontText, [
    { regex: /\u09AA\u09BF\u09A4\u09BE(?:\u09B0)?\s+\u09A8\u09BE\u09AE\s*[:.]?\s*(.*)$/u, source: "bengali_label" },
    { regex: /\u09AA\u09BF\u09A4\u09BE\s*[:.]?\s*(.*)$/u, source: "bengali_label" },
    { regex: /Father(?:'?s)?(?:\s+Name)?\s*[:.]?\s*(.*)$/i, source: "english_label" },
  ]);
  if (fatherMatch) {
    fields.fatherName = fatherMatch.value;
    fieldMeta.fatherName = fatherMatch.meta;
  } else if (positionalNames[0]) {
    fields.fatherName = positionalNames[0];
    fieldMeta.fatherName = {
      source: "positional_fallback",
      labelVerified: false,
      matchedText: positionalNames[0],
    };
  }

  const motherMatch = extractLabeledField(normalizedFrontText, [
    { regex: /\u09AE\u09BE\u09A4\u09BE(?:\u09B0)?\s+\u09A8\u09BE\u09AE\s*[:.]?\s*(.*)$/u, source: "bengali_label" },
    { regex: /\u09AE\u09BE\u09A4\u09BE\s*[:.]?\s*(.*)$/u, source: "bengali_label" },
    { regex: /Mother(?:'?s)?(?:\s+Name)?\s*[:.]?\s*(.*)$/i, source: "english_label" },
  ]);
  if (motherMatch) {
    fields.motherName = motherMatch.value;
    fieldMeta.motherName = motherMatch.meta;
  } else if (positionalNames[1]) {
    fields.motherName = positionalNames[1];
    fieldMeta.motherName = {
      source: "positional_fallback",
      labelVerified: false,
      matchedText: positionalNames[1],
    };
  }

  const dobPatterns: RegExp[] = [
    /Date\s+of\s+Birth\s*[;:,]?\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})/i,
    /Date\s+of\s+Birth\s*[;:,]?\s*\n\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})/i,
    /Date\s+of\s+Birth\s*[;:,]?\s*[\n\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})/i,
    /Date\s+of\s+Birth\s*[;:,]?\s*[\n\s]*(\d{4}-\d{2}-\d{2})/i,
    /Date\s+of\s+Bi\w{1,3}h?\s*[;:,]?\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})/i,
    /(?:Date|DOB)\s*[\s\S]{0,30}?(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})/i,
  ];
  for (const pattern of dobPatterns) {
    const match = normalizedFrontText.match(pattern);
    if (match?.[1]) {
      fields.dateOfBirth = match[1].trim();
      break;
    }
  }

  if (normalizedBackText) {
    const districtExtraction = extractDistrictFromAddressBlock(normalizedBackText);
    if (districtExtraction.addressRaw) fields.addressRaw = districtExtraction.addressRaw;
    if (districtExtraction.district) {
      fields.district = districtExtraction.district;
      if (districtExtraction.meta) fieldMeta.district = districtExtraction.meta;
    }

    const upazilaMatch = normalizedBackText.match(
      /[\u09E6-\u09EF]{4,6}\s*,\s*([\u0980-\u09FF][^\n,\u060C\u0964]{2,40})\s*,/u
    );
    if (upazilaMatch?.[1]) {
      fields.upazila = upazilaMatch[1].trim();
    } else {
      const upazilaAscii = normalizedBackText.match(
        /\d{4,6}\s*,\s*([\u0980-\u09FF][^\n,\u060C\u0964]{2,40})\s*,/u
      );
      if (upazilaAscii?.[1]) {
        fields.upazila = upazilaAscii[1].trim();
      } else {
        const upazilaLabel = normalizedBackText.match(
          /\u0989\u09AA\u099C\u09C7\u09B2\u09BE\s*[;:,]?\s*([\u0980-\u09FF][^\n,\u060C\u0964]{1,40})/u
        );
        if (upazilaLabel?.[1]) fields.upazila = upazilaLabel[1].trim();
      }
    }
  }

  fields.__fieldMeta = fieldMeta;
  return { fields, fieldMeta };
}

export function extractNIDFields(frontText: string, backText?: string): NIDFields {
  return extractNIDData(frontText, backText).fields;
}

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
        const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
        ctx.drawImage(img, 0, 0, w, h);

        const cropX = Math.round(w * 0.2);
        const cropY = Math.round(h * 0.2);
        const cropW = Math.round(w * 0.6);
        const cropH = Math.round(h * 0.6);
        const cropData = ctx.getImageData(cropX, cropY, cropW, cropH);
        const brightness = meanLuminance(cropData.data, cropW * cropH);

        const fullData = ctx.getImageData(0, 0, w, h);
        const gray: number[] = new Array(w * h);
        for (let index = 0; index < w * h; index += 1) {
          const r = fullData.data[index * 4];
          const g = fullData.data[index * 4 + 1];
          const b = fullData.data[index * 4 + 2];
          gray[index] = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
        }
        const sharpness = laplacianVariance(gray, w, h);

        const aspectRatio = h > 0 ? w / h : 0;
        const isLandscape = aspectRatio >= 1.3 && aspectRatio <= 2.0;
        const isPortrait = aspectRatio >= 0.5 && aspectRatio <= 0.77;
        const warning =
          !isLandscape && !isPortrait
            ? "Unusual image proportions for an NID card â€” ensure the full card is visible."
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
