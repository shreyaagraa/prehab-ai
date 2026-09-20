import { useEffect } from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import {
    LayoutDashboard,
    Users,
    ClipboardCheck,
    Video,
    UserCircle,
    Shield,
    History,
    FileText,
    LogOut,
    X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const STAFF_ROLES = [
    "Coach",
    "Physiotherapist",
    "Sports Scientist",
    "Administrator",
];

function NavDrawer({ isOpen, onClose }) {
    const auth = useAuth() || {};
    const user = auth.user;
    const logout = auth.logout;
    const role = user?.role;
    const navigate = useNavigate();
    const location = useLocation();

    // Close drawer when location changes
    useEffect(() => {
        onClose();
    }, [location.pathname]);

    // Handle Escape key to close drawer
    useEffect(() => {
        function handleKeyDown(e) {
            if (e.key === "Escape" && isOpen) {
                onClose();
            }
        }
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [isOpen, onClose]);

    // Prevent scrolling when drawer is open on mobile
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "";
        }
        return () => {
            document.body.style.overflow = "";
        };
    }, [isOpen]);

    const getReportsLabel = () => {
        switch (role) {
            case "Athlete":
                return "My Reports";
            case "Coach":
                return "Athlete Reports";
            case "Physiotherapist":
                return "Rehab & Risk Reports";
            case "Sports Scientist":
                return "Biomechanical Reports";
            default:
                return "Reports & Exports";
        }
    };

    const allLinks = [
        {
            name: "Dashboard",
            path: "/dashboard",
            icon: LayoutDashboard,
            roles: null,
        },
        {
            name: "Video Analysis",
            path: "/analysis",
            icon: Video,
            roles: ["Athlete"],
        },
        {
            name: "Analysis History",
            path: "/analysis/history",
            icon: History,
            roles: ["Athlete"],
        },
        {
            name: "Athletes",
            path: "/athletes",
            icon: Users,
            roles: STAFF_ROLES,
        },
        {
            name: "Assessments",
            path: "/assessments",
            icon: ClipboardCheck,
            roles: STAFF_ROLES,
        },
        {
            name: getReportsLabel(),
            path: "/reports",
            icon: FileText,
            roles: null,
        },
        {
            name: "Profile",
            path: "/profile",
            icon: UserCircle,
            roles: null,
        },
    ];

    const visibleLinks = allLinks.filter((link) => {
        if (!link.roles) return true;
        return role && link.roles.includes(role);
    });

    function handleLogout() {
        onClose();
        if (logout) logout();
        navigate("/login");
    }

    return (
        <>
            {/* Backdrop overlay */}
            <div
                className={`drawer-backdrop ${isOpen ? "active" : ""}`}
                onClick={onClose}
                aria-hidden="true"
            />

            {/* Slide-out Drawer */}
            <aside
                className={`nav-drawer ${isOpen ? "open" : ""}`}
                aria-label="Main Navigation Drawer"
                aria-hidden={!isOpen}
            >
                <div className="drawer-header">
                    <span className="drawer-title">Navigation</span>
                    <button
                        type="button"
                        className="drawer-close-btn"
                        onClick={onClose}
                        aria-label="Close Navigation Menu"
                    >
                        <X size={20} />
                    </button>
                </div>

                <nav className="drawer-nav">
                    {visibleLinks.map((link) => {
                        const Icon = link.icon;
                        return (
                            <NavLink
                                key={link.path}
                                to={link.path}
                                end={link.path === "/analysis"}
                                className={({ isActive }) =>
                                    `drawer-link ${isActive ? "active" : ""}`
                                }
                                onClick={onClose}
                            >
                                <Icon size={19} className="drawer-link-icon" />
                                <span>{link.name}</span>
                            </NavLink>
                        );
                    })}
                </nav>

                {user && (
                    <div className="drawer-footer">
                        <div className="user-profile-summary">
                            <div className="user-avatar-mini">
                                {user.name ? user.name.slice(0, 2).toUpperCase() : "AT"}
                            </div>
                            <div className="user-info-mini">
                                <span className="user-name-mini">{user.name || "User"}</span>
                                <span className="user-role-mini">
                                    <Shield size={11} /> {role || "Athlete"}
                                </span>
                            </div>
                        </div>
                        <button
                            type="button"
                            className="drawer-logout-btn"
                            onClick={handleLogout}
                            title="Log out of your account"
                        >
                            <LogOut size={16} />
                        </button>
                    </div>
                )}
            </aside>
        </>
    );
}

export default NavDrawer;
