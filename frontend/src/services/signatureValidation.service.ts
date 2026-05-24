import {
  SIGNATURE_ACCEPTED_MIME_TYPES,
  SIGNATURE_MAX_FILE_SIZE_BYTES,
  SIGNATURE_MIN_DIMENSION_PX,
} from "@/constants/signature";
import { formatFileSize } from "@/services/fileValidation.service";
import type {
  AccountRiskLevel,
  DigitalSignatureArtifact,
  FileValidationError,
  PinAuthorizationArtifact,
  SignatureImageAsset,
  SignatureMethod,
} from "@/types";

interface ValidateSignatureSubmissionInput {
  accountRisk: AccountRiskLevel;
  method: SignatureMethod;
  signatureImage: SignatureImageAsset | null;
  digitalSignature: DigitalSignatureArtifact | null;
  pinAuthorization: PinAuthorizationArtifact | null;
}

async function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Failed to read the uploaded signature file."));
    reader.readAsDataURL(file);
  });
}

async function readImageDimensions(dataUrl: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      resolve({ width: image.naturalWidth, height: image.naturalHeight });
    };
    image.onerror = () => {
      reject(new Error("The uploaded signature image is not readable."));
    };
    image.src = dataUrl;
  });
}

export function methodSatisfiesRisk(
  accountRisk: AccountRiskLevel,
  method: SignatureMethod
): boolean {
  if (accountRisk === "high") {
    return method === "wet" || method === "electronic";
  }

  return true;
}

export function getRiskRequirementMessage(accountRisk: AccountRiskLevel): string {
  if (accountRisk === "high") {
    return "High-risk accounts require a wet or handwritten electronic signature before submission.";
  }

  return "Low-risk accounts may use digital signature, uploaded image, or PIN authorization.";
}

export async function validateAndReadSignatureImage(
  file: File
): Promise<{ asset: SignatureImageAsset | null; error: FileValidationError | null }> {
  if (file.size === 0) {
    return {
      asset: null,
      error: { code: "EMPTY", message: "The uploaded signature file is empty.", fileName: file.name },
    };
  }

  if (file.size > SIGNATURE_MAX_FILE_SIZE_BYTES) {
    return {
      asset: null,
      error: {
        code: "FILE_TOO_LARGE",
        message: `Signature image exceeds the 5 MB limit (${formatFileSize(file.size)}).`,
        fileName: file.name,
      },
    };
  }

  if (!(SIGNATURE_ACCEPTED_MIME_TYPES as readonly string[]).includes(file.type)) {
    return {
      asset: null,
      error: {
        code: "UNSUPPORTED_TYPE",
        message: "Only PNG and JPG signature images are supported.",
        fileName: file.name,
      },
    };
  }

  try {
    const dataUrl = await readFileAsDataUrl(file);
    const { width, height } = await readImageDimensions(dataUrl);

    if (width < SIGNATURE_MIN_DIMENSION_PX || height < SIGNATURE_MIN_DIMENSION_PX) {
      return {
        asset: null,
        error: {
          code: "CORRUPTED",
          message: "Signature image is too small to preserve reliably.",
          fileName: file.name,
        },
      };
    }

    return {
      asset: {
        dataUrl,
        mimeType: file.type as "image/png" | "image/jpeg",
        width,
        height,
        source: "upload",
        fileName: file.name,
        fileSize: file.size,
      },
      error: null,
    };
  } catch (error) {
    return {
      asset: null,
      error: {
        code: "CORRUPTED",
        message:
          error instanceof Error ? error.message : "Unable to read the uploaded signature image.",
        fileName: file.name,
      },
    };
  }
}

export function validateSignatureSubmission(
  input: ValidateSignatureSubmissionInput
): string | null {
  const { accountRisk, method, signatureImage, digitalSignature, pinAuthorization } = input;

  if (accountRisk === "high" && method === "pin") {
    return "PIN-only authorization is not allowed for high-risk accounts.";
  }

  if (!methodSatisfiesRisk(accountRisk, method)) {
    return getRiskRequirementMessage(accountRisk);
  }

  if (method === "wet" || method === "electronic" || method === "upload") {
    if (!signatureImage?.dataUrl) {
      return "A readable signature image must be captured or uploaded before submission.";
    }
  }

  if (method === "digital" && !digitalSignature) {
    return "Generate the digital signature artifact before submitting Step 3.";
  }

  if (method === "pin" && !pinAuthorization) {
    return "Generate and validate the secure PIN before submitting Step 3.";
  }

  return null;
}
