import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import UserApi from "../api/UserApi";

function Signup() {
  const [username, setUsername] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string>("");
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    try {
      await UserApi.signup(username, password);
      navigate("/login", { state: { signupSuccess: true } });
    } catch (err) {
      setError(`Signup failed. Try a different username. ${err}`);
    }
  };

  return (
    <div style={s.page}>
      <div style={s.shell}>
        <div style={s.hero}>
          <span style={s.badge}>Create account</span>
          <h1 style={s.title}>Signup</h1>
          <p style={s.subtitle}>
            Register a new account to access the customer workflow securely.
          </p>
        </div>

        <form onSubmit={handleSubmit} style={s.form}>
          <label style={s.field}>
            <span style={s.label}>Username</span>
            <input
              type="text"
              placeholder="Choose a username"
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
              placeholder="Create a password"
              value={password}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
              style={s.input}
            />
          </label>

          {error && <div style={{ ...s.alert, ...s.errorAlert }}>{error}</div>}

          <button type="submit" style={s.primaryButton}>
            Signup
          </button>

          <p style={s.helperText}>
            Already have an account? <Link to="/login" style={s.link}>Login</Link>
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
    border: "1px solid rgba(56, 182, 255, 0.25)",
    color: "#38b6ff",
    background: "rgba(56, 182, 255, 0.06)",
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
    border: "1px solid #38b6ff",
    borderRadius: 14,
    background: "linear-gradient(135deg, #38b6ff, #1f8fe0)",
    color: "#08131c",
    fontSize: "1rem",
    fontWeight: 700,
    cursor: "pointer",
    boxShadow: "0 12px 28px rgba(56, 182, 255, 0.18)",
    transition: "transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease",
  },
  helperText: {
    margin: "0.2rem 0 0",
    color: "#9a9a9a",
    lineHeight: 1.5,
    textAlign: "center",
  },
  link: {
    color: "#00e5a0",
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
  errorAlert: {
    color: "#ffd2d2",
    border: "1px solid rgba(255, 99, 99, 0.28)",
    background: "rgba(255, 99, 99, 0.08)",
  },
};

export default Signup;
