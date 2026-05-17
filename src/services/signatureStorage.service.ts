import { PIN_LENGTH, SIGNATURE_STORAGE_KEY } from "@/constants/signature";
import type {
  AccountRiskLevel,
  DigitalSignatureArtifact,
  PinAuthorizationArtifact,
  SignatureAuditEvent,
  SignatureAuditEventStatus,
  SignatureAuditEventType,
  SignatureImageAsset,
  SignatureMethod,
  StoredSignatureRecord,
  VerificationMethod,
} from "@/types";

interface SaveSignatureRecordInput {
  signatureMethod: SignatureMethod;
  verificationMethod: VerificationMethod;
  accountRisk: AccountRiskLevel;
  signatureImage?: SignatureImageAsset;
  digitalSignature?: DigitalSignatureArtifact;
  pinAuthorization?: PinAuthorizationArtifact;
  metadata: StoredSignatureRecord["metadata"];
  auditLog: SignatureAuditEvent[];
}

function getCryptoApi(): Crypto | null {
  if (typeof window !== "undefined" && window.crypto) return window.crypto;
  if (typeof globalThis !== "undefined" && "crypto" in globalThis) {
    return globalThis.crypto as Crypto;
  }
  return null;
}

function createId(prefix: string): string {
  const cryptoApi = getCryptoApi();
  if (cryptoApi?.randomUUID) return `${prefix}-${cryptoApi.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createAuditEvent(
  type: SignatureAuditEventType,
  message: string,
  status: SignatureAuditEventStatus = "info"
): SignatureAuditEvent {
  return {
    id: createId("audit"),
    type,
    status,
    message,
    createdAt: new Date().toISOString(),
  };
}

export async function sha256Hex(value: string): Promise<string> {
  const cryptoApi = getCryptoApi();
  if (!cryptoApi?.subtle) {
    return `fallback-${btoa(unescape(encodeURIComponent(value))).slice(0, 32)}`;
  }

  const bytes = new TextEncoder().encode(value);
  const digest = await cryptoApi.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export function loadSignatureRecords(): StoredSignatureRecord[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.localStorage.getItem(SIGNATURE_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as StoredSignatureRecord[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function saveSignatureRecord(
  input: SaveSignatureRecordInput
): Promise<StoredSignatureRecord> {
  if (typeof window === "undefined") {
    throw new Error("Signature storage requires a browser environment.");
  }

  const recordWithoutHash: Omit<StoredSignatureRecord, "integrityHash"> = {
    id: createId("sig"),
    signatureMethod: input.signatureMethod,
    verificationMethod: input.verificationMethod,
    accountRisk: input.accountRisk,
    signatureImage: input.signatureImage,
    digitalSignature: input.digitalSignature,
    pinAuthorization: input.pinAuthorization,
    metadata: input.metadata,
    auditLog: input.auditLog,
  };

  const integrityHash = await sha256Hex(JSON.stringify(recordWithoutHash));
  const storedRecord: StoredSignatureRecord = {
    ...recordWithoutHash,
    integrityHash,
  };

  const currentRecords = loadSignatureRecords();
  window.localStorage.setItem(
    SIGNATURE_STORAGE_KEY,
    JSON.stringify([storedRecord, ...currentRecords])
  );

  return storedRecord;
}

export async function createDigitalSignatureArtifact(
  signerName: string,
  consentText: string,
  accountRisk: AccountRiskLevel
): Promise<DigitalSignatureArtifact> {
  const generatedAt = new Date().toISOString();
  const digest = await sha256Hex(
    JSON.stringify({
      signerName,
      consentText,
      accountRisk,
      generatedAt,
      userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
    })
  );

  return {
    token: `SIG-${digest.slice(0, 12).toUpperCase()}`,
    digest,
    signerName,
    generatedAt,
    consentText,
  };
}

export function generateSecurePin(): string {
  const cryptoApi = getCryptoApi();
  const randomBytes = new Uint8Array(PIN_LENGTH);

  if (cryptoApi?.getRandomValues) {
    cryptoApi.getRandomValues(randomBytes);
  } else {
    for (let index = 0; index < randomBytes.length; index += 1) {
      randomBytes[index] = Math.floor(Math.random() * 255);
    }
  }

  return Array.from(randomBytes)
    .map((byte) => (byte % 10).toString())
    .join("")
    .slice(0, PIN_LENGTH);
}

export async function createPinAuthorizationArtifact(
  pin: string,
  generatedAt: string,
  validatedAt: string
): Promise<PinAuthorizationArtifact> {
  return {
    challengeId: createId("pin"),
    pinHash: await sha256Hex(pin),
    last4: pin.slice(-4),
    generatedAt,
    validatedAt,
  };
}
