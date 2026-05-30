import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import UserApi from "../api/UserApi";
import { getOnboardingEligibility, loadOnboardingSession } from "@/api/OnboardingApi";

interface LocationState {
  signupSuccess?: boolean;
}

function Login() {
  const [username, setUsername] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string>("");
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState;

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    try {
      const response = await UserApi.login(username, password);
      const token = response.data.access_token;
      sessionStorage.setItem("jwt_token", token);

      const sessionRes = await UserApi.getSession(token);
      const role = sessionRes.data.role;
      if (role !== "admin") {
        const eligibility = await getOnboardingEligibility();
        if (eligibility.destination === "customer_dashboard") {
          navigate("/customer/dashboard", { replace: true });
          return;
        }
        if (eligibility.destination === "onboarding") {
          await loadOnboardingSession();
        }
      }

      navigate(role === "admin" ? "/admin" : "/");
    } catch (err) {
      setError(`Invalid credentials or server error: ${err}`);
    }
  };

  return (
    <div style={s.page}>
      <div style={s.shell}>
        <div style={s.hero}>
          <span style={s.badge}>Secure access</span>
          <h1 style={s.title}>Login</h1>
          <p style={s.subtitle}>
            Sign in to continue to the biometric and customer workflow.
          </p>
        </div>

        {state?.signupSuccess && (
          <div style={{ ...s.alert, ...s.successAlert }}>
            User created successfully. Please login.
          </div>
        )}

        <form onSubmit={handleSubmit} style={s.form}>
          <label style={s.field}>
            <span style={s.label}>Username</span>
            <input
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUsername(e.target.value)}
              required
              autoComplete="username"
              style={s.input}
            />
          </label>

          <label style={s.field}>
            <span style={s.label}>Password</span>
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              style={s.input}
            />
          </label>

          {error && <div style={{ ...s.alert, ...s.errorAlert }}>{error}</div>}

          <button type="submit" style={s.primaryButton}>
            Login
          </button>

          <p style={s.helperText}>
            Don't have an account? <Link to="/signup" style={s.link}>Create one</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "2rem 1rem",
    background:
      "radial-gradient(circle at top, rgba(0, 229, 160, 0.08), transparent 34%), radial-gradient(circle at bottom right, rgba(56, 182, 255, 0.08), transparent 28%), #050505",
  },
  shell: {
    width: "100%",
    maxWidth: 460,
    border: "1px solid #1f1f1f",
    borderRadius: 24,
    padding: "2rem",
    background: "linear-gradient(180deg, rgba(13,13,13,0.98), rgba(8,8,8,0.98))",
    boxShadow: "0 24px 80px rgba(0, 0, 0, 0.45)",
  },
  hero: {
    marginBottom: "1.5rem",
  },
  badge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "0.35rem 0.7rem",
    borderRadius: 999,
    border: "1px solid rgba(0, 229, 160, 0.25)",
    color: "#00e5a0",
    background: "rgba(0, 229, 160, 0.06)",
    fontSize: "0.76rem",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    marginBottom: "0.85rem",
  },
  title: {
    fontSize: "2rem",
    lineHeight: 1.1,
    margin: 0,
    color: "#f4f4f4",
  },
  subtitle: {
    margin: "0.75rem 0 0",
    color: "#a1a1a1",
    lineHeight: 1.6,
    fontSize: "0.98rem",
  },
  form: {
    display: "grid",
    gap: "1rem",
  },
  field: {
    display: "grid",
    gap: "0.5rem",
  },
  label: {
    color: "#d9d9d9",
    fontSize: "0.92rem",
    fontWeight: 600,
    letterSpacing: "0.01em",
  },
  input: {
    width: "100%",
    borderRadius: 14,
    border: "1px solid #262626",
    background: "#0b0b0b",
    color: "#f3f3f3",
    padding: "0.95rem 1rem",
    fontSize: "1rem",
    outline: "none",
    transition: "border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease",
  },
  primaryButton: {
    marginTop: "0.25rem",
    minHeight: 48,
    border: "1px solid #00e5a0",
    borderRadius: 14,
    background: "linear-gradient(135deg, #00e5a0, #14c48e)",
    color: "#04110d",
    fontSize: "1rem",
    fontWeight: 700,
    cursor: "pointer",
    boxShadow: "0 12px 28px rgba(0, 229, 160, 0.18)",
    transition: "transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease",
  },
  helperText: {
    margin: "0.2rem 0 0",
    color: "#9a9a9a",
    lineHeight: 1.5,
    textAlign: "center",
  },
  link: {
    color: "#38b6ff",
    textDecoration: "none",
    fontWeight: 600,
  },
  alert: {
    borderRadius: 14,
    padding: "0.85rem 1rem",
    lineHeight: 1.5,
    fontSize: "0.96rem",
    marginBottom: "0.25rem",
  },
  successAlert: {
    color: "#d9fff3",
    border: "1px solid rgba(0, 229, 160, 0.28)",
    background: "rgba(0, 229, 160, 0.08)",
  },
  errorAlert: {
    color: "#ffd2d2",
    border: "1px solid rgba(255, 99, 99, 0.28)",
    background: "rgba(255, 99, 99, 0.08)",
  },
};

export default Login;
