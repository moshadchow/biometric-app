import React, { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getScreeningStatus } from "@/api/ComplianceApi";
import Stepper from "@/components/Stepper";
import type { StepConfig } from "@/components/Stepper";
import FaceCapture from "@/components/FaceCapture";
import NIDExtractor from "@/components/NIDExtractor";
import CustomerIdentityForm from "@/components/CustomerIdentityForm";
import SignatureCapture from "@/components/SignatureCapture";
import {
  listOnboardingSessions,
  loadOnboardingSession,
  getOnboardingSessionStatus,
  submitFaceVerification,
  submitNIDExtraction,
  submitSignatureCapture,
} from "@/api/OnboardingApi";
import type { OnboardingSessionSummary } from "@/api/OnboardingApi";
import type {
  FaceMatchCompletionContext,
  MatchResult,
  NIDCompletionContext,
  NIDExtractorResult,
  SignatureCompletionContext,
  StoredSignatureRecord,
  ComplianceSummary,
} from "@/types";

const REFERENCE_IMAGE_URL = "/reference.jpg";

type SyncStatus = "pending" | "syncing" | "synced" | "error";
type StepKey = "face" | "ocr" | "identity" | "signature" | "screening";

interface StepSyncState {
  status: SyncStatus;
  detail: string;
}

function stepIndexForResumeStep(step: string): number {
  const normalized = step || "face_verification";
  if (normalized === "ocr_extraction") return 1;
  if (normalized === "identity_form") return 2;
  if (normalized === "signature_capture") return 3;
  if (["screening_status", "review_status", "complete", "rejected"].includes(normalized)) return 4;
  return 0;
}

function restoredNidResult(session: OnboardingSessionSummary): NIDExtractorResult | null {
  const ocr = session.ocr_extraction;
  if (!ocr) return null;
  return {
    front: {
      side: "front",
      pages: [],
      combinedText: ocr.front_text,
      averageConfidence: 0,
      processingTimeMs: 0,
    },
    back: ocr.back_text
      ? {
          side: "back",
          pages: [],
          combinedText: ocr.back_text,
          averageConfidence: 0,
          processingTimeMs: 0,
        }
      : undefined,
    mergedText: ocr.merged_text,
    completedAt: ocr.completed_at,
    fields: ocr.fields as NIDExtractorResult["fields"],
    frontDetection: ocr.front_detection as unknown as NIDExtractorResult["frontDetection"],
    backDetection: ocr.back_detection as unknown as NIDExtractorResult["backDetection"],
  };
}

