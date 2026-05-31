import React, { useCallback } from "react";
import type { NIDExtractorResult, NIDFieldMeta } from "@/types";
import ExtractedTextPanel from "@/components/OCRExtractor/ExtractedTextPanel";

interface NIDResultViewProps {
  result: NIDExtractorResult;
  onReset: () => void;
}

const NIDResultView: React.FC<NIDResultViewProps> = ({ result, onReset }) => {
  const { fields, front, back, frontDetection, backDetection, mergedText, completedAt } = result;
  const fieldMeta = result.fieldMeta ?? fields.__fieldMeta;

  const handleDownloadTxt = useCallback(() => {
    const blob = new Blob([mergedText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `nid-ocr-${Date.now()}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [mergedText]);

  const handleDownloadJson = useCallback(() => {
    const payload = {
      fields,
      fieldMeta,
      completedAt,
      frontDetection,
      backDetection,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `nid-data-${Date.now()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [fields, fieldMeta, completedAt, frontDetection, backDetection]);

  const ts = new Date(completedAt).toLocaleString();

  return (
    <div style={s.root}>
      <div style={s.detectionRow}>
        <div style={s.detectedBadge}>NID Card Detected</div>
        <span style={s.score}>detection score: {frontDetection.score}/100</span>
        {backDetection && !backDetection.isNID ? (
          <span style={s.backWarn}>Back side confidence low ({backDetection.score}/100)</span>
        ) : null}
        <span style={s.ts}>{ts}</span>
      </div>

      <div style={s.card}>
        <div style={s.cardTitle}>NID Card Information</div>
        <FieldRow label="ID Number" value={fields.idNumber} highlight />
        <FieldRow label="Name (Bengali)" value={fields.nameBengali} />
        <FieldRow label="Name (English)" value={fields.nameEnglish} />
        <FieldRow label="Father's Name" value={fields.fatherName} meta={fieldMeta?.fatherName} />
        <FieldRow label="Mother's Name" value={fields.motherName} meta={fieldMeta?.motherName} />
        <FieldRow label="Date of Birth" value={fields.dateOfBirth} />
      </div>

      {back ? (
        <div style={s.card}>
          <div style={s.cardTitle}>Address Information</div>
          {fields.addressRaw ? (
            <div style={s.addressBlock}>
              <span style={s.fieldLabel}>Address</span>
              <pre style={s.addressText}>{fields.addressRaw}</pre>
            </div>
          ) : null}
          <FieldRow label="District" value={fields.district} meta={fieldMeta?.district} />
          <FieldRow label="Upazila" value={fields.upazila} />
        </div>
      ) : null}

      <details style={s.details}>
        <summary style={s.summary}>Front Side - Raw OCR Text</summary>
        <div style={s.panelWrap}>
          <ExtractedTextPanel sideResult={front} label="Front" />
        </div>
      </details>
      {back ? (
        <details style={s.details}>
          <summary style={s.summary}>Back Side - Raw OCR Text</summary>
          <div style={s.panelWrap}>
            <ExtractedTextPanel sideResult={back} label="Back" />
          </div>
        </details>
      ) : null}

      <div style={s.actions}>
        <button style={s.btn} onClick={handleDownloadTxt}>Download .txt</button>
        <button style={s.btn} onClick={handleDownloadJson}>Download JSON</button>
        <button style={{ ...s.btn, ...s.btnSecondary }} onClick={onReset}>Reset</button>
      </div>
    </div>
  );
};

interface FieldRowProps {
  label: string;
  value: string | undefined;
  highlight?: boolean;
  meta?: NIDFieldMeta;
}

const FieldRow: React.FC<FieldRowProps> = ({ label, value, highlight, meta }) => (
  <div style={sr.row}>
    <span style={sr.label}>{label}</span>
    {value ? (
      <span style={sr.valueWrap}>
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
        {meta && !meta.labelVerified ? (
          <span style={sr.meta}>Extracted from nearby text. Verify this field.</span>
        ) : null}
      </span>
    ) : (
      <span style={sr.missing}>not extracted</span>
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
  valueWrap: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
    minWidth: 0,
  },
  meta: {
    fontSize: 11,
    color: "#c6a15b",
  },
  missing: {
    fontSize: 12,
    color: "#444",
    fontStyle: "italic",
  },
};

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
    background: "rgba(44, 166, 96, 0.15)",
    color: "#54d18f",
    border: "1px solid rgba(84, 209, 143, 0.35)",
    padding: "4px 10px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 600,
  },
  score: {
    fontSize: 12,
    color: "#9ca3af",
  },
  backWarn: {
    fontSize: 12,
    color: "#eab308",
  },
  ts: {
    fontSize: 12,
    color: "#6b7280",
    marginLeft: "auto",
  },
  card: {
    border: "1px solid #1f2937",
    borderRadius: 8,
    background: "#0f172a",
    padding: 16,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: "#f3f4f6",
    marginBottom: 8,
  },
  addressBlock: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    padding: "8px 0 12px",
    borderBottom: "1px solid #1a1a1a",
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
    fontSize: 13,
    color: "#e0e0e0",
    fontFamily: "inherit",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  details: {
    border: "1px solid #1f2937",
    borderRadius: 8,
    background: "#0b1220",
  },
  summary: {
    cursor: "pointer",
    padding: "12px 14px",
    color: "#d1d5db",
    fontSize: 13,
    fontWeight: 500,
  },
  panelWrap: {
    padding: "0 14px 14px",
  },
  actions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  btn: {
    border: "1px solid #334155",
    background: "#111827",
    color: "#e5e7eb",
    padding: "8px 12px",
    borderRadius: 6,
    cursor: "pointer",
  },
  btnSecondary: {
    background: "#1f2937",
  },
};

export default NIDResultView;
