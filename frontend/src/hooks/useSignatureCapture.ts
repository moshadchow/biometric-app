import { useCallback, useMemo, useState } from "react";
import {
  DEFAULT_ACCOUNT_RISK,
  DEFAULT_SIGNATURE_METHOD,
  DIGITAL_SIGNATURE_CONSENT,
} from "@/constants/signature";
import {
  createAuditEvent,
  createDigitalSignatureArtifact,
  createPinAuthorizationArtifact,
  generateSecurePin,
  saveSignatureRecord,
} from "@/services/signatureStorage.service";
import {
  getRiskRequirementMessage,
  methodSatisfiesRisk,
  validateAndReadSignatureImage,
  validateSignatureSubmission,
} from "@/services/signatureValidation.service";
import type {
  AccountRiskLevel,
  CustomerReference,
  DigitalSignatureArtifact,
  PinAuthorizationArtifact,
  SignatureAuditEvent,
  SignatureImageAsset,
  SignatureMethod,
  SignatureStatus,
  StoredSignatureRecord,
  VerificationMethod,
} from "@/types";

interface UseSignatureCaptureOptions {
  customerReference?: CustomerReference;
  onComplete?: (record: StoredSignatureRecord) => void;
}

export interface UseSignatureCaptureReturn {
  status: SignatureStatus;
  accountRisk: AccountRiskLevel;
  selectedMethod: SignatureMethod;
  signatureImage: SignatureImageAsset | null;
  digitalSignature: DigitalSignatureArtifact | null;
  pinAuthorization: PinAuthorizationArtifact | null;
  generatedPin: string;
  pinEntry: string;
  signerName: string;
  consentAccepted: boolean;
  auditLog: SignatureAuditEvent[];
  errorMsg: string;
  successMsg: string;
  isSelectedMethodEligible: boolean;
  requirementText: string;
  storedRecord: StoredSignatureRecord | null;
  handleRiskChange: (risk: AccountRiskLevel) => void;
  handleMethodChange: (method: SignatureMethod) => void;
  handleCanvasSave: (asset: Omit<SignatureImageAsset, "source">) => void;
  handleClearSignatureImage: () => void;
  handleUploadSignature: (file: File) => Promise<void>;
  handleSignerNameChange: (value: string) => void;
  handleConsentChange: (accepted: boolean) => void;
  handleGenerateDigitalSignature: () => Promise<void>;
  handleGeneratePin: () => Promise<void>;
  handlePinEntryChange: (value: string) => void;
  handleValidatePin: () => Promise<void>;
  handleSubmit: () => Promise<void>;
}

function getVerificationMethod(method: SignatureMethod): VerificationMethod {
  switch (method) {
    case "wet":
      return "wet_signature";
    case "electronic":
      return "electronic_signature";
    case "upload":
      return "uploaded_signature";
    case "digital":
      return "digital_signature";
    case "pin":
      return "pin_authorization";
    default:
      return "wet_signature";
  }
}

