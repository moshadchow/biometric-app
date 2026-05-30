import React from "react";
import { useNavigate } from "react-router-dom";
import { getOnboardingEligibility } from "@/api/OnboardingApi";
import type { OnboardingEligibility } from "@/api/OnboardingApi";

const CustomerDashboard: React.FC = () => {
  const [eligibility, setEligibility] = React.useState<OnboardingEligibility | null>(null);
  const [error, setError] = React.useState("");
  const navigate = useNavigate();

  React.useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const response = await getOnboardingEligibility();
        if (!cancelled) {
          setEligibility(response);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : String(loadError));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSignOut = () => {
    sessionStorage.removeItem("jwt_token");
    navigate("/login", { replace: true });
  };

  const session = eligibility?.latest_session;

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div>
          <p style={s.kicker}>Customer dashboard</p>
          <h1 style={s.title}>Account onboarding status</h1>
          <p style={s.subtitle}>
            Your onboarding record is preserved. Re-onboarding requires administrator approval.
          </p>
        </div>
        <button type="button" onClick={handleSignOut} style={s.signOutButton}>
          Sign Out
        </button>
      </div>

      {error && <div style={s.errorBanner}>{error}</div>}

      <div style={s.panel}>
        <div style={s.statusBadge}>{session?.workflow_state ?? "Loading"}</div>
        <div style={s.grid}>
          <Info label="Username" value={eligibility?.username ?? "Loading"} />
          <Info label="Activation" value={session?.activation_status ?? "Pending"} />
          <Info label="Risk" value={session?.risk_category ?? session?.compliance_summary?.risk_category ?? "N/A"} />
          <Info label="Screening" value={session?.compliance_summary?.screening_status ?? "N/A"} />
        </div>
        <p style={s.message}>{eligibility?.message ?? "Loading onboarding status..."}</p>
      </div>
    </div>
  );
};

const Info: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={s.infoCard}>
    <span style={s.infoLabel}>{label}</span>
    <span style={s.infoValue}>{value}</span>
  </div>
);

const s: Record<string, React.CSSProperties> = {
  page: {
    width: "100%",
    maxWidth: 1040,
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
    padding: "1rem 0",
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
  },
  subtitle: {
    margin: "0.65rem 0 0",
    color: "#a1a1a1",
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
  panel: {
    borderRadius: 18,
    border: "1px solid #1f1f1f",
    background: "rgba(10,10,10,0.96)",
    padding: "1.25rem",
    display: "grid",
    gap: "1rem",
  },
  statusBadge: {
    justifySelf: "start",
    borderRadius: 999,
    border: "1px solid rgba(56,182,255,0.28)",
    background: "rgba(56,182,255,0.08)",
    color: "#7dcfff",
    padding: "0.45rem 0.75rem",
    fontSize: "0.78rem",
    fontWeight: 800,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "0.75rem",
  },
  infoCard: {
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    padding: "0.85rem",
    display: "grid",
    gap: "0.4rem",
  },
  infoLabel: {
    color: "#8ca0b2",
    fontSize: "0.78rem",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  infoValue: {
    color: "#fff",
    fontWeight: 700,
  },
  message: {
    margin: 0,
    color: "#b0bac5",
    lineHeight: 1.6,
  },
  errorBanner: {
    borderRadius: 14,
    border: "1px solid rgba(255,99,99,0.28)",
    background: "rgba(255,99,99,0.08)",
    color: "#ffd2d2",
    padding: "0.9rem 1rem",
  },
};

export default CustomerDashboard;
