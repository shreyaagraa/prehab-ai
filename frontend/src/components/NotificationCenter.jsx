import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
    Bell,
    CheckCheck,
    AlertTriangle,
    AlertCircle,
    CheckCircle,
    Info,
    ArrowRight,
    Loader2,
    RefreshCw,
    X,
} from "lucide-react";

import {
    getNotifications,
    getUnreadCount,
    markAsRead,
    markAllAsRead,
} from "../api/notifications";

/**
 * Format timestamp into human-readable relative time.
 */
function formatRelativeTime(dateString) {
    if (!dateString) return "";
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHours = Math.floor(diffMin / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSec < 45) return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function NotificationCenter({ user }) {
    const [isOpen, setIsOpen] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [markingAll, setMarkingAll] = useState(false);

    const dropdownRef = useRef(null);
    const buttonRef = useRef(null);
    const navigate = useNavigate();

    // ── Fetch Unread Count ────────────────────────────────────────────────────
    const fetchUnreadCount = useCallback(async () => {
        if (!user) return;
        try {
            const data = await getUnreadCount();
            setUnreadCount(data.unread_count || 0);
        } catch {
            // Silently fail for background unread badge check
        }
    }, [user]);

    // ── Fetch Notifications List ──────────────────────────────────────────────
    const fetchNotificationList = useCallback(async () => {
        if (!user) return;
        setLoading(true);
        setError(null);
        try {
            const data = await getNotifications({ limit: 8, skip: 0 });
            setNotifications(data.items || []);
            setUnreadCount(data.unread_count || 0);
        } catch (err) {
            setError("Unable to load notifications.");
        } finally {
            setLoading(false);
        }
    }, [user]);

    // Initial fetch and lightweight periodic polling (every 45s)
    useEffect(() => {
        if (!user) return;
        fetchUnreadCount();
        const interval = setInterval(fetchUnreadCount, 45000);
        return () => clearInterval(interval);
    }, [user, fetchUnreadCount]);

    // When dropdown is opened, fetch latest notification list
    useEffect(() => {
        if (isOpen) {
            fetchNotificationList();
        }
    }, [isOpen, fetchNotificationList]);

    // ── Click Outside & Keyboard Listeners ────────────────────────────────────
    useEffect(() => {
        function handleClickOutside(event) {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target) &&
                buttonRef.current &&
                !buttonRef.current.contains(event.target)
            ) {
                setIsOpen(false);
            }
        }

        function handleKeyDown(event) {
            if (event.key === "Escape" && isOpen) {
                setIsOpen(false);
                buttonRef.current?.focus();
            }
        }

        if (isOpen) {
            document.addEventListener("mousedown", handleClickOutside);
            document.addEventListener("keydown", handleKeyDown);
        }
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [isOpen]);

    // ── Actions ───────────────────────────────────────────────────────────────
    async function handleNotificationClick(notif) {
        // Mark read optimistically
        if (!notif.is_read) {
            try {
                await markAsRead(notif.notification_id);
                setNotifications((prev) =>
                    prev.map((item) =>
                        item.notification_id === notif.notification_id
                            ? { ...item, is_read: true }
                            : item
                    )
                );
                setUnreadCount((prev) => Math.max(0, prev - 1));
            } catch {
                // If API fails, proceed with navigation
            }
        }

        setIsOpen(false);

        // Safe internal navigation
        if (notif.action_url) {
            navigate(notif.action_url);
        }
    }

    async function handleMarkAllAsRead(e) {
        e.stopPropagation();
        if (unreadCount === 0 || markingAll) return;
        setMarkingAll(true);
        try {
            await markAllAsRead();
            setNotifications((prev) =>
                prev.map((item) => ({ ...item, is_read: true }))
            );
            setUnreadCount(0);
        } catch {
            // Ignore error on mark all
        } finally {
            setMarkingAll(false);
        }
    }

    // Helper for severity icon & badge color
    function renderSeverityIcon(severity, type) {
        const sev = (severity || "").toUpperCase();
        if (sev === "CRITICAL") {
            return (
                <div className="notif-icon-badge critical" title="Critical Alert">
                    <AlertCircle size={15} />
                </div>
            );
        }
        if (sev === "HIGH") {
            return (
                <div className="notif-icon-badge high" title="High Risk Alert">
                    <AlertTriangle size={15} />
                </div>
            );
        }
        if (sev === "WARNING") {
            return (
                <div className="notif-icon-badge warning" title="Warning / Moderate Risk">
                    <AlertTriangle size={15} />
                </div>
            );
        }
        if (type === "CORRECTIVE_PLAN_READY") {
            return (
                <div className="notif-icon-badge corrective" title="Corrective Action Plan">
                    <CheckCircle size={15} />
                </div>
            );
        }
        return (
            <div className="notif-icon-badge info" title="Information">
                <Info size={15} />
            </div>
        );
    }

    if (!user) return null;

    return (
        <div className="notification-center-container">
            {/* Bell Trigger Button */}
            <button
                ref={buttonRef}
                type="button"
                className={`notif-bell-btn ${isOpen ? "active" : ""}`}
                onClick={() => setIsOpen((prev) => !prev)}
                aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ""}`}
                aria-expanded={isOpen}
                aria-controls="notification-dropdown"
                title="Notifications"
            >
                <Bell size={20} className="notif-bell-icon" />
                {unreadCount > 0 && (
                    <span className="notif-badge" aria-hidden="true">
                        {unreadCount > 99 ? "99+" : unreadCount}
                    </span>
                )}
            </button>

            {/* Dropdown Popover */}
            {isOpen && (
                <div
                    ref={dropdownRef}
                    id="notification-dropdown"
                    className="notif-dropdown"
                    role="region"
                    aria-label="Notification Center"
                >
                    {/* Header */}
                    <div className="notif-header">
                        <div className="notif-header-title">
                            <h3>Notifications</h3>
                            {unreadCount > 0 && (
                                <span className="notif-header-badge">{unreadCount} new</span>
                            )}
                        </div>
                        {unreadCount > 0 && (
                            <button
                                type="button"
                                className="notif-mark-all-btn"
                                onClick={handleMarkAllAsRead}
                                disabled={markingAll}
                                title="Mark all notifications as read"
                            >
                                <CheckCheck size={14} />
                                <span>{markingAll ? "Marking..." : "Mark all read"}</span>
                            </button>
                        )}
                    </div>

                    {/* Content List */}
                    <div className="notif-list-body">
                        {loading && (
                            <div className="notif-state-box loading">
                                <Loader2 size={24} className="spin-icon" />
                                <span>Loading notifications...</span>
                            </div>
                        )}

                        {!loading && error && (
                            <div className="notif-state-box error">
                                <AlertCircle size={24} className="text-red-500" />
                                <p>{error}</p>
                                <button
                                    type="button"
                                    className="notif-retry-btn"
                                    onClick={fetchNotificationList}
                                >
                                    <RefreshCw size={13} />
                                    <span>Retry</span>
                                </button>
                            </div>
                        )}

                        {!loading && !error && notifications.length === 0 && (
                            <div className="notif-state-box empty">
                                <div className="notif-empty-icon-wrap">
                                    <Bell size={28} />
                                </div>
                                <h4>No notifications yet</h4>
                                <p>
                                    When important assessment and account updates become available,
                                    they’ll appear here.
                                </p>
                            </div>
                        )}

                        {!loading &&
                            !error &&
                            notifications.length > 0 &&
                            notifications.map((notif) => (
                                <div
                                    key={notif.notification_id}
                                    className={`notif-item ${!notif.is_read ? "unread" : "read"}`}
                                    onClick={() => handleNotificationClick(notif)}
                                    role="button"
                                    tabIndex={0}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter" || e.key === " ") {
                                            e.preventDefault();
                                            handleNotificationClick(notif);
                                        }
                                    }}
                                >
                                    <div className="notif-item-left">
                                        {renderSeverityIcon(notif.severity, notif.notification_type)}
                                    </div>

                                    <div className="notif-item-content">
                                        <div className="notif-item-title-row">
                                            <span className="notif-item-title">{notif.title}</span>
                                            {!notif.is_read && <span className="notif-unread-dot" />}
                                        </div>
                                        <p className="notif-item-message">{notif.message}</p>
                                        <span className="notif-item-time">
                                            {formatRelativeTime(notif.created_at)}
                                        </span>
                                    </div>
                                </div>
                            ))}
                    </div>

                    {/* Footer */}
                    <div className="notif-footer">
                        <Link
                            to="/notifications"
                            className="notif-view-all-link"
                            onClick={() => setIsOpen(false)}
                        >
                            <span>View All Notifications</span>
                            <ArrowRight size={14} />
                        </Link>
                    </div>
                </div>
            )}
        </div>
    );
}
