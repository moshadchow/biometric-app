export type AccountRiskLevel = "high" | "low";

export type SignatureMethod =
  | "wet"
  | "electronic"
  | "digital"
  | "upload"
  | "pin";

export type VerificationMethod =
  | "wet_signature"
  | "electronic_signature"
  | "digital_signature"
  | "uploaded_signature"
  | "pin_authorization";

export type SignatureStatus =
  | "idle"
  | "uploading"
  | "generating"
  | "saving"
  | "saved"
  | "error";

export type SignatureAuditEventType =
  | "method_selected"
  | "capture_status"
  | "upload_status"
  | "pin_generated"
  | "pin_validated"
  | "submission_status";

export type SignatureAuditEventStatus = "info" | "success" | "warning" | "error";

export type SignatureImageSource = "wet" | "electronic" | "upload";

export interface SignatureAuditEvent {
  id: string;
  type: SignatureAuditEventType;
  status: SignatureAuditEventStatus;
  message: string;
  createdAt: string;
}

export interface SignatureImageAsset {
  dataUrl: string;
  mimeType: "image/png" | "image/jpeg";
  width: number;
  height: number;
  source: SignatureImageSource;
  fileName?: string;
  fileSize?: number;
}

export interface DigitalSignatureArtifact {
  token: string;
  digest: string;
  signerName: string;
  generatedAt: string;
  consentText: string;
}

export interface PinAuthorizationArtifact {
  challengeId: string;
  pinHash: string;
  last4: string;
  generatedAt: string;
  validatedAt: string;
}

export interface CustomerReference {
  name?: string;
  idNumber?: string;
}

export interface SignatureMetadata {
  submittedAt: string;
  verificationMethod: VerificationMethod;
  accountRisk: AccountRiskLevel;
  deviceUserAgent: string;
  fileName?: string;
  fileSize?: number;
  width?: number;
  height?: number;
  customerReference?: CustomerReference;
}

export interface StoredSignatureRecord {
  id: string;
  signatureMethod: SignatureMethod;
  verificationMethod: VerificationMethod;
  accountRisk: AccountRiskLevel;
  signatureImage?: SignatureImageAsset;
  digitalSignature?: DigitalSignatureArtifact;
  pinAuthorization?: PinAuthorizationArtifact;
  metadata: SignatureMetadata;
  auditLog: SignatureAuditEvent[];
  integrityHash: string;
}
