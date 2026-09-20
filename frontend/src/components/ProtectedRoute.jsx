import { Navigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "../context/AuthContext";

function ProtectedRoute({ children, allowedRoles }) {
    const { user, isAuthenticated, loading } = useAuth();

    if (loading) {
        return (
            <div className="page-center">
                <div className="spinner"></div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    // Role-based access control (RBAC) frontend boundary check
    if (
        allowedRoles &&
        allowedRoles.length > 0 &&
        (!user?.role || !allowedRoles.includes(user.role))
    ) {
        return (
            <div className="app-layout">
                <main className="dashboard">
                    <div className="empty-state" style={{ minHeight: "60vh" }}>
                        <ShieldAlert
                            size={48}
                            color="#9a4c4c"
                            style={{ marginBottom: "16px" }}
                        />
                        <h2>Access Restricted</h2>
                        <p
                            style={{
                                color: "#788294",
                                maxWidth: "450px",
                                margin: "8px 0 20px",
                                lineHeight: "1.6",
                            }}
                        >
                            Your role <strong>({user?.role || "Unknown"})</strong>{" "}
                            does not have permission to view this page.
                        </p>
                        <a href="/dashboard" className="primary-button">
                            Return to Dashboard
                        </a>
                    </div>
                </main>
            </div>
        );
    }

    return children;
}

export default ProtectedRoute;