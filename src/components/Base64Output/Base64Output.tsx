import React, { useState } from "react";
import { base64ToBytes, bytesPreview } from "@/services/imageConvert.service";

interface Base64OutputProps {
  dataUrl: string;
}

const Base64Output: React.FC<Base64OutputProps> = ({ dataUrl }) => {
  const [copied, setCopied] = useState(false);
  const b64Preview = dataUrl.substring(0, 200) + "…";
  const byteInfo = bytesPreview(dataUrl);

  const handleCopy = () => {
    const b64 = dataUrl.split(",")[1] ?? dataUrl;
    navigator.clipboard.writeText(b64).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleDownload = () => {
    const bytes = base64ToBytes(dataUrl);
    const blob = new Blob([bytes.buffer as ArrayBuffer], { type: "image/jpeg" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `face-capture-${Date.now()}.jpg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <details style={s.details}>
      <summary style={s.summary}>Base64 / byte output</summary>
      <div style={s.body}>
        <Row label="Base64 (first 200 chars)" value={b64Preview} />
        <Row label="Byte array preview" value={byteInfo} />
        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <button style={s.btn} onClick={handleCopy}>
            {copied ? "Copied!" : "Copy base64"}
          </button>
          <button style={s.btn} onClick={handleDownload}>
            Download .jpg
          </button>
        </div>
      </div>
    </details>
  );
};

const Row: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={{ marginBottom: 10 }}>
    <div style={{ fontSize: 10, color: "#555", textTransform: "uppercase" as const, letterSpacing: 0.8, marginBottom: 4 }}>
      {label}
    </div>
    <code
      style={{
        display: "block",
        background: "#0d0d0d",
        color: "#00e5a0",
        fontSize: 11,
        padding: "7px 10px",
        borderRadius: 6,
        overflowX: "auto" as const,
        wordBreak: "break-all" as const,
        fontFamily: "inherit",
        lineHeight: 1.5,
      }}
    >
      {value}
    </code>
  </div>
);

const s: Record<string, React.CSSProperties> = {
  details: {
    background: "#0d0d0d",
    border: "1px solid #1e1e1e",
    borderRadius: 8,
    overflow: "hidden",
    marginTop: 4,
  },
  summary: {
    padding: "10px 14px",
    cursor: "pointer",
    fontSize: 12,
    color: "#666",
    userSelect: "none" as const,
    letterSpacing: "0.5px",
  },
  body: {
    padding: "10px 14px 14px",
    borderTop: "1px solid #1e1e1e",
  },
  btn: {
    background: "transparent",
    color: "#888",
    border: "1px solid #333",
    borderRadius: 6,
    padding: "6px 14px",
    fontSize: 12,
    cursor: "pointer",
    fontFamily: "inherit",
  },
};

export default Base64Output;