const CustomerPage: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [nidResult, setNidResult] = useState<NIDExtractorResult | null>(null);
  const [backendSessionId, setBackendSessionId] = useState<number | null>(null);
  const [backendSessionStatus, setBackendSessionStatus] = useState<string>("loading");
  const [backendSessionStep, setBackendSessionStep] = useState<string>("unknown");
  const [workflowState, setWorkflowState] = useState<string>("ONBOARDING_STARTED");
  const [completedStepIds, setCompletedStepIds] = useState<string[]>([]);
  const [nextRequiredStep, setNextRequiredStep] = useState<string>("face_verification");
  const [riskCategory, setRiskCategory] = useState<string | null>(null);
  const [complianceSummary, setComplianceSummary] = useState<ComplianceSummary | null>(null);
  const [syncStates, setSyncStates] = useState<Record<StepKey, StepSyncState>>({
    face: { status: "pending", detail: "Not submitted yet." },
    ocr: { status: "pending", detail: "Not submitted yet." },
    identity: { status: "pending", detail: "Not submitted yet." },
    signature: { status: "pending", detail: "Not submitted yet." },
    screening: { status: "pending", detail: "Not started yet." },
  });
  const [sessionHistoryCount, setSessionHistoryCount] = useState<number>(0);
  const [syncNotice, setSyncNotice] = useState<string>("");
  const [syncError, setSyncError] = useState<string>("");
  const navigate = useNavigate();

  const handleSignOut = () => {
    sessionStorage.removeItem("jwt_token");
    navigate("/login", { replace: true });
  };

  const reportSyncSuccess = useCallback((message: string) => {
    setSyncNotice(message);
    setSyncError("");
  }, []);

  const reportSyncError = useCallback((message: string) => {
    setSyncError(message);
  }, []);

  const applyBackendSession = useCallback((session: OnboardingSessionSummary) => {
    setBackendSessionId(session.id);
    setBackendSessionStatus(session.status);
    setBackendSessionStep(session.current_step);
    setWorkflowState(session.workflow_state);
    setCompletedStepIds(session.completed_steps ?? []);
    setNextRequiredStep(session.next_required_step || session.current_step);
    setRiskCategory(session.risk_category ?? null);
    setComplianceSummary(session.compliance_summary ?? null);
    setSyncStates((current) => ({
      ...current,
      face: session.completed_steps?.includes("face_verification")
        ? { status: "synced", detail: "Face verification stored in the backend." }
        : current.face,
      ocr: session.completed_steps?.includes("ocr_extraction")
        ? { status: "synced", detail: "NID extraction stored in the backend." }
        : current.ocr,
      identity: session.completed_steps?.includes("identity_form")
        ? { status: "synced", detail: "Customer identity form submitted." }
        : current.identity,
      signature: session.completed_steps?.includes("signature_capture")
        ? { status: "synced", detail: "Signature record stored in the backend." }
        : current.signature,
      screening: session.completed_steps?.includes("screening")
        ? { status: "synced", detail: "Compliance screening completed." }
        : session.next_required_step === "screening_status" || session.next_required_step === "review_status"
          ? { status: "syncing", detail: "Compliance screening or review is active." }
          : current.screening,
    }));
    setActiveStep(stepIndexForResumeStep(session.next_required_step || session.current_step));
    const restored = restoredNidResult(session);
    if (restored) {
      setNidResult(restored);
    }
  }, []);

  const resolveBackendSessionId = useCallback(async (): Promise<number> => {
    if (backendSessionId !== null) {
      return backendSessionId;
    }

    const session = await loadOnboardingSession();
    applyBackendSession(session);
    return session.id;
  }, [applyBackendSession, backendSessionId]);

  const updateStepSync = useCallback((step: StepKey, status: SyncStatus, detail: string) => {
    setSyncStates((current) => ({
      ...current,
      [step]: { status, detail },
    }));
  }, []);

  React.useEffect(() => {
    let cancelled = false;

    const loadSession = async () => {
      try {
        const session = await loadOnboardingSession();

        const history = await listOnboardingSessions();
        if (cancelled) return;

        applyBackendSession(session);
        setSessionHistoryCount(history.length);
      } catch (error) {
        if (cancelled) return;
        reportSyncError(
          `Unable to load onboarding session state: ${
            error instanceof Error ? error.message : String(error)
          }`
        );
      }
    };

    void loadSession();

    return () => {
      cancelled = true;
    };
  }, [applyBackendSession, reportSyncError]);

  React.useEffect(() => {
    const screeningId = complianceSummary?.screening_request_id;
    const screeningStatus = complianceSummary?.screening_status;
    if (!screeningId || !screeningStatus || ["APPROVED", "REJECTED", "REVIEW_REQUIRED", "FAILED"].includes(screeningStatus)) {
      return;
    }

    let cancelled = false;
    const timer = window.setInterval(() => {
      void (async () => {
        try {
          const screening = await getScreeningStatus(screeningId);
          if (cancelled) {
            return;
          }
          setComplianceSummary({
            screening_request_id: screening.id,
            screening_status: screening.status,
            final_decision: screening.decision ?? null,
            risk_category: screening.risk_category ?? null,
            risk_score: screening.risk_score ?? null,
            review_required: screening.review_required,
            activation_eligible: screening.activation_eligible,
            last_updated_at: screening.updated_at,
          });
          if (backendSessionId) {
            const session = await getOnboardingSessionStatus(backendSessionId);
            if (!cancelled) {
              applyBackendSession(session);
            }
          }
        } catch {
          // Keep polling best-effort to avoid interrupting onboarding progress.
        }
      })();
    }, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [applyBackendSession, backendSessionId, complianceSummary]);

  const handleFaceMatch = useCallback(
    (result: MatchResult, score: number, context?: FaceMatchCompletionContext) => {
      if (result !== "Success" || !context) {
        return;
      }

      updateStepSync("face", "syncing", "Sending face verification to the backend.");
      void (async () => {
        try {
          const sessionId = await resolveBackendSessionId();
          const session = await submitFaceVerification(
            {
              result,
              distance: score,
              threshold: context.matchThreshold,
              context,
            },
            sessionId
          );
          applyBackendSession(session);
          updateStepSync("face", "synced", "Face verification stored in the backend.");
          reportSyncSuccess("Face verification stored in the backend.");
        } catch (error: unknown) {
          updateStepSync(
            "face",
            "error",
            error instanceof Error ? error.message : String(error)
          );
          reportSyncError(
            `Face verification completed locally, but backend persistence failed: ${
              error instanceof Error ? error.message : String(error)
            }`
          );
        }
      })();
    },
    [applyBackendSession, reportSyncError, reportSyncSuccess, resolveBackendSessionId]
  );

  const handleNidComplete = useCallback(
    (result: NIDExtractorResult, context?: NIDCompletionContext) => {
      setNidResult(result);

      if (!context?.frontFile) {
        reportSyncError("NID extraction completed locally, but the backend upload context was missing.");
        return;
      }

      updateStepSync("ocr", "syncing", "Sending OCR extraction to the backend.");
      void (async () => {
        try {
          const sessionId = await resolveBackendSessionId();
          const session = await submitNIDExtraction({ result, context }, sessionId);
          applyBackendSession(session);
          updateStepSync("ocr", "synced", "NID extraction stored in the backend.");
          reportSyncSuccess("NID extraction stored in the backend. Continue with the customer identity form.");
        } catch (error: unknown) {
          updateStepSync(
            "ocr",
            "error",
            error instanceof Error ? error.message : String(error)
          );
          reportSyncError(
            `NID extraction completed locally, but backend persistence failed: ${
              error instanceof Error ? error.message : String(error)
            }`
          );
        }
      })();
    },
    [applyBackendSession, reportSyncError, reportSyncSuccess, resolveBackendSessionId]
  );

  const handleIdentitySubmitted = useCallback(
    (session: OnboardingSessionSummary) => {
      applyBackendSession(session);
      updateStepSync("identity", "synced", "Customer identity form submitted.");
      reportSyncSuccess("Customer identity form submitted. Compliance screening has started.");
    },
    [applyBackendSession, reportSyncSuccess, updateStepSync]
  );

  const handleSignatureComplete = useCallback(
    (record: StoredSignatureRecord, context?: SignatureCompletionContext) => {
      if (!context) {
        reportSyncError("Signature saved locally, but backend persistence context was missing.");
        return;
      }

      updateStepSync("signature", "syncing", "Sending signature record to the backend.");
      void (async () => {
        try {
          const sessionId = await resolveBackendSessionId();
          const session = await submitSignatureCapture({ record, context }, sessionId);
          applyBackendSession(session);
          updateStepSync("signature", "synced", "Signature record stored in the backend.");
          reportSyncSuccess("Signature record stored in the backend.");
        } catch (error: unknown) {
          updateStepSync(
            "signature",
            "error",
            error instanceof Error ? error.message : String(error)
          );
          reportSyncError(
            `Signature saved locally, but backend persistence failed: ${
              error instanceof Error ? error.message : String(error)
            }`
          );
        }
      })();
    },
    [applyBackendSession, reportSyncError, reportSyncSuccess, resolveBackendSessionId]
  );

  const steps: StepConfig[] = [
    {
      id: "face_verification",
      label: "Face Verification",
      component: (
        <FaceCapture
          referenceImageSrc={REFERENCE_IMAGE_URL}
          modelPath="/models"
          onMatch={handleFaceMatch}
          onProceed={() => setActiveStep(1)}
        />
      ),
    },
    {
      id: "ocr_extraction",
      label: "OCR Extraction",
      component: <NIDExtractor onComplete={handleNidComplete} />,
    },
    {
      id: "identity_form",
      label: "Identity Form",
      component: (
        <CustomerIdentityForm
          sessionId={backendSessionId}
          onSubmitted={handleIdentitySubmitted}
        />
      ),
    },
    {
      id: "signature_capture",
      label: "Signature Capture",
      component: (
        <SignatureCapture
          nidResult={nidResult}
          onComplete={handleSignatureComplete}
        />
      ),
    },
    {
      id: "screening",
      label: "Status",
      component: (
        <OnboardingStatusPanel
          workflowState={workflowState}
          currentStep={backendSessionStep}
          nextRequiredStep={nextRequiredStep}
          complianceSummary={complianceSummary}
          riskCategory={riskCategory}
          onRefresh={async () => {
            if (!backendSessionId) return;
            const session = await getOnboardingSessionStatus(backendSessionId);
            applyBackendSession(session);
          }}
        />
      ),
    },
  ];

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div>
          <p style={s.kicker}>Customer workspace</p>
          <h1 style={s.title}>Biometric verification</h1>
          <p style={s.subtitle}>
            Complete face check, OCR extraction, identity review, and signature capture.
          </p>
        </div>

        <button type="button" onClick={handleSignOut} style={s.signOutButton}>
          Sign Out
        </button>
      </div>

      <div style={s.syncPanel}>
        <div style={s.syncPanelHeader}>
          <div>
            <div style={s.syncPanelTitle}>Backend sync status</div>
            <div style={s.syncPanelSubtitle}>
              Session {backendSessionId ? `#${backendSessionId}` : "loading"} | {backendSessionStatus} | {backendSessionStep}
            </div>
          </div>
          <div style={s.syncPanelMeta}>History: {sessionHistoryCount} record{sessionHistoryCount === 1 ? "" : "s"}</div>
        </div>
        <div style={s.syncGrid}>
          <SyncCard label="Face verification" state={syncStates.face} />
          <SyncCard label="OCR extraction" state={syncStates.ocr} />
          <SyncCard label="Identity form" state={syncStates.identity} />
          <SyncCard label="Signature capture" state={syncStates.signature} />
          <SyncCard label="Screening and review" state={syncStates.screening} />
        </div>
        <div style={s.compliancePanel}>
          <div style={s.complianceTitle}>Compliance screening</div>
          <div style={s.complianceStatus}>
            {complianceSummary?.screening_status ?? "NOT_STARTED"}
            {complianceSummary?.final_decision ? ` | ${complianceSummary.final_decision}` : ""}
          </div>
          <div style={s.complianceDetail}>
            {formatComplianceMessage(complianceSummary, backendSessionStatus, backendSessionStep)}
          </div>
        </div>
      </div>

      {(syncNotice || syncError) && (
        <div style={syncError ? s.errorBanner : s.noticeBanner}>
          {syncError || syncNotice}
        </div>
      )}

      <div style={s.shell}>
        <Stepper
          steps={steps}
          activeIndex={activeStep}
          onStepChange={setActiveStep}
          completedStepIds={completedStepIds}
          isStepUnlocked={(step, index) => completedStepIds.includes(step.id) || stepIndexForResumeStep(nextRequiredStep) === index}
        />
      </div>
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  page: {
    width: "100%",
    maxWidth: 1240,
    margin: "0 auto",
    padding: "1.25rem 1rem 2rem",
    display: "grid",
    gap: "1rem",
  },
  header: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: "1rem",
    padding: "1.1rem 1.1rem 0.5rem",
    flexWrap: "wrap",
  },
  kicker: {
    margin: 0,
    color: "#00e5a0",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    fontSize: "0.76rem",
    fontWeight: 700,
  },
  title: {
    margin: "0.35rem 0 0",
    color: "#f4f4f4",
    fontSize: "2rem",
    lineHeight: 1.1,
  },
  subtitle: {
    margin: "0.65rem 0 0",
    color: "#a1a1a1",
    lineHeight: 1.6,
    maxWidth: 680,
  },
  signOutButton: {
    alignSelf: "flex-start",
    borderRadius: 14,
    border: "1px solid rgba(255, 255, 255, 0.12)",
    background: "rgba(255, 255, 255, 0.04)",
    color: "#f1f1f1",
    padding: "0.85rem 1.1rem",
    fontSize: "0.96rem",
    fontWeight: 700,
    cursor: "pointer",
    transition: "transform 0.18s ease, border-color 0.18s ease, background 0.18s ease",
  },
  shell: {
    width: "100%",
    border: "1px solid #1f1f1f",
    borderRadius: 24,
    background: "linear-gradient(180deg, rgba(13,13,13,0.98), rgba(8,8,8,0.98))",
    boxShadow: "0 24px 80px rgba(0, 0, 0, 0.38)",
    padding: "1.35rem",
  },
  noticeBanner: {
    margin: "0 1.1rem",
    borderRadius: 14,
    border: "1px solid rgba(0, 229, 160, 0.25)",
    background: "rgba(0, 229, 160, 0.08)",
    color: "#b8ffe6",
    padding: "0.9rem 1rem",
    lineHeight: 1.5,
    fontSize: "0.95rem",
  },
  errorBanner: {
    margin: "0 1.1rem",
    borderRadius: 14,
    border: "1px solid rgba(255, 99, 99, 0.28)",
    background: "rgba(255, 99, 99, 0.08)",
    color: "#ffd2d2",
    padding: "0.9rem 1rem",
    lineHeight: 1.5,
    fontSize: "0.95rem",
  },
  syncPanel: {
    margin: "0 1.1rem",
    borderRadius: 18,
    border: "1px solid rgba(56, 182, 255, 0.18)",
    background:
      "linear-gradient(180deg, rgba(8,14,18,0.95), rgba(8,8,8,0.95)), radial-gradient(circle at top right, rgba(56,182,255,0.08), transparent 34%)",
    padding: "1rem",
    display: "grid",
    gap: "0.9rem",
  },
  syncPanelHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "1rem",
    alignItems: "flex-start",
    flexWrap: "wrap",
  },
  syncPanelTitle: {
    color: "#eaf7ff",
    fontSize: "0.98rem",
    fontWeight: 700,
  },
  syncPanelSubtitle: {
    color: "#8aa6b8",
    marginTop: "0.25rem",
    fontSize: "0.88rem",
  },
  syncPanelMeta: {
    color: "#38b6ff",
    fontSize: "0.86rem",
    fontWeight: 700,
  },
  syncGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: "0.75rem",
  },
  compliancePanel: {
    borderTop: "1px solid rgba(255,255,255,0.08)",
    paddingTop: "0.9rem",
    display: "grid",
    gap: "0.3rem",
  },
  complianceTitle: {
    color: "#fff",
    fontWeight: 700,
    fontSize: "0.92rem",
  },
  complianceStatus: {
    color: "#7dcfff",
    fontSize: "0.82rem",
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  complianceDetail: {
    color: "#aeb8c2",
    fontSize: "0.9rem",
    lineHeight: 1.5,
  },
  statusPanel: {
    border: "1px solid #212121",
    borderRadius: 18,
    background: "#0a0a0a",
    color: "#ececec",
    padding: "1.5rem",
    display: "grid",
    gap: "1rem",
  },
  statusEyebrow: {
    color: "#38b6ff",
    fontSize: "0.78rem",
    fontWeight: 800,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
  },
  statusTitle: {
    margin: "0.35rem 0 0",
    color: "#fff",
    fontSize: "1.35rem",
  },
  statusCopy: {
    margin: "0.6rem 0 0",
    color: "#aeb8c2",
    lineHeight: 1.6,
  },
  statusGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
    gap: "0.75rem",
  },
  statusDatum: {
    border: "1px solid #202020",
    borderRadius: 12,
    background: "#0f0f0f",
    padding: "0.85rem",
    display: "grid",
    gap: "0.35rem",
  },
  statusDatumLabel: {
    color: "#6f6f6f",
    fontSize: "0.72rem",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  statusDatumValue: {
    color: "#f3f3f3",
    fontSize: "0.9rem",
    wordBreak: "break-word",
  },
  refreshButton: {
    justifySelf: "start",
    borderRadius: 8,
    border: "1px solid #2a2a2a",
    background: "#111",
    color: "#d6d6d6",
    padding: "0.7rem 0.95rem",
    fontSize: "0.86rem",
    fontWeight: 700,
    cursor: "pointer",
  },
};

