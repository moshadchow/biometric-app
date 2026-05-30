import type { DocumentSide, OCRSideResult } from "@/types";

export interface NIDDetectionResult {
  isNID: boolean;
  score: number;
  matchedMarkers: string[];
  side: DocumentSide;
}

export type NIDValidationErrorCode =
  | "UNSUPPORTED_TYPE"
  | "FILE_TOO_LARGE"
  | "LOW_QUALITY";

export interface NIDValidationFailure {
  code: NIDValidationErrorCode;
  message: string;
  fileName: string;
}

export interface ImageQualityResult {
  valid: boolean;
  brightness: number;
  sharpness: number;
  aspectRatio: number;
  reason?: string;
  warning?: string;
}

export interface NIDFields {
  idNumber?: string;
  nameEnglish?: string;
  nameBengali?: string;
  fatherName?: string;
  motherName?: string;
  dateOfBirth?: string;
  addressRaw?: string;
  district?: string;
  upazila?: string;
}

export interface NIDExtractorResult {
  front: OCRSideResult;
  back?: OCRSideResult;
  mergedText: string;
  completedAt: string;
  fields: NIDFields;
  frontDetection: NIDDetectionResult;
  backDetection?: NIDDetectionResult;
}

export interface NIDCompletionContext {
  frontFile?: File | null;
  backFile?: File | null;
}
