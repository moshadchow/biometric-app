import type { NIDValidationFailure } from "@/types";

export const NID_ACCEPTED_MIME_TYPES = ["image/jpeg", "image/png"] as const;
export const NID_ACCEPTED_EXTENSIONS = ".jpg,.jpeg,.png";
export const NID_MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;
export const NID_DETECTION_THRESHOLD = 50;
export const NID_BACK_DETECTION_THRESHOLD = 40;
export const NID_MIN_BRIGHTNESS = 40;
export const NID_MAX_BRIGHTNESS = 230;
export const NID_MIN_SHARPNESS = 15;

export function validateNIDFile(file: File): NIDValidationFailure | null {
  if (file.size === 0) {
    return {
      code: "UNSUPPORTED_TYPE",
      message: "The file appears to be empty.",
      fileName: file.name,
    };
  }

  if (file.size > NID_MAX_FILE_SIZE_BYTES) {
    const mb = (file.size / (1024 * 1024)).toFixed(1);
    return {
      code: "FILE_TOO_LARGE",
      message: `File exceeds the 20 MB limit (${mb} MB).`,
      fileName: file.name,
    };
  }

  if (!(NID_ACCEPTED_MIME_TYPES as readonly string[]).includes(file.type)) {
    if (file.type === "application/pdf") {
      return {
        code: "UNSUPPORTED_TYPE",
        message:
          "Only JPG and PNG images are accepted. Bangladesh NID cards are photo IDs — PDFs are not supported.",
        fileName: file.name,
      };
    }
    return {
      code: "UNSUPPORTED_TYPE",
      message: "Only JPG and PNG photo files are accepted for NID card scanning.",
      fileName: file.name,
    };
  }

  return null;
}