function formatComplianceMessage(
  summary: ComplianceSummary | null,
  onboardingStatus: string,
  onboardingStep: string
): string {
  if (!summary) {
    return "Compliance screening will start automatically after the customer identity form is submitted.";
  }
  if (summary.screening_status === "SCREENING_PENDING") {
    return "Screening request created. Background checks are waiting to start.";
  }
  if (summary.screening_status === "SCREENING_IN_PROGRESS") {
    return "Background sanctions, PEP, media, watchlist, exit-list, and IP checks are running. Activation stays blocked until the final decision.";
  }
  if (summary.screening_status === "REVIEW_REQUIRED") {
    return "A compliance analyst review is required before activation can proceed.";
  }
  if (summary.screening_status === "REJECTED") {
    return "Compliance screening rejected this onboarding. Activation remains blocked.";
  }
  if (summary.screening_status === "APPROVED") {
    if (onboardingStatus === "completed" && onboardingStep === "complete" && summary.activation_eligible) {
      return "Compliance screening approved. This onboarding is eligible for activation.";
    }
    return "Compliance screening approved. Complete the remaining onboarding step to become activation eligible.";
  }
  return "Compliance screening state is available.";
}

const OnboardingStatusPanel: React.FC<{
  workflowState: string;
  currentStep: string;
  nextRequiredStep: string;
  complianceSummary: ComplianceSummary | null;
  riskCategory: string | null;
  onRefresh: () => Promise<void>;
}> = ({ workflowState, currentStep, nextRequiredStep, complianceSummary, riskCategory, onRefresh }) => {
  const [refreshing, setRefreshing] = React.useState(false);
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div style={s.statusPanel}>
      <div>
        <div style={s.statusEyebrow}>{workflowState}</div>
        <h2 style={s.statusTitle}>{statusTitleForWorkflow(workflowState)}</h2>
        <p style={s.statusCopy}>
          {formatComplianceMessage(complianceSummary, workflowState, currentStep)}
        </p>
      </div>
      <div style={s.statusGrid}>
        <StatusDatum label="Current step" value={currentStep} />
        <StatusDatum label="Next required" value={nextRequiredStep} />
        <StatusDatum label="Screening" value={complianceSummary?.screening_status ?? "NOT_STARTED"} />
        <StatusDatum label="Risk" value={riskCategory ?? complianceSummary?.risk_category ?? "Pending"} />
      </div>
      <button type="button" style={s.refreshButton} onClick={handleRefresh} disabled={refreshing}>
        {refreshing ? "Refreshing..." : "Refresh Status"}
      </button>
    </div>
  );
};

