```jsx
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Activity } from "lucide-react";

import { useAuth } from "../context/AuthContext";

function Login() {
    const navigate = useNavigate();
    const { login } = useAuth();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(event) {
        event.preventDefault();

        setError("");
        setLoading(true);

        try {
            await login(email.trim(), password);

            // Login and /auth/me both succeeded.
            navigate("/dashboard");
        } catch (error) {
            console.error("Login error:", error);

            setError(
                error.response?.data?.detail ||
                "Unable to login. Please check your credentials."
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="auth-page">
            <div className="auth-card">

                <div className="auth-header">
                    <div className="auth-logo">
                        <img src="/logo.png" alt="PreHab AI" className="auth-logo-img" />
                    </div>

                    <h1>Welcome back</h1>

                    <p>
                        Sign in to your PreHab AI
                        account.
                    </p>
                </div>

                <form onSubmit={handleSubmit}>

                    <div className="form-group">
                        <label htmlFor="email">
                            Email
                        </label>

                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(event) =>
                                setEmail(event.target.value)
                            }
                            placeholder="Enter your email"
                            required
                            autoComplete="email"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">
                            Password
                        </label>

                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(event) =>
                                setPassword(event.target.value)
                            }
                            placeholder="Enter your password"
                            required
                            autoComplete="current-password"
                        />
                    </div>

                    {error && (
                        <div className="auth-error">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="primary-button auth-submit"
                        disabled={loading}
                    >
                        {loading ? "Signing in..." : "Sign In"}
                    </button>
                </form>

                <div className="auth-footer">
                    <span>
                        Don't have an account?
                    </span>

                    <Link to="/register">
                        Create an account
                    </Link>
                </div>

            </div>
        </div>
    );
}

export default Login;
```
