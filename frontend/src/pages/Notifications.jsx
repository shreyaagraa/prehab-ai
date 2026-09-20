import { useState, useEffect, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
    Bell,
    CheckCheck,
    AlertTriangle,
    AlertCircle,
    CheckCircle,
    Info,
    Trash2,
    Check,
    ArrowRight,
    Loader2,
    RefreshCw,
    Filter,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import {
    getNotifications,
    markAsRead,
    markAllAsRead,
    deleteNotification,
} from "../api/notifications";

function formatFullDate(dateString) {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

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

export default function Notifications() {
    const { user } = useAuth();
    const navigate = useNavigate();

    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [totalCount, setTotalCount] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filterTab, setFilterTab] = useState("all"); // "all" | "unread" | "risk" | "completed"
    const [markingAll, setMarkingAll] = useState(false);
    const [actionId, setActionId] = useState(null);

    const loadNotifications = useCallback(async () => {
        if (!user) return;
        setLoading(true);
        setError(null);
        try {
            const data = await getNotifications({ limit: 50, skip: 0 });
            setNotifications(data.items || []);
            setTotalCount(data.total || 0);
            setUnreadCount(data.unread_count || 0);
        } catch {
            setError("Failed to load notifications. Please try again.");
        } finally {
            setLoading(false);
        }
    }, [user]);

    useEffect(() => {
        loadNotifications();
    }, [loadNotifications]);

    async function handleMarkOneRead(notificationId) {
        setActionId(notificationId);
        try {
            await markAsRead(notificationId);
            setNotifications((prev) =>
                prev.map((n) =>
                    n.notification_id === notificationId ? { ...n, is_read: true } : n
                )
            );
            setUnreadCount((prev) => Math.max(0, prev - 1));
        } catch {
            // Ignore error
        } finally {
            setActionId(null);
        }
    }

    async function handleMarkAll() {
        if (unreadCount === 0 || markingAll) return;
        setMarkingAll(true);
        try {
            await markAllAsRead();
            setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
            setUnreadCount(0);
        } catch {
            // Ignore error
        } finally {
            setMarkingAll(false);
        }
    }

    async function handleDelete(notificationId) {
        setActionId(notificationId);
        try {
            await deleteNotification(notificationId);
            const target = notifications.find((n) => n.notification_id === notificationId);
            setNotifications((prev) =>
                prev.filter((n) => n.notification_id !== notificationId)
            );
            setTotalCount((prev) => Math.max(0, prev - 1));
            if (target && !target.is_read) {
                setUnreadCount((prev) => Math.max(0, prev - 1));
            }
        } catch {
            // Ignore error
        } finally {
            setActionId(null);
        }
    }

    function handleNavigate(notif) {
        if (!notif.is_read) {
            handleMarkOneRead(notif.notification_id);
        }
        if (notif.action_url) {
            navigate(notif.action_url);
        }
    }

    // Filter items according to active tab
    const filteredNotifications = notifications.filter((notif) => {
        if (filterTab === "unread") return !notif.is_read;
        if (filterTab === "risk") {
            const sev = (notif.severity || "").toUpperCase();
            return (
                sev === "CRITICAL" ||
                sev === "HIGH" ||
                notif.notification_type?.includes("RISK")
            );
        }
        if (filterTab === "completed") {
            return (
                notif.notification_type === "ASSESSMENT_COMPLETED" ||
                notif.notification_type === "CORRECTIVE_PLAN_READY"
            );
        }
        return true;
    });

    function renderSeverityBadge(severity) {
        const sev = (severity || "").toUpperCase();
        if (sev === "CRITICAL") {
            return <span className="notif-page-badge critical">Critical Risk</span>;
        }
        if (sev === "HIGH") {
            return <span className="notif-page-badge high">High Risk</span>;
        }
        if (sev === "WARNING") {
            return <span className="notif-page-badge warning">Moderate Risk</span>;
        }
        return <span className="notif-page-badge info">Info</span>;
    }

    function renderSeverityIcon(severity, type) {
        const sev = (severity || "").toUpperCase();
        if (sev === "CRITICAL") return <AlertCircle size={20} className="text-red-600" />;
        if (sev === "HIGH") return <AlertTriangle size={20} className="text-orange-500" />;
        if (sev === "WARNING") return <AlertTriangle size={20} className="text-amber-500" />;
        if (type === "CORRECTIVE_PLAN_READY") return <CheckCircle size={20} className="text-indigo-600" />;
        return <Info size={20} className="text-blue-500" />;
    }

    return (
        <div className="notifications-page-container">
            {/* Page Header */}
            <div className="notifications-page-header">
                <div>
                    <h1 className="notifications-page-title">Notifications & Alerts</h1>
                    <p className="notifications-page-subtitle">
                        Stay updated on movement quality assessments, biomechanical risk alerts,
                        and corrective exercise plans.
                    </p>
                </div>
                {unreadCount > 0 && (
                    <button
                        type="button"
                        className="notif-page-mark-all-btn"
                        onClick={handleMarkAll}
                        disabled={markingAll}
                    >
                        <CheckCheck size={16} />
                        <span>{markingAll ? "Marking..." : "Mark all as read"}</span>
                    </button>
                )}
            </div>

            {/* Filter Tabs */}
            <div className="notif-page-tabs">
                <button
                    type="button"
                    className={`notif-tab-btn ${filterTab === "all" ? "active" : ""}`}
                    onClick={() => setFilterTab("all")}
                >
                    <span>All</span>
                    <span className="notif-tab-count">{totalCount}</span>
                </button>
                <button
                    type="button"
                    className={`notif-tab-btn ${filterTab === "unread" ? "active" : ""}`}
                    onClick={() => setFilterTab("unread")}
                >
                    <span>Unread</span>
                    {unreadCount > 0 && (
                        <span className="notif-tab-count unread-pill">{unreadCount}</span>
                    )}
                </button>
                <button
                    type="button"
                    className={`notif-tab-btn ${filterTab === "risk" ? "active" : ""}`}
                    onClick={() => setFilterTab("risk")}
                >
                    <span>Risk Alerts</span>
                </button>
                <button
                    type="button"
                    className={`notif-tab-btn ${filterTab === "completed" ? "active" : ""}`}
                    onClick={() => setFilterTab("completed")}
                >
                    <span>Assessments</span>
                </button>
            </div>

            {/* Main Content Feed */}
            <div className="notif-page-content">
                {loading && (
                    <div className="notif-page-loading">
                        <Loader2 size={32} className="spin-icon" />
                        <p>Loading your notifications...</p>
                    </div>
                )}

                {!loading && error && (
                    <div className="notif-page-error">
                        <AlertCircle size={32} />
                        <h3>{error}</h3>
                        <button
                            type="button"
                            className="primary-button"
                            onClick={loadNotifications}
                        >
                            <RefreshCw size={15} />
                            <span>Retry</span>
                        </button>
                    </div>
                )}

                {!loading && !error && filteredNotifications.length === 0 && (
                    <div className="notif-page-empty">
                        <div className="notif-empty-icon-wrap large">
                            <Bell size={36} />
                        </div>
                        <h3>No notifications found</h3>
                        <p>
                            {filterTab === "unread"
                                ? "You're all caught up! No unread notifications."
                                : "No notifications match the selected filter."}
                        </p>
                    </div>
                )}

                {!loading && !error && filteredNotifications.length > 0 && (
                    <div className="notif-page-list">
                        {filteredNotifications.map((notif) => (
                            <div
                                key={notif.notification_id}
                                className={`notif-card ${!notif.is_read ? "unread" : "read"}`}
                            >
                                <div className="notif-card-icon-wrap">
                                    {renderSeverityIcon(notif.severity, notif.notification_type)}
                                </div>

                                <div className="notif-card-body">
                                    <div className="notif-card-header-row">
                                        <div className="notif-card-title-group">
                                            <h4 className="notif-card-title">{notif.title}</h4>
                                            {renderSeverityBadge(notif.severity)}
                                            {!notif.is_read && <span className="notif-card-unread-dot" />}
                                        </div>
                                        <span
                                            className="notif-card-time"
                                            title={formatFullDate(notif.created_at)}
                                        >
                                            {formatRelativeTime(notif.created_at)}
                                        </span>
                                    </div>

                                    <p className="notif-card-message">{notif.message}</p>

                                    <div className="notif-card-actions">
                                        {notif.action_url && (
                                            <button
                                                type="button"
                                                className="notif-action-btn primary"
                                                onClick={() => handleNavigate(notif)}
                                            >
                                                <span>
                                                    {notif.notification_type === "ASSESSMENT_FAILED"
                                                        ? "Go to Assessment"
                                                        : "View Analysis Report"}
                                                </span>
                                                <ArrowRight size={14} />
                                            </button>
                                        )}

                                        {!notif.is_read && (
                                            <button
                                                type="button"
                                                className="notif-action-btn secondary"
                                                onClick={() => handleMarkOneRead(notif.notification_id)}
                                                disabled={actionId === notif.notification_id}
                                                title="Mark as read"
                                            >
                                                <Check size={14} />
                                                <span>Mark read</span>
                                            </button>
                                        )}

                                        <button
                                            type="button"
                                            className="notif-action-btn danger"
                                            onClick={() => handleDelete(notif.notification_id)}
                                            disabled={actionId === notif.notification_id}
                                            title="Dismiss notification"
                                        >
                                            <Trash2 size={14} />
                                            <span>Dismiss</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
