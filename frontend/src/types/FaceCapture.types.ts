export type MatchResult = "Success" | "Fail" | null;

export type AppStatus =
  | "loading"
  | "idle"
  | "detecting"
  | "captured"
  | "comparing"
  | "done"
  | "error";

export interface QualityReport {
  brightness: number;
  sharpness: number;
  faceArea: number;
  valid: boolean;
  message: string;
}

export interface FaceMatchPayload {
  result: MatchResult;
  distance: number;
  error?: string;
}

export interface FaceMatchCompletionContext {
  capturedBase64: string;
  referenceImageSrc: string;
  matchThreshold: number;
  quality?: QualityReport | null;
}

export interface FaceCaptureProps {
  referenceImageSrc: string;
  matchThreshold?: number;
  onMatch?: (result: MatchResult, score: number, context?: FaceMatchCompletionContext) => void;
  onProceed?: () => void;
  modelPath?: string;
}
