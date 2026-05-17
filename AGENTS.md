# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm run dev        # Start dev server on http://localhost:5173
npm run build      # TypeScript type check + Vite production bundle → dist/
npm run preview    # Serve production build locally
npm run test       # Run Vitest suite (15 tests)
npm run lint       # ESLint
```

To run a single test file:
```bash
npx vitest run src/__tests__/imageConvert.test.ts
```

## Architecture

Pure client-side React + TypeScript app (no backend). Two-step biometric workflow wrapped in a `Stepper`:

1. **Face Verification** — webcam capture compared against a reference image using `@vladmandic/face-api` (WebGL, runs entirely in-browser)
2. **NID OCR Extraction** — Bangladesh NID card front/back upload (JPG/PNG only, no PDF) processed by `tesseract.js` with NID-specific validation and field extraction

Navigation from step 1 → 2 only happens via `onProceed` (wired to "Proceed →" button visible only on a verified match). `onMatch` is logging-only.

### Key abstractions

**Hooks** (`src/hooks/`) own all stateful logic:
- `useCamera` — MediaStream webcam lifecycle
- `useModels` — loads the three face-api models once at mount from `public/models/`
- `useFaceDetection` — per-frame detection loop; emits `QualityReport` (brightness, sharpness, face area)
- `useFaceMatch` — orchestrates the face comparison pipeline; returns `FaceMatchPayload`
- `useOCR` — generic OCR state machine (supports PDF + image); used by `OCRExtractor` component
- `useNIDOCR` — NID-specific OCR state machine; initialises Tesseract on mount with `workerReady` flag to prevent race conditions; front is required, back is optional

**Services** (`src/services/`) are pure functions with no React dependencies:
- `faceApi.service.ts` — face-api.js wrapper: model loading, detection, 128-d descriptor extraction, Euclidean distance
- `imageQuality.service.ts` — brightness (luminance), sharpness (Laplacian variance), face area ratio
- `imageConvert.service.ts` — canvas ↔ base64 ↔ byte array; **mirrors the canvas horizontally** to correct for CSS `scaleX(-1)` on the video element
- `fileValidation.service.ts` — validates MIME type, file size, creates/revokes object URLs
- `pdfRenderer.service.ts` — renders PDF pages to canvas using `pdfjs-dist` v5; uses `{ canvas, viewport }` (not `canvasContext`) in `page.render()`
- `tesseract.service.ts` — singleton Tesseract worker (eng+ben); uses `PSM.AUTO_OSD` (not `SINGLE_BLOCK`) so layout analysis handles the NID card's photo-column + text-column structure; runs `enhanceForOCR` (greyscale + contrast stretch) on every image before recognition; upscales images below `OCR_MIN_IMAGE_HEIGHT`
- `nidFileValidation.service.ts` — NID-specific file validation: JPG/PNG only (no PDF), ≤20 MB; exports `NID_ACCEPTED_MIME_TYPES`, `NID_ACCEPTED_EXTENSIONS`
- `nidValidation.service.ts` — three exports:
  - `detectNIDCard(text, side)` — weighted marker scoring against known Bengali/English NID phrases; threshold 50 (front) / 40 (back); rejects non-NID uploads
  - `extractNIDFields(frontText, backText?)` — regex cascade for all 9 fields; see critical notes below
  - `analyzeCardImageQuality(file)` — brightness (center 60% crop), sharpness (Laplacian), aspect ratio warning

**Components** (`src/components/`):
- `Stepper` — 180px left nav + flex-1 content area; completed steps show ✓ and are clickable; forward nav disabled by default (`allowForwardNav=false`)
- `FaceCapture` — orchestrating component for step 1; sub-components (`MatchResult`, `Base64Output`, `FaceOverlay`, `QualityIndicator`) are display-only
- `OCRExtractor` — generic OCR component (kept for reference); sub-components (`FileUploadZone`, `OCRProgressBar`, `ExtractedTextPanel`, `OCRResultView`) are display-only and shared with NIDExtractor
- `NIDExtractor` — orchestrating component for step 2; uses `useNIDOCR`; shows upload zones, progress, quality warnings, `NIDResultView`
- `NIDResultView` — displays extracted NID fields in structured cards; includes Download .txt and Download JSON buttons

**Constants:**
- `src/constants/thresholds.ts` — face matching tunable: match threshold (default 0.45), quality gates, confidence minimums, JPEG quality. `VITE_MATCH_THRESHOLD` and `VITE_MODEL_PATH` override at build time.
- `src/constants/ocr.ts` — OCR tunable: languages (`eng+ben`), DPI (300), min image height (1200px), confidence warn threshold (40%).

### Face matching safeguards

1. Exactly one face must be detected in both the captured and reference images (rejects 0 or 2+).
2. Detection confidence must meet a minimum score (0.6) before extracting descriptors.
3. Euclidean distance between the two 128-d descriptors is compared against the threshold (default 0.45).

### NID OCR pipeline

1. `useNIDOCR` initialises Tesseract on mount; `workerReady` state prevents the extract button from being clickable before the worker is ready (race condition fix).
2. On file select, `analyzeCardImageQuality` runs a brightness/sharpness/aspect-ratio gate; low-quality images are rejected before OCR.
3. `recognizeFile` in `tesseract.service.ts` converts to canvas, runs `enhanceForOCR` (greyscale + contrast stretch), then passes to Tesseract.
4. After OCR, `detectNIDCard` scores the front text; score < 50 rejects the upload as not an NID card.
5. `extractNIDFields` extracts up to 9 structured fields from the combined front+back text.

### Critical: NID field extraction regex notes

Tesseract OCR on NID card images produces predictable corruption patterns — these are handled in `extractNIDFields`:

- **Bengali visarga `ঃ`** (U+0983) is inside `[ঀ-৿]` range, so separator patterns use `[;:।ঃ]` not `[;:।]`
- **Line-boundary bleed**: capture classes use `[^\n\r]` not `[ঀ-৿\s.'-]` to stop at line end
- **`মাতা`/`পিতা` label corruption**: Tesseract often OCRs the label or leading syllable as ASCII (e.g. `Gi চৌধুরী` instead of `মো: জামী চৌধুরী`). The `\S` anchor (not `[ঀ-৿]`) is used so the capture starts even when the first word is ASCII. `stripOCRNoise()` then strips leading words with zero Bengali characters.
- **`Name` label corruption**: `Narne` / `Namne` are common rn→m OCR errors; pattern 0 covers these
- **`Birth` corruption**: `Bisth` / `Bith` / `Birh` — pattern 5 uses `Bi\w{1,3}h?`
- **DOB label corruption**: `Date of Birth.` (period instead of colon), `Date Ne` — pattern 6 uses a month-name anchor as a label-independent fallback; positional DOB uses loose `\bDate\b`
- **District**: extracted as last Bengali token after the final comma/quote on address lines, before the `প্রদানকারী` landmark — NOT from danda `।` which also appears in the ownership-notice boilerplate at the top of the back side

### Styling

All styles are inline using `const s: Record<string, React.CSSProperties> = { ... }` — no CSS modules or utility classes. Dark theme throughout (#0a0a0a background, #00e5a0 accent, #38b6ff active).

### Models

Pre-trained model weights live in `public/models/` (binary files, not committed as source). Three are required at runtime: `ssd_mobilenetv1`, `face_landmark_68`, `face_recognition`.

### Path alias

`@/` maps to `src/` — use it for all intra-project imports. `"types": ["vite/client"]` in `tsconfig.json` enables `import.meta.env` and `?url` imports.
