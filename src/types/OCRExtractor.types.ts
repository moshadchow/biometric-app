export type OCRStatus = "idle" | "uploading" | "processing" | "done" | "error";

export type DocumentSide = "front" | "back";

export interface UploadedFile {
  side: DocumentSide;
  file: File;
  previewUrl: string;
  mimeType: "image/jpeg" | "image/png" | "application/pdf";
  pageCount?: number;
}

export interface OCRProgressEvent {
  side: DocumentSide;
  progress: number;
  statusText: string;
}

export interface OCRPageResult {
  pageNumber: number;
  text: string;
  confidence: number;
}

export interface OCRSideResult {
  side: DocumentSide;
  pages: OCRPageResult[];
  combinedText: string;
  averageConfidence: number;
  processingTimeMs: number;
}

export interface OCRExtractorResult {
  front: OCRSideResult;
  back?: OCRSideResult;
  mergedText: string;
  completedAt: string;
}

export interface OCRExtractorProps {
  onComplete?: (result: OCRExtractorResult) => void;
  supportedLanguages?: string[];
}

export interface FileValidationError {
  code: "UNSUPPORTED_TYPE" | "FILE_TOO_LARGE" | "CORRUPTED" | "EMPTY";
  message: string;
  fileName: string;
}
