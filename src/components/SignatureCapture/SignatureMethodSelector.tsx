import React from "react";
import type { AccountRiskLevel, SignatureMethod } from "@/types";

interface SignatureMethodSelectorProps {
  accountRisk: AccountRiskLevel;
  selectedMethod: SignatureMethod;
  onRiskChange: (risk: AccountRiskLevel) => void;
  onMethodChange: (method: SignatureMethod) => void;
  isMethodEligible: (method: SignatureMethod) => boolean;
  requirementText: string;
}

const methodCards: Array<{
  method: SignatureMethod;
  title: string;
  description: string;
}> = [
  {
    method: "wet",
    title: "Wet Signature",
    description: "Handwritten signature captured with pen, stylus, touch, or mouse input.",
  },
  {
    method: "electronic",
    title: "Electronic Signature",
    description: "Handwritten signature drawn directly on a digital device.",
  },
  {
    method: "upload",
    title: "Uploaded Image",
    description: "Upload an existing PNG or JPG signature image for review and retention.",
  },
  {
    method: "digital",
    title: "Digital Signature",
    description: "Generate a cryptographic signature token when wet signature is unavailable.",
  },
  {
    method: "pin",
    title: "PIN Authorization",
    description: "Generate and validate a secure PIN for eligible low-risk accounts only.",
  },
];

const SignatureMethodSelector: React.FC<SignatureMethodSelectorProps> = ({
  accountRisk,
  selectedMethod,
  onRiskChange,
  onMethodChange,
  isMethodEligible,
  requirementText,
}) => {
  return (
    <div style={s.root}>
      <div style={s.riskSection}>
        <div style={s.riskHeader}>
          <div style={s.sectionTitle}>Account Risk</div>
          <div style={s.requirement}>{requirementText}</div>
        </div>

        <div style={s.toggleRow}>
          {(["high", "low"] as AccountRiskLevel[]).map((risk) => {
            const selected = risk === accountRisk;
            return (
              <button
                key={risk}
                type="button"
                onClick={() => onRiskChange(risk)}
                style={{
                  ...s.toggleButton,
                  ...(selected ? s.toggleButtonActive : null),
                }}
              >
                {risk === "high" ? "High Risk" : "Low Risk"}
              </button>
            );
          })}
        </div>
      </div>

      <div style={s.methodGrid}>
        {methodCards.map((card) => {
          const selected = card.method === selectedMethod;
          const eligible = isMethodEligible(card.method);
          const isBlocked = accountRisk === "high" && card.method === "pin";

          return (
            <button
              key={card.method}
              type="button"
              onClick={() => onMethodChange(card.method)}
              style={{
                ...s.card,
                ...(selected ? s.cardActive : null),
                ...(isBlocked ? s.cardBlocked : null),
              }}
            >
              <div style={s.cardHeader}>
                <span style={s.cardTitle}>{card.title}</span>
                <span
                  style={{
                    ...s.cardBadge,
                    ...(eligible ? s.cardBadgeSuccess : s.cardBadgeMuted),
                    ...(isBlocked ? s.cardBadgeError : null),
                  }}
                >
                  {isBlocked ? "Blocked" : eligible ? "Eligible" : "Supplemental"}
                </span>
              </div>
              <div style={s.cardText}>{card.description}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: 18,
  },
  riskSection: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  riskHeader: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  sectionTitle: {
    fontSize: 11,
    color: "#6f6f6f",
    fontWeight: 700,
    letterSpacing: "0.7px",
    textTransform: "uppercase",
  },
  requirement: {
    fontSize: 12,
    color: "#d2d2d2",
    lineHeight: 1.5,
  },
  toggleRow: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  toggleButton: {
    padding: "10px 14px",
    borderRadius: 999,
    border: "1px solid #2b2b2b",
    background: "#101010",
    color: "#d4d4d4",
    fontFamily: "inherit",
    fontSize: 12,
    fontWeight: 600,
  },
  toggleButtonActive: {
    borderColor: "#38b6ff",
    color: "#38b6ff",
    background: "#0b2230",
  },
  methodGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: 12,
  },
  card: {
    textAlign: "left",
    borderRadius: 14,
    border: "1px solid #222222",
    background: "#101010",
    color: "#efefef",
    padding: "14px 14px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 12,
    minHeight: 132,
    fontFamily: "inherit",
  },
  cardActive: {
    borderColor: "#00e5a0",
    boxShadow: "0 0 0 1px rgba(0, 229, 160, 0.18) inset",
  },
  cardBlocked: {
    opacity: 0.75,
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: 10,
    alignItems: "center",
  },
  cardTitle: {
    fontSize: 13,
    fontWeight: 700,
  },
  cardBadge: {
    fontSize: 10,
    fontWeight: 700,
    borderRadius: 999,
    padding: "3px 8px",
  },
  cardBadgeSuccess: {
    background: "#0f3528",
    color: "#00e5a0",
  },
  cardBadgeMuted: {
    background: "#1b1b1b",
    color: "#888888",
  },
  cardBadgeError: {
    background: "#351010",
    color: "#ff9e9e",
  },
  cardText: {
    fontSize: 12,
    color: "#9a9a9a",
    lineHeight: 1.6,
  },
};

export default SignatureMethodSelector;