const StatusDatum: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={s.statusDatum}>
    <span style={s.statusDatumLabel}>{label}</span>
    <span style={s.statusDatumValue}>{value}</span>
  </div>
);

function statusTitleForWorkflow(workflowState: string): string {
  if (workflowState === "EDD_REQUIRED" || workflowState === "EDD_IN_REVIEW") {
    return "Enhanced Due Diligence Review";
  }
  if (workflowState === "ONBOARDING_COMPLETED") {
    return "Onboarding Completed";
  }
  if (workflowState === "ONBOARDING_REJECTED") {
    return "Onboarding Rejected";
  }
  return "Compliance Screening Status";
}

const SyncCard: React.FC<{ label: string; state: StepSyncState }> = ({ label, state }) => {
  const colors: Record<SyncStatus, { border: string; bg: string; color: string }> = {
    pending: { border: "rgba(255,255,255,0.10)", bg: "rgba(255,255,255,0.03)", color: "#9aa3ab" },
    syncing: { border: "rgba(56,182,255,0.28)", bg: "rgba(56,182,255,0.08)", color: "#7dcfff" },
    synced: { border: "rgba(0,229,160,0.30)", bg: "rgba(0,229,160,0.08)", color: "#8effd1" },
    error: { border: "rgba(255,99,99,0.30)", bg: "rgba(255,99,99,0.08)", color: "#ffb5b5" },
  };

  const c = colors[state.status];
  return (
    <div
      style={{
        borderRadius: 14,
        border: `1px solid ${c.border}`,
        background: c.bg,
        padding: "0.9rem",
        display: "grid",
        gap: "0.35rem",
      }}
    >
      <div style={{ color: "#fff", fontWeight: 700, fontSize: "0.92rem" }}>{label}</div>
      <div style={{ color: c.color, fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 700 }}>
        {state.status}
      </div>
      <div style={{ color: "#aeb8c2", fontSize: "0.86rem", lineHeight: 1.5 }}>{state.detail}</div>
    </div>
  );
};

export default CustomerPage;
