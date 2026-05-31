import React from "react";
import { useNavigate } from "react-router-dom";
import {
  approveComplianceCase,
  getComplianceCase,
  listAdminCustomerOnboarding,
  listComplianceCases,
  recalculateRiskAssessment,
  rejectComplianceCase,
} from "@/api/ComplianceApi";
import type { ComplianceCase, ComplianceCaseDetail } from "@/types";
import type { AdminCustomerOnboarding } from "@/api/OnboardingApi";
import { RiskCategoryManagement } from "./RiskCategoryManagement";
import { RiskModelManagement } from "./RiskModelManagement";

type AdminTab = "cases" | "eligibility" | "risk" | "business" | "profession";

function AdminDashboard() {
  const navigate = useNavigate();
  const [cases, setCases] = React.useState<ComplianceCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = React.useState<number | null>(null);
  const [selectedCase, setSelectedCase] = React.useState<ComplianceCaseDetail | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [actionError, setActionError] = React.useState("");
  const [actionLoading, setActionLoading] = React.useState(false);
  const [customers, setCustomers] = React.useState<AdminCustomerOnboarding[]>([]);
  const [adminTab, setAdminTab] = React.useState<AdminTab>("cases");

  const loadCases = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const items = await listComplianceCases();
      setCases(items);
      setSelectedCaseId((current) => current ?? items[0]?.id ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCustomers = React.useCallback(async () => {
    try {
      setCustomers(await listAdminCustomerOnboarding());
    } catch (loadError) {
      setActionError(loadError instanceof Error ? loadError.message : String(loadError));
    }
  }, []);

  React.useEffect(() => {
    void loadCases();
    void loadCustomers();
  }, [loadCases, loadCustomers]);

  React.useEffect(() => {
    if (!selectedCaseId) {
      setSelectedCase(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const detail = await getComplianceCase(selectedCaseId);
        if (!cancelled) {
          setSelectedCase(detail);
        }
      } catch (detailError) {
        if (!cancelled) {
          setActionError(detailError instanceof Error ? detailError.message : String(detailError));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedCaseId]);

  const handleDecision = React.useCallback(
    async (decision: "approve" | "reject") => {
      if (!selectedCase) {
        return;
      }
      setActionLoading(true);
      setActionError("");
      try {
        const payload = {
          reason: decision === "approve" ? "Manual compliance approval." : "Manual compliance rejection.",
          notes: `Decision submitted from admin dashboard as ${decision}.`,
        };
        const detail =
          decision === "approve"
            ? await approveComplianceCase(selectedCase.case.id, payload)
            : await rejectComplianceCase(selectedCase.case.id, payload);
        setSelectedCase(detail);
        await loadCases();
      } catch (decisionError) {
        setActionError(decisionError instanceof Error ? decisionError.message : String(decisionError));
      } finally {
        setActionLoading(false);
      }
    },
    [loadCases, selectedCase]
  );

  const handleRiskRecalculate = React.useCallback(async () => {
    if (!selectedCase) {
      return;
    }
    setActionLoading(true);
    setActionError("");
    try {
      await recalculateRiskAssessment(selectedCase.screening.session_id);
      const detail = await getComplianceCase(selectedCase.case.id);
      setSelectedCase(detail);
      await loadCases();
    } catch (recalculateError) {
      setActionError(recalculateError instanceof Error ? recalculateError.message : String(recalculateError));
    } finally {
      setActionLoading(false);
    }
  }, [loadCases, selectedCase]);

  const handleSignOut = React.useCallback(() => {
    sessionStorage.removeItem("jwt_token");
    navigate("/login", { replace: true });
  }, [navigate]);

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div>
          <div style={s.kicker}>Compliance portal</div>
          <h1 style={s.title}>Screening review queue</h1>
          <p style={s.subtitle}>Review automated sanctions and due-diligence outcomes before activation.</p>
        </div>
        <button type="button" onClick={handleSignOut} style={s.signOutButton}>
          Sign Out
        </button>
      </div>

      {error && <div style={s.errorBanner}>{error}</div>}

      <div style={s.tabBar}>
        <button type="button" onClick={() => setAdminTab("cases")} style={{ ...s.tabButton, ...(adminTab === "cases" ? s.tabButtonActive : {}) }}>
          Cases
        </button>
        <button type="button" onClick={() => setAdminTab("eligibility")} style={{ ...s.tabButton, ...(adminTab === "eligibility" ? s.tabButtonActive : {}) }}>
          Customer Eligibility
        </button>
        <button type="button" onClick={() => setAdminTab("risk")} style={{ ...s.tabButton, ...(adminTab === "risk" ? s.tabButtonActive : {}) }}>
          Risk Management
        </button>
        <button type="button" onClick={() => setAdminTab("business")} style={{ ...s.tabButton, ...(adminTab === "business" ? s.tabButtonActive : {}) }}>
          Business Categories
        </button>
        <button type="button" onClick={() => setAdminTab("profession")} style={{ ...s.tabButton, ...(adminTab === "profession" ? s.tabButtonActive : {}) }}>
          Profession Categories
        </button>
      </div>

      {adminTab === "risk" && <RiskModelManagement />}
      {adminTab === "business" && <RiskCategoryManagement kind="business" />}
      {adminTab === "profession" && <RiskCategoryManagement kind="profession" />}

      {adminTab === "eligibility" && <div style={s.customerPanel}>
        <div style={s.panelTitle}>Customer onboarding eligibility</div>
        {customers.length === 0 ? (
          <div style={s.emptyState}>No customer onboarding records available.</div>
        ) : (
          <div style={s.customerGrid}>
            {customers.map((customer) => {
              const completed = customer.latest_session?.workflow_state === "ONBOARDING_COMPLETED";
              const status = completed ? "Permanently locked" : "In progress or not started";
              return (
                <div key={customer.user_id} style={s.customerCard}>
                  <div>
                    <div style={s.resultTitle}>{customer.username}</div>
                    <div style={s.resultMeta}>
                      {customer.latest_session?.workflow_state ?? "NO_SESSION"} | {status}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>}

      {adminTab === "cases" && <div style={s.layout}>
        <div style={s.queuePanel}>
          <div style={s.panelTitle}>Cases</div>
          {loading ? (
            <div style={s.emptyState}>Loading cases...</div>
          ) : cases.length === 0 ? (
            <div style={s.emptyState}>No compliance cases are currently open.</div>
          ) : (
            <div style={s.queueList}>
              {cases.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedCaseId(item.id)}
                  style={{
                    ...s.queueItem,
                    ...(selectedCaseId === item.id ? s.queueItemActive : {}),
                  }}
                >
                  <div style={s.queueItemHeader}>
                    <span style={s.queueUser}>{item.username ?? `User ${item.screening_request_id}`}</span>
                    <span style={s.queueStatus}>{item.status}</span>
                  </div>
                  <div style={s.queueMeta}>
                    Screening {item.screening_status}
                    {item.decision ? ` | ${item.decision}` : ""}
                  </div>
                  <div style={s.queueMeta}>
                    Risk {item.risk_category ?? "N/A"}
                    {typeof item.risk_score === "number" ? ` (${item.risk_score})` : ""}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div style={s.detailPanel}>
          <div style={s.panelTitle}>Case detail</div>
          {!selectedCase ? (
            <div style={s.emptyState}>Select a case to inspect results and audit history.</div>
          ) : (
            <div style={s.detailBody}>
              <div style={s.summaryGrid}>
                <InfoCard label="Queue Status" value={selectedCase.case.status} />
                <InfoCard label="Screening" value={selectedCase.screening.status} />
                <InfoCard label="Decision" value={selectedCase.screening.decision ?? "Pending"} />
                <InfoCard
                  label="Risk"
                  value={
                    selectedCase.customer_risk_assessment
                      ? `${selectedCase.customer_risk_assessment.risk_category} (${selectedCase.customer_risk_assessment.total_score})`
                      : selectedCase.risk_assessment
                        ? `${selectedCase.risk_assessment.risk_category} (${selectedCase.risk_assessment.risk_score})`
                      : "Pending"
                  }
                />
                <InfoCard
                  label="EDD"
                  value={
                    selectedCase.customer_risk_assessment?.edd_required
                      ? selectedCase.customer_risk_assessment.edd_status ?? "EDD_REQUIRED"
                      : "Not required"
                  }
                />
                <InfoCard
                  label="Rule Version"
                  value={selectedCase.customer_risk_assessment?.rule_version ?? "N/A"}
                />
              </div>

              {actionError && <div style={s.errorBanner}>{actionError}</div>}

              <div style={s.actionRow}>
                <button type="button" style={s.secondaryButton} disabled={actionLoading} onClick={() => void handleRiskRecalculate()}>
                  Recalculate Risk
                </button>
                <button type="button" style={s.approveButton} disabled={actionLoading} onClick={() => void handleDecision("approve")}>
                  Approve
                </button>
                <button type="button" style={s.rejectButton} disabled={actionLoading} onClick={() => void handleDecision("reject")}>
                  Reject
                </button>
              </div>

              <Section title="Risk assessment">
                {!selectedCase.customer_risk_assessment ? (
                  <div style={s.emptyState}>No customer risk assessment has been calculated yet.</div>
                ) : (
                  <div style={s.riskPanel}>
                    {selectedCase.customer_risk_assessment.edd_reasons.length > 0 && (
                      <div style={s.eddList}>
                        {selectedCase.customer_risk_assessment.edd_reasons.map((reason) => (
                          <span key={reason} style={s.eddBadge}>{reason.replace(/_/g, " ")}</span>
                        ))}
                      </div>
                    )}
                    <div style={s.factorList}>
                      {selectedCase.customer_risk_assessment.factors.map((factor) => (
                        <div key={factor.id} style={s.factorRow}>
                          <div>
                            <div style={s.resultTitle}>{factor.factor_name.replace(/_/g, " ")}</div>
                            <div style={s.resultMeta}>{factor.source}</div>
                          </div>
                          <div style={s.factorScore}>{factor.factor_score}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </Section>

              <Section title="Results">
                {selectedCase.results.length === 0 ? (
                  <div style={s.emptyState}>No screening results available yet.</div>
                ) : (
                  selectedCase.results.map((result) => (
                    <div key={result.id} style={s.resultCard}>
                      <div style={s.resultTitle}>
                        {result.screening_type} | {result.outcome}
                      </div>
                      <div style={s.resultText}>{result.evidence_summary ?? "No evidence summary provided."}</div>
                      <div style={s.resultMeta}>Provider: {result.provider_name}</div>
                    </div>
                  ))
                )}
              </Section>

              <Section title="Audit log">
                {selectedCase.audit_logs.length === 0 ? (
                  <div style={s.emptyState}>No audit entries recorded yet.</div>
                ) : (
                  selectedCase.audit_logs.map((entry) => (
                    <div key={entry.id} style={s.auditEntry}>
                      <div style={s.resultTitle}>{entry.event_type}</div>
                      <div style={s.resultText}>{entry.message}</div>
                      <div style={s.resultMeta}>{new Date(entry.created_at).toLocaleString()}</div>
                    </div>
                  ))
                )}
              </Section>
            </div>
          )}
        </div>
      </div>}
    </div>
  );
}

const InfoCard: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={s.infoCard}>
    <div style={s.infoLabel}>{label}</div>
    <div style={s.infoValue}>{value}</div>
  </div>
);

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <section style={s.section}>
    <div style={s.sectionTitle}>{title}</div>
    <div style={s.sectionBody}>{children}</div>
  </section>
);

const s: Record<string, React.CSSProperties> = {
  page: {
    width: "100%",
    maxWidth: 1320,
    margin: "0 auto",
    padding: "1.5rem 1rem 2rem",
    display: "grid",
    gap: "1rem",
  },
  header: {
    padding: "0.5rem 0",
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: "1rem",
    flexWrap: "wrap",
  },
  kicker: {
    color: "#38b6ff",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    fontWeight: 700,
    fontSize: "0.76rem",
  },
  title: {
    margin: "0.35rem 0 0",
    color: "#f4f4f4",
    fontSize: "2rem",
  },
  subtitle: {
    margin: "0.6rem 0 0",
    color: "#a1a1a1",
    maxWidth: 720,
    lineHeight: 1.6,
  },
  signOutButton: {
    borderRadius: 12,
    border: "1px solid rgba(255, 255, 255, 0.12)",
    background: "rgba(255, 255, 255, 0.04)",
    color: "#f1f1f1",
    padding: "0.8rem 1rem",
    fontWeight: 700,
    cursor: "pointer",
  },
  tabBar: {
    display: "flex",
    gap: "0.65rem",
    flexWrap: "wrap",
  },
  tabButton: {
    borderRadius: 12,
    border: "1px solid rgba(255, 255, 255, 0.12)",
    background: "rgba(255, 255, 255, 0.04)",
    color: "#d8d8d8",
    padding: "0.75rem 0.95rem",
    fontWeight: 800,
    cursor: "pointer",
  },
  tabButtonActive: {
    borderColor: "#38b6ff",
    background: "rgba(56, 182, 255, 0.12)",
    color: "#f4f4f4",
  },
  layout: {
    display: "grid",
    gridTemplateColumns: "340px minmax(0, 1fr)",
    gap: "1rem",
  },
  queuePanel: {
    borderRadius: 20,
    border: "1px solid #1f1f1f",
    background: "rgba(10,10,10,0.96)",
    padding: "1rem",
    display: "grid",
    gap: "0.8rem",
    alignContent: "start",
  },
  detailPanel: {
    borderRadius: 20,
    border: "1px solid #1f1f1f",
    background: "rgba(10,10,10,0.96)",
    padding: "1rem",
    display: "grid",
    gap: "0.8rem",
    alignContent: "start",
  },
  customerPanel: {
    borderRadius: 20,
    border: "1px solid #1f1f1f",
    background: "rgba(10,10,10,0.96)",
    padding: "1rem",
    display: "grid",
    gap: "0.8rem",
  },
  customerGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "0.75rem",
  },
  customerCard: {
    borderRadius: 16,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    padding: "0.9rem",
    display: "grid",
    gap: "0.75rem",
  },
  panelTitle: {
    color: "#fff",
    fontSize: "1rem",
    fontWeight: 700,
  },
  queueList: {
    display: "grid",
    gap: "0.75rem",
  },
  queueItem: {
    borderRadius: 16,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    padding: "0.9rem",
    color: "#fff",
    textAlign: "left",
    cursor: "pointer",
  },
  queueItemActive: {
    border: "1px solid rgba(56,182,255,0.45)",
    background: "rgba(56,182,255,0.08)",
  },
  queueItemHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "0.5rem",
  },
  queueUser: {
    fontWeight: 700,
    color: "#fff",
  },
  queueStatus: {
    color: "#7dcfff",
    fontSize: "0.8rem",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  queueMeta: {
    marginTop: "0.3rem",
    color: "#b0bac5",
    fontSize: "0.85rem",
  },
  detailBody: {
    display: "grid",
    gap: "1rem",
  },
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "0.75rem",
  },
  infoCard: {
    borderRadius: 16,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    padding: "0.85rem",
  },
  infoLabel: {
    color: "#8ca0b2",
    fontSize: "0.78rem",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  infoValue: {
    color: "#fff",
    fontSize: "1rem",
    fontWeight: 700,
    marginTop: "0.4rem",
  },
  actionRow: {
    display: "flex",
    gap: "0.75rem",
    flexWrap: "wrap",
  },
  approveButton: {
    borderRadius: 14,
    border: "1px solid rgba(0,229,160,0.35)",
    background: "rgba(0,229,160,0.12)",
    color: "#b8ffe6",
    padding: "0.85rem 1rem",
    fontWeight: 700,
    cursor: "pointer",
  },
  rejectButton: {
    borderRadius: 14,
    border: "1px solid rgba(255,99,99,0.35)",
    background: "rgba(255,99,99,0.12)",
    color: "#ffd2d2",
    padding: "0.85rem 1rem",
    fontWeight: 700,
    cursor: "pointer",
  },
  secondaryButton: {
    borderRadius: 14,
    border: "1px solid rgba(255,255,255,0.16)",
    background: "rgba(255,255,255,0.05)",
    color: "#e7eef5",
    padding: "0.85rem 1rem",
    fontWeight: 700,
    cursor: "pointer",
  },
  riskPanel: {
    display: "grid",
    gap: "0.75rem",
  },
  eddList: {
    display: "flex",
    gap: "0.5rem",
    flexWrap: "wrap",
  },
  eddBadge: {
    borderRadius: 999,
    border: "1px solid rgba(250,204,21,0.28)",
    background: "rgba(250,204,21,0.08)",
    color: "#fde68a",
    padding: "0.35rem 0.6rem",
    fontSize: "0.78rem",
    textTransform: "capitalize",
  },
  factorList: {
    display: "grid",
    gap: "0.5rem",
  },
  factorRow: {
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    padding: "0.75rem",
    display: "flex",
    justifyContent: "space-between",
    gap: "1rem",
    alignItems: "center",
  },
  factorScore: {
    color: "#fff",
    fontSize: "1.1rem",
    fontWeight: 800,
  },
  section: {
    display: "grid",
    gap: "0.65rem",
  },
  sectionTitle: {
    color: "#fff",
    fontWeight: 700,
  },
  sectionBody: {
    display: "grid",
    gap: "0.75rem",
  },
  resultCard: {
    borderRadius: 14,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    padding: "0.85rem",
  },
  resultTitle: {
    color: "#fff",
    fontWeight: 700,
    fontSize: "0.92rem",
  },
  resultText: {
    color: "#b0bac5",
    marginTop: "0.35rem",
    lineHeight: 1.5,
    fontSize: "0.9rem",
  },
  resultMeta: {
    color: "#7c92a6",
    marginTop: "0.4rem",
    fontSize: "0.82rem",
  },
  auditEntry: {
    borderRadius: 14,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    padding: "0.85rem",
  },
  emptyState: {
    color: "#97a7b6",
    lineHeight: 1.6,
  },
  errorBanner: {
    borderRadius: 14,
    border: "1px solid rgba(255,99,99,0.28)",
    background: "rgba(255,99,99,0.08)",
    color: "#ffd2d2",
    padding: "0.9rem 1rem",
    lineHeight: 1.5,
    fontSize: "0.95rem",
  },
};

export default AdminDashboard;
