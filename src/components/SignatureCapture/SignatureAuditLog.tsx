import React from "react";
import type { SignatureAuditEvent } from "@/types";

interface SignatureAuditLogProps {
  auditLog: SignatureAuditEvent[];
}

const statusColors: Record<string, { background: string; color: string; border: string }> = {
  info: { background: "#111827", color: "#93c5fd", border: "#1d4ed8" },
  success: { background: "#0f2e22", color: "#00e5a0", border: "#146c47" },
  warning: { background: "#2d2409", color: "#facc15", border: "#7c5c0b" },
  error: { background: "#351010", color: "#ff9e9e", border: "#7f1d1d" },
};

const SignatureAuditLog: React.FC<SignatureAuditLogProps> = ({ auditLog }) => {
  return (
    <div style={s.root}>
      <div style={s.title}>Audit Log</div>
      <div style={s.list}>
        {auditLog.map((event) => {
          const colors = statusColors[event.status] ?? statusColors.info;
          return (
            <div key={event.id} style={s.item}>
              <div style={s.itemHeader}>
                <span
                  style={{
                    ...s.badge,
                    background: colors.background,
                    color: colors.color,
                    borderColor: colors.border,
                  }}
                >
                  {event.type.split("_").join(" ")}
                </span>
                <span style={s.time}>{new Date(event.createdAt).toLocaleTimeString()}</span>
              </div>
              <div style={s.message}>{event.message}</div>
            </div>
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
    gap: 12,
  },
  title: {
    fontSize: 11,
    color: "#6f6f6f",
    fontWeight: 700,
    letterSpacing: "0.7px",
    textTransform: "uppercase",
  },
  list: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
    maxHeight: 280,
    overflowY: "auto",
    paddingRight: 4,
  },
  item: {
    border: "1px solid #1e1e1e",
    borderRadius: 12,
    background: "#0f0f0f",
    padding: 12,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  itemHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: 10,
    alignItems: "center",
    flexWrap: "wrap",
  },
  badge: {
    border: "1px solid transparent",
    borderRadius: 999,
    fontSize: 10,
    fontWeight: 700,
    padding: "3px 8px",
    textTransform: "capitalize",
  },
  time: {
    fontSize: 10,
    color: "#6f6f6f",
  },
  message: {
    fontSize: 12,
    color: "#d4d4d4",
    lineHeight: 1.5,
  },
};

export default SignatureAuditLog;
