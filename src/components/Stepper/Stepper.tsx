import React from "react";

export interface StepConfig {
  id: string;
  label: string;
  component: React.ReactNode;
}

type StepState = "pending" | "active" | "complete";

export interface StepperProps {
  steps: StepConfig[];
  activeIndex: number;
  onStepChange: (index: number) => void;
  allowForwardNav?: boolean;
}

function getStepState(index: number, activeIndex: number): StepState {
  if (index < activeIndex) return "complete";
  if (index === activeIndex) return "active";
  return "pending";
}

const Stepper: React.FC<StepperProps> = ({
  steps,
  activeIndex,
  onStepChange,
  allowForwardNav = false,
}) => {
  return (
    <div style={s.root}>
      {/* Left nav */}
      <div style={s.nav}>
        {steps.map((step, index) => {
          const state = getStepState(index, activeIndex);
          const isClickable = state === "complete" || (state === "pending" && allowForwardNav);

          return (
            <div key={step.id} style={s.stepRow}>
              {/* Vertical connector line */}
              <div style={s.connectorColumn}>
                {index > 0 && <div style={s.connectorLine} />}
                <button
                  style={{
                    ...s.circle,
                    ...(state === "complete" && s.circleComplete),
                    ...(state === "active" && s.circleActive),
                    ...(state === "pending" && s.circlePending),
                    cursor: isClickable ? "pointer" : "default",
                  }}
                  onClick={() => isClickable && onStepChange(index)}
                  aria-label={`Step ${index + 1}: ${step.label}`}
                >
                  {state === "complete" ? "✓" : index + 1}
                </button>
              </div>

              {/* Label */}
              <div
                style={{
                  ...s.stepLabel,
                  color:
                    state === "active"
                      ? "#e0e0e0"
                      : state === "complete"
                      ? "#00e5a0"
                      : "#555",
                  cursor: isClickable ? "pointer" : "default",
                  opacity: state === "pending" ? 0.6 : 1,
                }}
                onClick={() => isClickable && onStepChange(index)}
              >
                <span style={s.stepNumber}>STEP {index + 1}</span>
                <span style={s.stepName}>{step.label}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Content area */}
      <div style={s.content}>{steps[activeIndex]?.component}</div>
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    gap: 24,
    alignItems: "flex-start",
    width: "100%",
    fontFamily: "'DM Mono','Fira Code','Cascadia Code',monospace",
  },
  nav: {
    width: 180,
    flexShrink: 0,
    display: "flex",
    flexDirection: "column",
    paddingTop: 4,
  },
  stepRow: {
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
    marginBottom: 0,
  },
  connectorColumn: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    flexShrink: 0,
  },
  connectorLine: {
    width: 2,
    height: 24,
    background: "#222",
    marginBottom: 0,
  },
  circle: {
    width: 28,
    height: 28,
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    fontWeight: 700,
    fontFamily: "inherit",
    border: "none",
    outline: "none",
    transition: "background 0.2s, border-color 0.2s, color 0.2s",
    flexShrink: 0,
    padding: 0,
    marginBottom: 4,
  },
  circleComplete: {
    background: "#00e5a0",
    color: "#000",
    border: "2px solid #00e5a0",
  },
  circleActive: {
    background: "transparent",
    color: "#38b6ff",
    border: "2px solid #38b6ff",
  },
  circlePending: {
    background: "transparent",
    color: "#444",
    border: "2px solid #2a2a2a",
  },
  stepLabel: {
    display: "flex",
    flexDirection: "column",
    gap: 1,
    paddingTop: 4,
    paddingBottom: 20,
    userSelect: "none",
  },
  stepNumber: {
    fontSize: 9,
    letterSpacing: "0.8px",
    color: "#555",
    fontWeight: 600,
  },
  stepName: {
    fontSize: 13,
    fontWeight: 500,
    lineHeight: 1.3,
  },
  content: {
    flex: 1,
    minWidth: 0,
  },
};

export default Stepper;
