export const OCR_MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;

export const OCR_ACCEPTED_MIME_TYPES = [
  "image/jpeg",
  "image/png",
  "application/pdf",
] as const;

export const OCR_ACCEPTED_EXTENSIONS = ".jpg,.jpeg,.png,.pdf";

export const OCR_LANGUAGES = "eng+ben";

export const PDF_RENDER_SCALE = 2.0;

export const OCR_MIN_CONFIDENCE_WARN = 40;

export const OCR_MERGE_SEPARATOR =
  "\n\n════════════════════════════════\n" +
  "            BACK PAGE\n" +
  "════════════════════════════════\n\n";

export const OCR_PAGE_SEPARATOR = "\n\n--- Page {n} ---\n\n";

// Minimum pixel height for image OCR inputs. Images shorter than this are
// upscaled proportionally before OCR so small glyphs (e.g. NID digits) are
// large enough for reliable recognition (~20px per character minimum).
export const OCR_MIN_IMAGE_HEIGHT = 1200;

// DPI hint passed to Tesseract. Overrides the 70dpi default which causes
// Tesseract to misscale character priors and clip long numeric strings.
export const OCR_DPI = "300";
