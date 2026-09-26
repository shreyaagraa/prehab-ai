import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

function GoogleSignInButton({ onSuccess, onError, text = "continue_with", disabled = false }) {
  const buttonRef = useRef(null);
  const [gisLoaded, setGisLoaded] = useState(false);
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  useEffect(() => {
    let intervalId = null;

    function checkGisLoaded() {
      if (window.google?.accounts?.id) {
        setGisLoaded(true);
        if (intervalId) clearInterval(intervalId);
      }
    }

    checkGisLoaded();
    if (!window.google?.accounts?.id) {
      intervalId = setInterval(checkGisLoaded, 300);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    if (gisLoaded && googleClientId && buttonRef.current) {
      try {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: (response) => {
            if (response.credential) {
              onSuccess(response.credential);
            } else if (onError) {
              onError(new Error("No credential received from Google."));
            }
          },
        });

        buttonRef.current.innerHTML = "";
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: "outline",
          size: "large",
          type: "standard",
          shape: "rectangular",
          text: text,
          logo_alignment: "left",
          width: "100%",
        });
      } catch (err) {
        console.error("Failed to initialize Google Identity Services:", err);
      }
    }
  }, [gisLoaded, googleClientId, onSuccess, onError, text]);

  const handleCustomClick = () => {
    if (!googleClientId) {
      if (onError) {
        onError(new Error("Google OAuth Client ID is not configured (VITE_GOOGLE_CLIENT_ID)."));
      } else {
        alert("Google OAuth Client ID is not configured in VITE_GOOGLE_CLIENT_ID.");
      }
      return;
    }

    if (window.google?.accounts?.id) {
      window.google.accounts.id.prompt();
    } else if (onError) {
      onError(new Error("Google Identity Services script is still loading. Please try again in a moment."));
    }
  };

  const getButtonText = () => {
    if (disabled) return "Signing in...";
    if (text === "signup_with") return "Sign up with Google";
    if (text === "signin_with") return "Sign in with Google";
    return "Continue with Google";
  };

  return (
    <div className="google-auth-container" style={{ width: "100%" }}>
      {disabled ? (
        <button
          type="button"
          disabled
          className="google-custom-btn loading" style={{ width: "100%" }}
        >
          <Loader2 size={18} className="spinner-icon" />
          <span>Signing in with Google...</span>
        </button>
      ) : gisLoaded && googleClientId ? (
        <div ref={buttonRef} className="google-gis-wrapper" style={{ width: "100%", display: "flex", justifyContent: "center" }} />
      ) : (
        <button
          type="button"
          onClick={handleCustomClick}
          disabled={disabled}
          className="google-custom-btn" style={{ width: "100%" }}
          aria-label={getButtonText()}
        >
          <svg className="google-g-icon" width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              fill="#EA4335"
            />
          </svg>
          <span>{getButtonText()}</span>
        </button>
      )}
    </div>
  );
}

export default GoogleSignInButton;
