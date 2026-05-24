import React from "react";
import {
  DIGITAL_SIGNATURE_CONSENT,
  SIGNATURE_ACCEPTED_EXTENSIONS,
} from "@/constants/signature";
import { useSignatureCapture } from "@/hooks/useSignatureCapture";
import { methodSatisfiesRisk } from "@/services/signatureValidation.service";
import type { CustomerReference, NIDExtractorResult, StoredSignatureRecord } from "@/types";
import SignatureAuditLog from "./SignatureAuditLog";
import SignatureCanvas from "./SignatureCanvas";
import SignatureMethodSelector from "./SignatureMethodSelector";
import SignaturePreview from "./SignaturePreview";

interface SignatureCaptureProps {
  nidResult?: NIDExtractorResult | null;
  onComplete?: (record: StoredSignatureRecord) => void;
}

const SignatureCapture: React.FC<SignatureCaptureProps> = ({ nidResult, onComplete }) => {
  const customerReference: CustomerReference | undefined = nidResult
    ? {
        name: nidResult.fields.nameEnglish ?? nidResult.fields.nameBengali,
        idNumber: nidResult.fields.idNumber,
      }
    : undefined;

  const {
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
  } = useSignatureCapture({
    customerReference,
    onComplete,
  });

  const handleUploadChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await handleUploadSignature(file);
    event.target.value = "";
  };

  const customerName = customerReference?.name ?? "Customer";
  const customerId = customerReference?.idNumber ?? "Pending NID result";

  return (
    <div style={s.root}>
      <div style={s.header}>
        <div style={s.headerCopy}>
          <div style={s.headerLogo}>SIG</div>
          <div>
            <h1 style={s.title}>Signature Capture and Preservation</h1>
            <div style={s.subtitle}>
              Step 3 securely captures the customer signature, metadata, timestamp, and verification method.
            </div>
          </div>
        </div>
        <div style={s.statusBadge}>{status === "saved" ? "Stored" : status}</div>
      </div>

      <div style={s.referenceBar}>
        <div style={s.referenceItem}>
          <span style={s.referenceLabel}>Customer</span>
          <span style={s.referenceValue}>{customerName}</span>
        </div>
        <div style={s.referenceItem}>
          <span style={s.referenceLabel}>NID / Ref</span>
          <span style={s.referenceValue}>{customerId}</span>
        </div>
      </div>

      <div style={s.mainGrid}>
        <div style={s.column}>
          <div style={s.panel}>
            <SignatureMethodSelector
              accountRisk={accountRisk}
              selectedMethod={selectedMethod}
              onRiskChange={handleRiskChange}
              onMethodChange={handleMethodChange}
              isMethodEligible={(method) => methodSatisfiesRisk(accountRisk, method)}
              requirementText={requirementText}
            />
          </div>

          {(selectedMethod === "wet" || selectedMethod === "electronic") && (
            <div style={s.panel}>
              <SignatureCanvas
                label={selectedMethod === "wet" ? "Wet Signature Pad" : "Electronic Signature Pad"}
                helperText="Supports mouse, stylus, and mobile touch input. Save the preview before submitting."
                onSave={handleCanvasSave}
                onClear={handleClearSignatureImage}
              />
            </div>
          )}

          {selectedMethod === "upload" && (
            <div style={s.panel}>
              <div style={s.sectionTitle}>Upload Existing Signature</div>
              <div style={s.helperText}>
                Accepts {SIGNATURE_ACCEPTED_EXTENSIONS.join(", ")}. Uploaded images are validated for readability before submission.
              </div>
              <label style={s.uploadBox}>
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                  onChange={handleUploadChange}
                  style={s.hiddenInput}
                />
                <span style={s.uploadTitle}>Choose signature image</span>
                <span style={s.uploadHint}>PNG or JPG, max 5 MB</span>
              </label>
            </div>
          )}

          {selectedMethod === "digital" && (
            <div style={s.panel}>
              <div style={s.sectionTitle}>Generate Digital Signature</div>
              <div style={s.formField}>
                <label style={s.fieldLabel}>Signer Name</label>
                <input
                  value={signerName}
                  onChange={(event) => handleSignerNameChange(event.target.value)}
                  placeholder="Enter the customer name"
                  style={s.input}
                />
              </div>
              <label style={s.checkboxRow}>
                <input
                  type="checkbox"
                  checked={consentAccepted}
                  onChange={(event) => handleConsentChange(event.target.checked)}
                />
                <span style={s.checkboxText}>{DIGITAL_SIGNATURE_CONSENT}</span>
              </label>
              <button type="button" style={s.button} onClick={handleGenerateDigitalSignature}>
                Generate Digital Signature
              </button>
            </div>
          )}

          {selectedMethod === "pin" && (
            <div style={s.panel}>
              <div style={s.sectionTitle}>PIN Authorization</div>
              <div style={s.helperText}>
                PIN authorization is available only for eligible low-risk accounts. A validated PIN is stored as a hash, not in plain text.
              </div>
              <div style={s.buttonRow}>
                <button type="button" style={s.button} onClick={handleGeneratePin}>
                  Generate Secure PIN
                </button>
                {generatedPin && <div style={s.pinBadge}>PIN: {generatedPin}</div>}
              </div>
              <div style={s.formField}>
                <label style={s.fieldLabel}>Re-enter PIN to validate</label>
                <input
                  value={pinEntry}
                  onChange={(event) => handlePinEntryChange(event.target.value)}
                  placeholder="Enter the generated PIN"
                  inputMode="numeric"
                  style={s.input}
                />
              </div>
              <button type="button" style={s.secondaryButton} onClick={handleValidatePin}>
                Validate PIN
              </button>
            </div>
          )}

          {!isSelectedMethodEligible && (
            <div style={s.warningBanner}>
              The selected method can be captured, but it does not satisfy current risk rules for Step 3 completion.
            </div>
          )}

          {errorMsg && <div style={s.errorBanner}>{errorMsg}</div>}
          {successMsg && <div style={s.successBanner}>{successMsg}</div>}

          <div style={s.panel}>
            <div style={s.submitRow}>
              <div>
                <div style={s.sectionTitle}>Submit Step 3</div>
                <div style={s.helperText}>
                  Submission preserves the signature record locally with metadata, timestamp, verification method, and audit history.
                </div>
              </div>
              <button
                type="button"
                style={{
                  ...s.button,
                  opacity: status === "saving" ? 0.6 : 1,
                  cursor: status === "saving" ? "wait" : "pointer",
                }}
                disabled={status === "saving"}
                onClick={handleSubmit}
              >
                {status === "saving" ? "Saving..." : "Submit Signature Record"}
              </button>
            </div>
          </div>
        </div>

        <div style={s.column}>
          <div style={s.panel}>
            <SignaturePreview
              method={selectedMethod}
              signatureImage={signatureImage}
              digitalSignature={digitalSignature}
              pinAuthorization={pinAuthorization}
              storedRecord={storedRecord}
            />
          </div>
          <div style={s.panel}>
            <SignatureAuditLog auditLog={auditLog} />
          </div>
        </div>
      </div>
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  root: {
    fontFamily: "'DM Mono','Fira Code','Cascadia Code',monospace",
    background: "#0a0a0a",
    color: "#ececec",
    border: "1px solid #212121",
    borderRadius: 18,
    padding: "2rem 1.5rem",
    display: "flex",
    flexDirection: "column",
    gap: 18,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: 16,
    alignItems: "flex-start",
    flexWrap: "wrap",
  },
  headerCopy: {
    display: "flex",
    gap: 12,
    alignItems: "center",
  },
  headerLogo: {
    width: 48,
    height: 48,
    borderRadius: 14,
    background: "linear-gradient(135deg, #00e5a0, #38b6ff)",
    color: "#04100c",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 14,
    fontWeight: 800,
    letterSpacing: "1px",
  },
  title: {
    margin: 0,
    fontSize: 22,
    color: "#ffffff",
  },
  subtitle: {
    marginTop: 6,
    fontSize: 12,
    color: "#8b8b8b",
    lineHeight: 1.6,
    maxWidth: 760,
  },
  statusBadge: {
    borderRadius: 999,
    border: "1px solid #2b2b2b",
    background: "#111111",
    color: "#38b6ff",
    padding: "6px 12px",
    fontSize: 11,
    fontWeight: 700,
    textTransform: "uppercase",
  },
  referenceBar: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: 12,
  },
  referenceItem: {
    borderRadius: 12,
    border: "1px solid #202020",
    background: "#0e0e0e",
    padding: "12px 14px",
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  referenceLabel: {
    fontSize: 10,
    color: "#6f6f6f",
    textTransform: "uppercase",
    letterSpacing: "0.8px",
  },
  referenceValue: {
    fontSize: 13,
    color: "#f0f0f0",
    wordBreak: "break-word",
  },
  mainGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
    gap: 16,
  },
  column: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
    minWidth: 0,
  },
  panel: {
    borderRadius: 16,
    border: "1px solid #1f1f1f",
    background: "#0d0d0d",
    padding: 16,
  },
  sectionTitle: {
    fontSize: 11,
    color: "#6f6f6f",
    fontWeight: 700,
    letterSpacing: "0.7px",
    textTransform: "uppercase",
    marginBottom: 8,
  },
  helperText: {
    fontSize: 12,
    color: "#9a9a9a",
    lineHeight: 1.6,
  },
  uploadBox: {
    marginTop: 14,
    display: "flex",
    flexDirection: "column",
    gap: 8,
    borderRadius: 14,
    border: "1px dashed #2c2c2c",
    background: "#101010",
    padding: 18,
    cursor: "pointer",
  },
  hiddenInput: {
    display: "none",
  },
  uploadTitle: {
    fontSize: 14,
    color: "#f3f3f3",
    fontWeight: 700,
  },
  uploadHint: {
    fontSize: 12,
    color: "#7d7d7d",
  },
  formField: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    marginBottom: 14,
  },
  fieldLabel: {
    fontSize: 11,
    color: "#7d7d7d",
  },
  input: {
    borderRadius: 10,
    border: "1px solid #2a2a2a",
    background: "#111111",
    color: "#f0f0f0",
    padding: "11px 12px",
    fontFamily: "inherit",
    fontSize: 13,
  },
  checkboxRow: {
    display: "flex",
    gap: 10,
    alignItems: "flex-start",
    marginBottom: 14,
  },
  checkboxText: {
    fontSize: 12,
    color: "#d7d7d7",
    lineHeight: 1.6,
  },
  buttonRow: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
    alignItems: "center",
    marginBottom: 14,
  },
  button: {
    background: "#00e5a0",
    color: "#06120d",
    border: "none",
    borderRadius: 8,
    padding: "10px 16px",
    fontFamily: "inherit",
    fontSize: 12,
    fontWeight: 800,
  },
  secondaryButton: {
    background: "transparent",
    color: "#d6d6d6",
    border: "1px solid #2a2a2a",
    borderRadius: 8,
    padding: "10px 16px",
    fontFamily: "inherit",
    fontSize: 12,
    fontWeight: 700,
  },
  pinBadge: {
    borderRadius: 999,
    background: "#0d2330",
    color: "#38b6ff",
    border: "1px solid #214f6d",
    padding: "6px 10px",
    fontSize: 12,
    fontWeight: 700,
  },
  warningBanner: {
    borderRadius: 12,
    border: "1px solid #6a5b18",
    background: "#2c2509",
    color: "#facc15",
    padding: "12px 14px",
    fontSize: 12,
    lineHeight: 1.6,
  },
  errorBanner: {
    borderRadius: 12,
    border: "1px solid #7f1d1d",
    background: "#351010",
    color: "#ffb3b3",
    padding: "12px 14px",
    fontSize: 12,
    lineHeight: 1.6,
  },
  successBanner: {
    borderRadius: 12,
    border: "1px solid #146c47",
    background: "#0f2e22",
    color: "#00e5a0",
    padding: "12px 14px",
    fontSize: 12,
    lineHeight: 1.6,
  },
  submitRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: 16,
    alignItems: "center",
    flexWrap: "wrap",
  },
};

export default SignatureCapture;
