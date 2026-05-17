import React from "react";
import type {
  DigitalSignatureArtifact,
  PinAuthorizationArtifact,
  SignatureImageAsset,
  SignatureMethod,
  StoredSignatureRecord,
} from "@/types";

interface SignaturePreviewProps {
  method: SignatureMethod;
  signatureImage: SignatureImageAsset | null;
  digitalSignature: DigitalSignatureArtifact | null;
  pinAuthorization: PinAuthorizationArtifact | null;
  storedRecord: StoredSignatureRecord | null;
}

const SignaturePreview: React.FC<SignaturePreviewProps> = ({
  method,
  signatureImage,
  digitalSignature,
  pinAuthorization,
  storedRecord,
}) => {
  return (
    <div style={s.root}>
      <div style={s.title}>Preview</div>

      {(method === "wet" || method === "electronic" || method === "upload") && signatureImage && (
        <div style={s.previewCard}>
          <img src={signatureImage.dataUrl} alt="Signature preview" style={s.image} />
          <div style={s.metaGrid}>
            <Meta label="Source" value={signatureImage.source} />
            <Meta label="Format" value={signatureImage.mimeType} />
            <Meta label="Size" value={`${signatureImage.width} x ${signatureImage.height}`} />
            {signatureImage.fileName && <Meta label="File" value={signatureImage.fileName} />}
          </div>
        </div>
      )}

      {method === "digital" && digitalSignature && (
        <div style={s.previewCard}>
          <Meta label="Signer" value={digitalSignature.signerName} />
          <Meta label="Token" value={digitalSignature.token} />
          <Meta label="Digest" value={`${digitalSignature.digest.slice(0, 24)}...`} />
          <Meta label="Generated" value={new Date(digitalSignature.generatedAt).toLocaleString()} />
        </div>
      )}

      {method === "pin" && pinAuthorization && (
        <div style={s.previewCard}>
          <Meta label="Challenge" value={pinAuthorization.challengeId} />
          <Meta label="PIN Reference" value={`****${pinAuthorization.last4}`} />
          <Meta label="Validated" value={new Date(pinAuthorization.validatedAt).toLocaleString()} />
        </div>
      )}

      {!signatureImage && !digitalSignature && !pinAuthorization && (
        <div style={s.emptyState}>
          Capture, upload, or generate the selected signature method to review it here before submission.
        </div>
      )}

      {storedRecord && (
        <div style={s.savedCard}>
          <div style={s.savedTitle}>Stored Record</div>
          <Meta label="Reference" value={storedRecord.id} />
          <Meta label="Submitted" value={new Date(storedRecord.metadata.submittedAt).toLocaleString()} />
          <Meta label="Verification" value={storedRecord.verificationMethod} />
          <Meta label="Integrity Hash" value={`${storedRecord.integrityHash.slice(0, 24)}...`} />
        </div>
      )}
    </div>
  );
};

const Meta: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={s.metaRow}>
    <span style={s.metaLabel}>{label}</span>
    <span style={s.metaValue}>{value}</span>
  </div>
);

const s: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  title: {
    fontSize: 11,
    color: "#6f6f6f",
    fontWeight: 700,
    letterSpacing: "0.7px",
    textTransform: "uppercase",
  },
  previewCard: {
    borderRadius: 14,
    border: "1px solid #222222",
    background: "#0f0f0f",
    padding: 14,
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  image: {
    width: "100%",
    borderRadius: 10,
    border: "1px solid #2b2b2b",
    background: "#ffffff",
    objectFit: "contain",
  },
  metaGrid: {
    display: "grid",
    gap: 8,
  },
  metaRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    alignItems: "flex-start",
  },
  metaLabel: {
    fontSize: 11,
    color: "#7d7d7d",
    minWidth: 90,
  },
  metaValue: {
    fontSize: 11,
    color: "#f0f0f0",
    textAlign: "right",
    wordBreak: "break-word",
  },
  emptyState: {
    borderRadius: 14,
    border: "1px dashed #2a2a2a",
    background: "#0d0d0d",
    padding: 18,
    fontSize: 12,
    color: "#8b8b8b",
    lineHeight: 1.6,
  },
  savedCard: {
    borderRadius: 14,
    border: "1px solid #1a5c43",
    background: "#0b1f18",
    padding: 14,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  savedTitle: {
    fontSize: 12,
    color: "#00e5a0",
    fontWeight: 700,
  },
};

export default SignaturePreview;
