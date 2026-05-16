import {
  OCR_ACCEPTED_MIME_TYPES,
  OCR_MAX_FILE_SIZE_BYTES,
} from "@/constants/ocr";
import type { FileValidationError } from "@/types";

export function validateOCRFile(file: File): FileValidationError | null {
  if (file.size === 0) {
    return { code: "EMPTY", message: "The file is empty.", fileName: file.name };
  }
  if (file.size > OCR_MAX_FILE_SIZE_BYTES) {
    return {
      code: "FILE_TOO_LARGE",
      message: `File exceeds the 20 MB limit (${formatFileSize(file.size)}).`,
      fileName: file.name,
    };
  }
  if (!(OCR_ACCEPTED_MIME_TYPES as readonly string[]).includes(file.type)) {
    return {
      code: "UNSUPPORTED_TYPE",
      message: "Only JPG, PNG, and PDF files are supported.",
      fileName: file.name,
    };
  }
  return null;
}

export function createPreviewUrl(file: File): string {
  return URL.createObjectURL(file);
}

export function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}
