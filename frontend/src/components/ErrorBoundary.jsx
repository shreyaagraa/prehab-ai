import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error("ErrorBoundary caught an error:", error, errorInfo);
        this.setState({ errorInfo });
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="app-layout">
                    <main className="dashboard">
                        <div className="empty-state" style={{ minHeight: "60vh", padding: "40px 20px" }}>
                            <AlertTriangle size={52} color="#dc2626" style={{ marginBottom: "16px" }} />
                            <h2>Something went wrong</h2>
                            <p style={{ color: "#788294", maxWidth: "500px", margin: "8px 0 20px", lineHeight: "1.6" }}>
                                {this.state.error?.message || "An unexpected rendering error occurred."}
                            </p>
                            <div style={{ display: "flex", gap: "12px" }}>
                                <button type="button" onClick={this.handleReset} className="primary-button">
                                    <RefreshCw size={16} />
                                    Reload Page
                                </button>
                                <a href="/dashboard" className="secondary-button">
                                    Return to Dashboard
                                </a>
                            </div>
                        </div>
                    </main>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
