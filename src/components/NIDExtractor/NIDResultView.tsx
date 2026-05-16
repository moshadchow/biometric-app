import React, { useCallback } from "react";
import type { NIDExtractorResult, NIDFields } from "@/types";
import ExtractedTextPanel from "@/components/OCRExtractor/ExtractedTextPanel";

interface NIDResultViewProps {
  result: NIDExtractorResult;
  onReset: () => void;
}

const NIDResultView: React.FC<NIDResultViewProps> = ({ result, onReset }) => {
  const { fields, front, back, frontDetection, backDetection, mergedText, completedAt } = result;

  const handleDownloadTxt = useCallback(() => {
    const blob = new Blob([mergedText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nid-ocr-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [mergedText]);

  const handleDownloadJson = useCallback(() => {
    const payload = {
      fields,
      completedAt,
      frontDetection,
      backDetection,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nid-data-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [fields, completedAt, frontDetection, backDetection]);

  const ts = new Date(completedAt).toLocaleString();

  return (
    <div style={s.root}>
      {/* Detection header */}
      <div style={s.detectionRow}>
        <div style={s.detectedBadge}>NID Card Detected ✓</div>
        <span style={s.score}>detection score: {frontDetection.score}/100</span>
        {backDetection && !backDetection.isNID && (
          <span style={s.backWarn}>Back side confidence low ({backDetection.score}/100)</span>
        )}
        <span style={s.ts}>{ts}</span>
      </div>

      {/* Structured fields */}
      <div style={s.card}>
        <div style={s.cardTitle}>NID Card Information</div>
        <FieldRow label="ID Number" value={fields.idNumber} highlight />
        <FieldRow label="Name (Bengali)" value={fields.nameBengali} />
        <FieldRow label="Name (English)" value={fields.nameEnglish} />
        <FieldRow label="Father's Name" value={fields.fatherName} />
        <FieldRow label="Mother's Name" value={fields.motherName} />
        <FieldRow label="Date of Birth" value={fields.dateOfBirth} />
      </div>

      {/* Address — only if back was processed */}
      {back && (
        <div style={s.card}>
          <div style={s.cardTitle}>Address Information</div>
          {fields.addressRaw && (
            <div style={s.addressBlock}>
              <span style={s.fieldLabel}>Address</span>
              <pre style={s.addressText}>{fields.addressRaw}</pre>
            </div>
          )}
          <FieldRow label="District" value={fields.district} />
          <FieldRow label="Upazila" value={fields.upazila} />
        </div>
      )}

      {/* Collapsible raw OCR */}
      <details style={s.details}>
        <summary style={s.summary}>Front Side — Raw OCR Text</summary>
        <div style={s.panelWrap}>
          <ExtractedTextPanel sideResult={front} label="Front" />
        </div>
      </details>
      {back && (
        <details style={s.details}>
          <summary style={s.summary}>Back Side — Raw OCR Text</summary>
          <div style={s.panelWrap}>
            <ExtractedTextPanel sideResult={back} label="Back" />
          </div>
        </details>
      )}

      {/* Actions */}
      <div style={s.actions}>
        <button style={s.btn} onClick={handleDownloadTxt}>↓ Download .txt</button>
        <button style={s.btn} onClick={handleDownloadJson}>↓ Download JSON</button>
        <button style={{ ...s.btn, ...s.btnSecondary }} onClick={onReset}>Reset</button>
      </div>
    </div>
  );
};

// ── Field row helper ──────────────────────────────────────────────────────────

interface FieldRowProps {
  label: string;
  value: string | undefined;
  highlight?: boolean;
}

const FieldRow: React.FC<FieldRowProps> = ({ label, value, highlight }) => (
  <div style={sr.row}>
    <span style={sr.label}>{label}</span>
    {value ? (
      <span
        style={{
          ...sr.value,
          ...(highlight && {
            color: "#38b6ff",
            fontSize: 18,
            letterSpacing: "2px",
            fontFamily: "'DM Mono','Fira Code',monospace",
          }),
        }}
      >
        {value}
      </span>
    ) : (
      <span style={sr.missing}>— not extracted —</span>
    )}
  </div>
);

const sr: Record<string, React.CSSProperties> = {
  row: {
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
    padding: "8px 0",
    borderBottom: "1px solid #1a1a1a",
  },
  label: {
    fontSize: 11,
    color: "#666",
    fontWeight: 600,
    letterSpacing: "0.4px",
    textTransform: "uppercase",
    minWidth: 130,
    flexShrink: 0,
    paddingTop: 2,
  },
  value: {
    fontSize: 13,
    color: "#e0e0e0",
    wordBreak: "break-word",
  },
  missing: {
    fontSize: 12,
    color: "#444",
    fontStyle: "italic",
  },
};

// ── Styles ────────────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  detectionRow: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    flexWrap: "wrap",
    marginBottom: 4,
  },
  detectedBadge: {
    background: "#0f3d2a",
    color: "#00e5a0",
    border: "1px solid #1a6a40",
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 600,
    padding: "3px 12px",
  },
  score: {
    fontSize: 11,
    color: "#555",
  },
  backWarn: {
    fontSize: 11,
    color: "#ffe56b",
    background: "#2a2a0d",
    border: "1px solid #555520",
    borderRadius: 20,
    padding: "2px 10px",
  },
  ts: {
    fontSize: 11,
    color: "#444",
    marginLeft: "auto",
  },
  card: {
    background: "#0d0d0d",
    border: "1px solid #1e1e1e",
    borderRadius: 10,
    padding: "14px 16px",
  },
  cardTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: "#555",
    letterSpacing: "0.6px",
    textTransform: "uppercase",
    marginBottom: 8,
  },
  addressBlock: {
    padding: "8px 0",
    borderBottom: "1px solid #1a1a1a",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  fieldLabel: {
    fontSize: 11,
    color: "#666",
    fontWeight: 600,
    letterSpacing: "0.4px",
    textTransform: "uppercase",
  },
  addressText: {
    margin: 0,
    fontSize: 12,
    color: "#e0e0e0",
    fontFamily: "'DM Mono','Fira Code','Cascadia Code',monospace",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    unicodeBidi: "plaintext",
    lineHeight: 1.6,
    marginTop: 4,
  },
  details: {
    border: "1px solid #1e1e1e",
    borderRadius: 10,
    overflow: "hidden",
  },
  summary: {
    fontSize: 12,
    color: "#888",
    padding: "10px 14px",
    cursor: "pointer",
    userSelect: "none",
    background: "#111",
    listStyle: "none",
  },
  panelWrap: {
    padding: "0 0 0 0",
  },
  actions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
    marginTop: 4,
  },
  btn: {
    background: "#00e5a0",
    color: "#000",
    border: "none",
    borderRadius: 8,
    padding: "10px 22px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    fontFamily: "inherit",
    letterSpacing: "0.2px",
    transition: "opacity 0.15s",
  },
  btnSecondary: {
    background: "transparent",
    color: "#999",
    border: "1px solid #333",
  },
};

export default NIDResultView;
