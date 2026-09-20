import { useState } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import {
  Activity,
  Eye,
  EyeOff,
  Mail,
  Lock,
  User,
  Shield,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  ShieldCheck,
  TrendingUp,
  Zap,
  Loader2,
  CheckCircle2,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import GoogleSignInButton from "../components/GoogleSignInButton";

function Register() {
  const navigate = useNavigate();

  const { register, loginWithGoogle, isAuthenticated } = useAuth();

  const [form, setForm] = useState({
    email: "",
    password: "",
    name: "",
    role: "Athlete"
  });

  const [confirmPassword, setConfirmPassword] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(true);

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Account Linking Modal State
  const [linkingCredential, setLinkingCredential] = useState(null);
  const [linkPassword, setLinkPassword] = useState("");
  const [linkingLoading, setLinkingLoading] = useState(false);
  const [linkingError, setLinkingError] = useState("");

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  function updateField(event) {
    setForm({
      ...form,
      [event.target.name]: event.target.value
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (confirmPassword && form.password !== confirmPassword) {
      setError("Passwords do not match. Please verify your password.");
      return;
    }

    if (!acceptTerms) {
      setError("Please accept the Terms of Service to create an account.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      await register(form);
      navigate("/login");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Registration failed. Please check your details and try again."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleSuccess(credential) {
    setError("");
    setLoading(true);

    try {
      await loginWithGoogle(credential);
      navigate("/dashboard");
    } catch (err) {
      const detail = err.response?.data?.detail;
      const status = err.response?.status;

      if (status === 409 || (typeof detail === "string" && detail.includes("ACCOUNT_LINKING_REQUIRED"))) {
        setLinkingCredential(credential);
        setLinkingError("");
        setLinkPassword("");
      } else {
        setError(
          typeof detail === "string" ? detail : "Google sign up failed. Please try again."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmAccountLink(event) {
    event.preventDefault();
    if (!linkingCredential || !linkPassword) return;

    setLinkingError("");
    setLinkingLoading(true);

    try {
      await loginWithGoogle(linkingCredential, linkPassword);
      setLinkingCredential(null);
      navigate("/dashboard");
    } catch (err) {
      setLinkingError(
        err.response?.data?.detail || "Incorrect password. Failed to link account."
      );
    } finally {
      setLinkingLoading(false);
    }
  }

  function handleGoogleError(err) {
    setError(err.message || "Failed to initiate Google Sign Up.");
  }

  return (
    <main className="login-split-page">
      {/* ── Left Hero Panel (50%) ────────────────────────────────────────── */}
      <div className="login-hero-panel">
        <div className="login-hero-overlay" />
        <div className="login-hero-content">
          {/* Hero Header Brand */}
          <Link to="/" className="hero-brand">
            <div className="hero-logo-box">
              <img src="/logo.png" alt="PreHab AI" className="hero-logo-img" />
            </div>
            <div className="hero-brand-text">
              <span className="hero-brand-name">PreHab AI</span>
              <span className="hero-brand-tagline">AI Injury Prevention</span>
            </div>
          </Link>

          {/* Hero Main Copy */}
          <div className="hero-main-copy">
            <div className="hero-eyebrow-pill">
              <Sparkles size={14} />
              <span>AI-POWERED BIOMECHANICAL ANALYSIS</span>
            </div>

            <h1 className="hero-headline">
              Smarter Movement.<br />
              <span className="headline-gradient">Safer Athletes.</span><br />
              Healthier Future.
            </h1>

            <p className="hero-description">
              AI-powered injury risk detection and personalized prevention.
            </p>

            {/* Feature Highlights Grid */}
            <div className="hero-features-grid">
              <div className="hero-feature-card">
                <div className="feature-icon-wrapper cyan">
                  <Activity size={18} />
                </div>
                <div className="feature-text">
                  <strong>AI Pose Analysis</strong>
                  <span>Real-time joint tracking</span>
                </div>
              </div>

              <div className="hero-feature-card">
                <div className="feature-icon-wrapper blue">
                  <ShieldCheck size={18} />
                </div>
                <div className="feature-text">
                  <strong>Injury Risk Detection</strong>
                  <span>LESS biomechanical scoring</span>
                </div>
              </div>

              <div className="hero-feature-card">
                <div className="feature-icon-wrapper indigo">
                  <TrendingUp size={18} />
                </div>
                <div className="feature-text">
                  <strong>Personalized Insights</strong>
                  <span>Tailored corrective plans</span>
                </div>
              </div>

              <div className="hero-feature-card">
                <div className="feature-icon-wrapper teal">
                  <Zap size={18} />
                </div>
                <div className="feature-text">
                  <strong>Better Performance</strong>
                  <span>Movement optimization</span>
                </div>
              </div>
            </div>
          </div>

          {/* Telemetry HUD Floating Badges */}
          <div className="hero-telemetry-badge telemetry-badge-top">
            <div className="telemetry-dot glowing" />
            <div>
              <span className="telemetry-label">Knee Flexion Angle</span>
              <strong className="telemetry-val">142° • Optimal</strong>
            </div>
          </div>

          <div className="hero-telemetry-badge telemetry-badge-bottom">
            <ShieldCheck size={16} color="#10b981" />
            <div>
              <span className="telemetry-label">Injury Risk Status</span>
              <strong className="telemetry-val status-safe">Low Risk (94% Stability)</strong>
            </div>
          </div>
        </div>
      </div>

      {/* ── Right Signup Panel (50%) ────────────────────────────────────────── */}
      <div className="login-form-panel">
        <div className="login-card-container">
          {/* Card Header */}
          <div className="login-card-header">
            <div className="mobile-brand">
              <img src="/logo.png" alt="PreHab AI" className="mobile-logo-img" />
              <span className="mobile-brand-name">PreHab AI</span>
            </div>
            <h2>Create Account</h2>
            <p>Start monitoring movement and injury risk</p>
          </div>

          {/* Global Error Banner */}
          {error && (
            <div className="login-error-alert" role="alert">
              <ShieldAlert size={18} className="alert-icon" />
              <span>{error}</span>
            </div>
          )}

          {/* Google Sign-Up Button */}
          <div className="google-btn-wrapper">
            <GoogleSignInButton
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              text="signup_with"
              disabled={loading}
            />
          </div>

          {/* OR Divider */}
          <div className="login-divider">
            <div className="divider-line" />
            <span className="divider-text">OR</span>
            <div className="divider-line" />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="register-name">Full Name</label>
              <div className="input-group-icon">
                <User size={18} className="field-icon" />
                <input
                  id="register-name"
                  type="text"
                  name="name"
                  value={form.name}
                  onChange={updateField}
                  placeholder="Enter your full name"
                  required
                  autoComplete="name"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="register-email">Email Address</label>
              <div className="input-group-icon">
                <Mail size={18} className="field-icon" />
                <input
                  id="register-email"
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={updateField}
                  placeholder="name@example.com"
                  required
                  autoComplete="email"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="register-password">Password</label>
              <div className="input-group-icon">
                <Lock size={18} className="field-icon" />
                <input
                  id="register-password"
                  type={showPassword ? "text" : "password"}
                  name="password"
                  value={form.password}
                  onChange={updateField}
                  placeholder="Create a password (min 8 chars)"
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="toggle-password-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="register-confirm-password">Confirm Password</label>
              <div className="input-group-icon">
                <Lock size={18} className="field-icon" />
                <input
                  id="register-confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter your password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="toggle-password-btn"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                >
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="register-role">Account Role</label>
              <div className="input-group-icon">
                <Shield size={18} className="field-icon" />
                <select
                  id="register-role"
                  name="role"
                  value={form.role}
                  onChange={updateField}
                  className="role-select"
                >
                  <option value="Athlete">Athlete (Personal Movement & Risk Tracking)</option>
                  <option value="Coach">Coach (Roster & Team Risk Management)</option>
                  <option value="Physiotherapist">Physiotherapist (Rehab & Clinical Protocols)</option>
                  <option value="Sports Scientist">Sports Scientist (Biomechanical Analytics)</option>
                </select>
              </div>
            </div>

            <div className="form-options-row">
              <label className="remember-me-checkbox">
                <input
                  type="checkbox"
                  checked={acceptTerms}
                  onChange={(e) => setAcceptTerms(e.target.checked)}
                />
                <span>I agree to the Terms of Service & Privacy Policy</span>
              </label>
            </div>

            <button
              type="submit"
              className="login-primary-submit-btn"
              disabled={loading}
              id="register-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="spinner-icon" />
                  <span>Creating account...</span>
                </>
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="login-card-footer">
            <p>
              Already have an account?{" "}
              <Link to="/login" className="register-link">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>

      {/* Account Linking Modal */}
      {linkingCredential && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem",
          }}
        >
          <div
            className="auth-card"
            style={{
              maxWidth: "420px",
              width: "100%",
              backgroundColor: "#111827",
              border: "1px solid #374151",
              borderRadius: "0.75rem",
              padding: "1.5rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", color: "#f59e0b", marginBottom: "1rem" }}>
              <ShieldAlert size={24} />
              <h2 style={{ fontSize: "1.25rem", fontWeight: "600", margin: 0, color: "#f9fafb" }}>Link Google Account</h2>
            </div>

            <p style={{ fontSize: "0.875rem", color: "#9ca3af", marginBottom: "1rem" }}>
              An account with this email address already exists. Please enter your existing password to link your Google account.
            </p>

            {linkingError && (
              <div className="error-box" style={{ marginBottom: "1rem" }}>
                {linkingError}
              </div>
            )}

            <form onSubmit={handleConfirmAccountLink}>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: "500", color: "#d1d5db", marginBottom: "0.5rem" }}>
                Account Password
              </label>
              <div className="password-wrapper" style={{ marginBottom: "1.25rem" }}>
                <input
                  type="password"
                  value={linkPassword}
                  onChange={(e) => setLinkPassword(e.target.value)}
                  placeholder="Enter your existing account password"
                  required
                />
              </div>

              <div style={{ display: "flex", gap: "0.75rem" }}>
                <button
                  type="button"
                  onClick={() => setLinkingCredential(null)}
                  style={{
                    flex: 1,
                    padding: "0.625rem",
                    borderRadius: "0.375rem",
                    border: "1px solid #4b5563",
                    backgroundColor: "transparent",
                    color: "#d1d5db",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={linkingLoading}
                  className="primary-button"
                  style={{ flex: 1 }}
                >
                  {linkingLoading ? "Linking..." : "Confirm & Link"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}

export default Register;