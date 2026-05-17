import type { SignatureMethod } from "@/types";

export const SIGNATURE_STORAGE_KEY = "biometric-app.signature-records";
export const SIGNATURE_ACCEPTED_MIME_TYPES = ["image/png", "image/jpeg"] as const;
export const SIGNATURE_ACCEPTED_EXTENSIONS = [".png", ".jpg", ".jpeg"] as const;
export const SIGNATURE_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
export const SIGNATURE_MIN_DIMENSION_PX = 40;
export const SIGNATURE_CANVAS_WIDTH = 620;
export const SIGNATURE_CANVAS_HEIGHT = 220;
export const DEFAULT_SIGNATURE_METHOD: SignatureMethod = "wet";
export const DEFAULT_ACCOUNT_RISK = "high";
export const PIN_LENGTH = 6;
export const DIGITAL_SIGNATURE_CONSENT =
  "I confirm this electronic authorization represents my intent to sign and retain this record.";
