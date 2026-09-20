import { useState } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import {
  Activity,
  Eye,
  EyeOff,
  Mail,
  Lock,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  ShieldCheck,
  TrendingUp,
  Zap,
  Loader2,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import GoogleSignInButton from "../components/GoogleSignInButton";

function Login() {
  const navigate = useNavigate();

  const { login, loginWithGoogle, isAuthenticated } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);

  const [showPassword, setShowPassword] = useState(false);

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

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      await login(email.trim(), password);

      navigate("/dashboard");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to login. Please check your credentials."
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
          typeof detail === "string" ? detail : "Google authentication failed. Please try again."
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
    setError(err.message || "Failed to initiate Google Sign In.");
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

      {/* ── Right Login Panel (50%) ────────────────────────────────────────── */}
      <div className="login-form-panel">
        <div className="login-card-container">
          {/* Card Header */}
          <div className="login-card-header">
            <div className="mobile-brand">
              <img src="/logo.png" alt="PreHab AI" className="mobile-logo-img" />
              <span className="mobile-brand-name">PreHab AI</span>
            </div>
            <h2>Welcome Back</h2>
            <p>Sign in to your account to continue</p>
          </div>

          {/* Global Error Banner */}
          {error && (
            <div className="login-error-alert" role="alert">
              <ShieldAlert size={18} className="alert-icon" />
              <span>{error}</span>
            </div>
          )}

          {/* Google Sign-In Button */}
          <div className="google-btn-wrapper">
            <GoogleSignInButton
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              text="continue_with"
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
              <label htmlFor="login-email">Email Address</label>
              <div className="input-group-icon">
                <Mail size={18} className="field-icon" />
                <input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                />
              </div>
            </div>

            <div className="form-group">
              <div className="label-row">
                <label htmlFor="login-password">Password</label>
                <a
                  href="#forgot"
                  onClick={(e) => {
                    e.preventDefault();
                    alert("Password reset: Please contact your administrator or support@prehab.ai for account recovery.");
                  }}
                  className="forgot-link"
                >
                  Forgot password?
                </a>
              </div>
              <div className="input-group-icon">
                <Lock size={18} className="field-icon" />
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
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

            <div className="form-options-row">
              <label className="remember-me-checkbox">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span>Remember me on this device</span>
              </label>
            </div>

            <button
              type="submit"
              className="login-primary-submit-btn"
              disabled={loading}
              id="login-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="spinner-icon" />
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="login-card-footer">
            <p>
              Don't have an account?{" "}
              <Link to="/register" className="register-link">
                Create one
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

export default Login;