export function useSignatureCapture(
  options: UseSignatureCaptureOptions = {}
): UseSignatureCaptureReturn {
  const [status, setStatus] = useState<SignatureStatus>("idle");
  const [accountRisk, setAccountRisk] = useState<AccountRiskLevel>(DEFAULT_ACCOUNT_RISK);
  const [selectedMethod, setSelectedMethod] = useState<SignatureMethod>(DEFAULT_SIGNATURE_METHOD);
  const [signatureImage, setSignatureImage] = useState<SignatureImageAsset | null>(null);
  const [digitalSignature, setDigitalSignature] = useState<DigitalSignatureArtifact | null>(null);
  const [pinAuthorization, setPinAuthorization] = useState<PinAuthorizationArtifact | null>(null);
  const [generatedPin, setGeneratedPin] = useState("");
  const [pinGeneratedAt, setPinGeneratedAt] = useState("");
  const [pinEntry, setPinEntry] = useState("");
  const [signerName, setSignerName] = useState("");
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [auditLog, setAuditLog] = useState<SignatureAuditEvent[]>([
    createAuditEvent("method_selected", "Step 3 ready. Wet signature selected by default."),
  ]);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [storedRecord, setStoredRecord] = useState<StoredSignatureRecord | null>(null);

  const appendAuditEvent = useCallback((event: SignatureAuditEvent) => {
    setAuditLog((current) => [event, ...current]);
  }, []);

  const clearMessages = useCallback(() => {
    setErrorMsg("");
    setSuccessMsg("");
  }, []);

  const handleRiskChange = useCallback(
    (risk: AccountRiskLevel) => {
      setAccountRisk(risk);
      clearMessages();
      appendAuditEvent(
        createAuditEvent("method_selected", `Account risk level set to ${risk}.`, "info")
      );
    },
    [appendAuditEvent, clearMessages]
  );

  const handleMethodChange = useCallback(
    (method: SignatureMethod) => {
      setSelectedMethod(method);
      clearMessages();
      appendAuditEvent(
        createAuditEvent("method_selected", `Signature method changed to ${method}.`, "info")
      );
    },
    [appendAuditEvent, clearMessages]
  );

  const handleCanvasSave = useCallback(
    (asset: Omit<SignatureImageAsset, "source">) => {
      clearMessages();
      const source = selectedMethod === "electronic" ? "electronic" : "wet";
      setSignatureImage({ ...asset, source });
      appendAuditEvent(
        createAuditEvent("capture_status", `${source} signature captured and previewed.`, "success")
      );
    },
    [appendAuditEvent, clearMessages, selectedMethod]
  );

  const handleClearSignatureImage = useCallback(() => {
    setSignatureImage(null);
    clearMessages();
    appendAuditEvent(
      createAuditEvent("capture_status", "Signature image cleared from the current draft.", "warning")
    );
  }, [appendAuditEvent, clearMessages]);

  const handleUploadSignature = useCallback(
    async (file: File) => {
      setStatus("uploading");
      clearMessages();
      appendAuditEvent(
        createAuditEvent("upload_status", `Validating uploaded signature image: ${file.name}.`)
      );

      const { asset, error } = await validateAndReadSignatureImage(file);
      if (error || !asset) {
        const message = error?.message ?? "Unable to validate the uploaded signature image.";
        setStatus("error");
        setErrorMsg(message);
        appendAuditEvent(createAuditEvent("upload_status", message, "error"));
        return;
      }

      setSignatureImage(asset);
      setStatus("idle");
      appendAuditEvent(
        createAuditEvent("upload_status", `Uploaded signature image preserved from ${file.name}.`, "success")
      );
    },
    [appendAuditEvent, clearMessages]
  );

  const handleSignerNameChange = useCallback((value: string) => {
    setSignerName(value);
  }, []);

  const handleConsentChange = useCallback((accepted: boolean) => {
    setConsentAccepted(accepted);
  }, []);

  const handleGenerateDigitalSignature = useCallback(async () => {
    clearMessages();
    if (!signerName.trim()) {
      setStatus("error");
      setErrorMsg("Signer name is required to generate a digital signature.");
      appendAuditEvent(
        createAuditEvent(
          "capture_status",
          "Digital signature generation blocked: missing signer name.",
          "error"
        )
      );
      return;
    }

    if (!consentAccepted) {
      setStatus("error");
      setErrorMsg("Consent must be confirmed before generating a digital signature.");
      appendAuditEvent(
        createAuditEvent(
          "capture_status",
          "Digital signature generation blocked: consent missing.",
          "error"
        )
      );
      return;
    }

    setStatus("generating");
    const artifact = await createDigitalSignatureArtifact(
      signerName.trim(),
      DIGITAL_SIGNATURE_CONSENT,
      accountRisk
    );
    setDigitalSignature(artifact);
    setStatus("idle");
    appendAuditEvent(
      createAuditEvent(
        "capture_status",
        `Digital signature token generated for ${artifact.signerName}.`,
        "success"
      )
    );
  }, [accountRisk, appendAuditEvent, clearMessages, consentAccepted, signerName]);

  const handleGeneratePin = useCallback(async () => {
    clearMessages();

    if (accountRisk === "high") {
      setStatus("error");
      setErrorMsg("PIN authorization is only allowed for eligible low-risk accounts.");
      appendAuditEvent(
        createAuditEvent("pin_generated", "PIN generation blocked for a high-risk account.", "error")
      );
      return;
    }

    setStatus("generating");
    const nextPin = generateSecurePin();
    setGeneratedPin(nextPin);
    setPinGeneratedAt(new Date().toISOString());
    setPinEntry("");
    setPinAuthorization(null);
    setStatus("idle");
    appendAuditEvent(
      createAuditEvent("pin_generated", "Secure PIN generated for low-risk authorization.", "success")
    );
  }, [accountRisk, appendAuditEvent, clearMessages]);

  const handlePinEntryChange = useCallback((value: string) => {
    setPinEntry(value.replace(/\D/g, "").slice(0, 6));
  }, []);

  const handleValidatePin = useCallback(async () => {
    clearMessages();

    if (!generatedPin) {
      setStatus("error");
      setErrorMsg("Generate a PIN before validating it.");
      appendAuditEvent(
        createAuditEvent("pin_validated", "PIN validation blocked: no PIN generated.", "error")
      );
      return;
    }

    if (pinEntry !== generatedPin) {
      setStatus("error");
      setErrorMsg("Entered PIN does not match the generated PIN.");
      setPinAuthorization(null);
      appendAuditEvent(createAuditEvent("pin_validated", "PIN validation failed.", "error"));
      return;
    }

    setStatus("generating");
    const validatedAt = new Date().toISOString();
    const artifact = await createPinAuthorizationArtifact(generatedPin, pinGeneratedAt, validatedAt);
    setPinAuthorization(artifact);
    setStatus("idle");
    appendAuditEvent(
      createAuditEvent("pin_validated", "PIN validated and ready for submission.", "success")
    );
  }, [appendAuditEvent, clearMessages, generatedPin, pinEntry, pinGeneratedAt]);

  const handleSubmit = useCallback(async () => {
    clearMessages();
    setStatus("saving");
    const submissionStarted = createAuditEvent("submission_status", "Signature submission started.");
    appendAuditEvent(submissionStarted);

    const validationMessage = validateSignatureSubmission({
      accountRisk,
      method: selectedMethod,
      signatureImage,
      digitalSignature,
      pinAuthorization,
    });

    if (validationMessage) {
      setStatus("error");
      setErrorMsg(validationMessage);
      appendAuditEvent(createAuditEvent("submission_status", validationMessage, "error"));
      return;
    }

    try {
      const verificationMethod = getVerificationMethod(selectedMethod);
      const submittedAt = new Date().toISOString();
      const submissionCompleted = createAuditEvent(
        "submission_status",
        "Signature submission completed.",
        "success"
      );

      const record = await saveSignatureRecord({
        signatureMethod: selectedMethod,
        verificationMethod,
        accountRisk,
        signatureImage:
          selectedMethod === "wet" || selectedMethod === "electronic" || selectedMethod === "upload"
            ? signatureImage ?? undefined
            : undefined,
        digitalSignature: selectedMethod === "digital" ? digitalSignature ?? undefined : undefined,
        pinAuthorization: selectedMethod === "pin" ? pinAuthorization ?? undefined : undefined,
        metadata: {
          submittedAt,
          verificationMethod,
          accountRisk,
          deviceUserAgent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
          fileName: signatureImage?.fileName,
          fileSize: signatureImage?.fileSize,
          width: signatureImage?.width,
          height: signatureImage?.height,
          customerReference: options.customerReference,
        },
        auditLog: [submissionCompleted, submissionStarted, ...auditLog],
      });

      setStoredRecord(record);
      setStatus("saved");
      setSuccessMsg(`Signature preserved successfully. Reference: ${record.id}`);
      appendAuditEvent(createAuditEvent("submission_status", `Signature record stored as ${record.id}.`, "success"));
      options.onComplete?.(record);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to securely preserve the signature record.";
      setStatus("error");
      setErrorMsg(message);
      appendAuditEvent(createAuditEvent("submission_status", message, "error"));
    }
  }, [
    accountRisk,
    appendAuditEvent,
    auditLog,
    clearMessages,
    digitalSignature,
    options,
    pinAuthorization,
    selectedMethod,
    signatureImage,
  ]);

  const requirementText = useMemo(
    () => getRiskRequirementMessage(accountRisk),
    [accountRisk]
  );

  const isSelectedMethodEligible = useMemo(
    () => methodSatisfiesRisk(accountRisk, selectedMethod),
    [accountRisk, selectedMethod]
  );

  return {
    status,
    accountRisk,
    selectedMethod,
    signatureImage,
    digitalSignature,
    pinAuthorization,
    generatedPin,
    pinEntry,
    signerName,
    consentAccepted,
    auditLog,
    errorMsg,
    successMsg,
    isSelectedMethodEligible,
    requirementText,
    storedRecord,
    handleRiskChange,
    handleMethodChange,
    handleCanvasSave,
    handleClearSignatureImage,
    handleUploadSignature,
    handleSignerNameChange,
    handleConsentChange,
    handleGenerateDigitalSignature,
    handleGeneratePin,
    handlePinEntryChange,
    handleValidatePin,
    handleSubmit,
  };
}
