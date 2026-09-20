import React from "react";
import { Gauge, ShieldCheck, AlertTriangle, ShieldAlert, Activity } from "lucide-react";

function getBadgeConfig(level) {
    const l = (level || "").toUpperCase();
    switch (l) {
        case "LOW":
            return {
                label: "Low Risk",
                className: "risk-badge risk-badge--low",
                icon: ShieldCheck,
                bg: "#f0fdf4",
                color: "#16a34a",
                borderColor: "#bbf7d0",
            };
        case "MODERATE":
            return {
                label: "Moderate Risk",
                className: "risk-badge risk-badge--moderate",
                icon: Gauge,
                bg: "#fffbeb",
                color: "#d97706",
                borderColor: "#fde68a",
            };
        case "HIGH":
            return {
                label: "High Risk",
                className: "risk-badge risk-badge--high",
                icon: AlertTriangle,
                bg: "#fff7ed",
                color: "#ea580c",
                borderColor: "#ffedd5",
            };
        case "CRITICAL":
            return {
                label: "Critical Risk",
                className: "risk-badge risk-badge--critical",
                icon: ShieldAlert,
                bg: "#fef2f2",
                color: "#dc2626",
                borderColor: "#fecaca",
            };
        default:
            return {
                label: level || "Pending",
                className: "risk-badge risk-badge--unknown",
                icon: Activity,
                bg: "#f8fafc",
                color: "#64748b",
                borderColor: "#e2e8f0",
            };
    }
}

function RiskBadge({ level }) {
    const config = getBadgeConfig(level);
    const Icon = config.icon;

    return (
        <span
            className={config.className}
            style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "4px 10px",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 600,
                backgroundColor: config.bg,
                color: config.color,
                border: `1px solid ${config.borderColor}`,
                lineHeight: 1,
            }}
        >
            <Icon size={14} style={{ flexShrink: 0 }} />
            <span>{config.label}</span>
        </span>
    );
}

export default RiskBadge;