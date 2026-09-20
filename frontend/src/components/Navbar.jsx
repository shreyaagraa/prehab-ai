import { useState } from "react";
import { NavLink, Link, useNavigate } from "react-router-dom";
import { Menu, LogOut, User } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import NotificationCenter from "./NotificationCenter";
import NavDrawer from "./NavDrawer";

function Navbar() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    function handleLogout() {
        logout();
        navigate("/login");
    }

    return (
        <>
            <header className="navbar">
                <div className="navbar-brand-wrapper">
                    <button
                        type="button"
                        className="menu-toggle-btn"
                        onClick={() => setIsDrawerOpen(true)}
                        aria-label="Open Navigation Menu"
                        id="hamburger-menu-btn"
                    >
                        <Menu size={22} />
                    </button>

                    <Link to="/" className="brand">
                        <div className="brand-icon">
                            <img src="/logo.png" alt="PreHab AI" className="brand-logo-img" />
                        </div>
                        <div className="brand-text">
                            <span className="brand-name">PreHab AI</span>
                            <span className="brand-tagline">AI Injury Prevention</span>
                        </div>
                    </Link>
                </div>

                <nav className="nav-links">
                    {!user ? (
                        <>
                            <NavLink
                                to="/"
                                end
                                className={({ isActive }) =>
                                    `nav-link ${isActive ? "active" : ""}`
                                }
                            >
                                Home
                            </NavLink>
                            <NavLink
                                to="/login"
                                className={({ isActive }) =>
                                    `nav-link ${isActive ? "active" : ""}`
                                }
                            >
                                Login
                            </NavLink>
                            <NavLink
                                to="/register"
                                className={({ isActive }) =>
                                    `nav-button ${isActive ? "active" : ""}`
                                }
                            >
                                Get Started
                            </NavLink>
                        </>
                    ) : (
                        <>
                            {/* Notification Center Popover Bell */}
                            <NotificationCenter user={user} />

                            <NavLink
                                to="/profile"
                                className={({ isActive }) =>
                                    `nav-link profile-nav-link ${isActive ? "active" : ""}`
                                }
                                title="View Profile"
                            >
                                <User size={18} />
                                <span className="nav-text-desktop">Profile</span>
                            </NavLink>

                            <button
                                className="logout-button"
                                onClick={handleLogout}
                                title="Log out of your account"
                                id="header-logout-btn"
                            >
                                <LogOut size={17} />
                                <span className="nav-text-desktop">Logout</span>
                            </button>
                        </>
                    )}
                </nav>
            </header>

            {/* Slide-out Navigation Drawer */}
            <NavDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
            />
        </>
    );
}

export default Navbar;