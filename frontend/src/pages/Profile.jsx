import { useState, useEffect } from "react";
import {
    User,
    Shield,
    Activity,
    CheckCircle2,
    AlertCircle,
    Edit3,
    Save,
    X,
    Dumbbell,
    UserCheck,
    Ruler,
    Weight as WeightIcon,
    Calendar,
    Sparkles,
    Loader2,
    Plus,
    Trash2,
    Info,
    Flame,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import {
    getMyAthleteProfile,
    upsertMyAthleteProfile,
} from "../api/athletes";
import {
    getMyInjuryHistory,
    addMyInjuryRecord,
    deleteMyInjuryRecord,
} from "../api/injuryHistory";

const CORE_FIELDS = ["sport", "position", "age", "height", "weight", "dominant_leg"];
const RPE_DESCRIPTORS = {
    1: "1 — Very easy",
    2: "2 — Easy",
    3: "3 — Easy/Moderate",
    4: "4 — Moderate",
    5: "5 — Somewhat hard",
    6: "6 — Hard",
    7: "7 — Very hard",
    8: "8 — Extremely hard",
    9: "9 — Near maximum effort",
    10: "10 — Maximum effort",
};

const FATIGUE_DESCRIPTORS = {
    1: "1 — Very fresh",
    2: "2 — Fresh",
    3: "3 — Light fatigue",
    4: "4 — Mild fatigue",
    5: "5 — Moderate fatigue",
    6: "6 — Noticeable fatigue",
    7: "7 — High fatigue",
    8: "8 — Very tired",
    9: "9 — Exhausted",
    10: "10 — Extremely fatigued",
};

function Profile() {
    const { user } = useAuth();
    const isAthlete = user?.role === "Athlete";

    // Athlete profile state
    const [profile, setProfile] = useState(null);
    const [loadingProfile, setLoadingProfile] = useState(true);
    const [profileError, setProfileError] = useState("");

    // Injury history records state
    const [injuries, setInjuries] = useState([]);
    const [loadingInjuries, setLoadingInjuries] = useState(false);

    // Form field state
    const [sport, setSport] = useState("");
    const [position, setPosition] = useState("");
    const [dominantLeg, setDominantLeg] = useState("Right");
    const [age, setAge] = useState("");
    const [height, setHeight] = useState("");
    const [weight, setWeight] = useState("");

    // Training load fields
    const [sessionsPerWeek, setSessionsPerWeek] = useState("");
    const [sessionDuration, setSessionDuration] = useState("");
    const [sessionRpe, setSessionRpe] = useState("");

    // Fatigue
    const [fatigueLevel, setFatigueLevel] = useState("");

    // Injury confirmation status
    const [hasInjuryHistory, setHasInjuryHistory] = useState("UNKNOWN");

    // Add new injury form state inside modal
    const [newInjuryType, setNewInjuryType] = useState("");
    const [newBodyPart, setNewBodyPart] = useState("Knee");
    const [newInjuryDate, setNewInjuryDate] = useState("");
    const [newInjuryStatus, setNewInjuryStatus] = useState("Recovered");
    const [addingInjury, setAddingInjury] = useState(false);

    // Mode & save state
    const [isEditing, setIsEditing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saveMsg, setSaveMsg] = useState({ type: "", text: "" });

    // Load profile & injury history on mount
    useEffect(() => {
        async function fetchProfileData() {
            setLoadingProfile(true);
            setProfileError("");

            try {
                const data = await getMyAthleteProfile();
                setProfile(data);
                populateForm(data);
            } catch (err) {
                if (err.response?.status === 404 || err.response?.status === 403) {
                    setProfile(null);
                } else {
                    setProfileError(
                        err.response?.data?.detail || "Could not load athlete profile."
                    );
                }
            } finally {
                setLoadingProfile(false);
            }

            try {
                setLoadingInjuries(true);
                const injuryRecords = await getMyInjuryHistory();
                setInjuries(injuryRecords);
            } catch (err) {
                console.warn("Could not load injury history records", err);
            } finally {
                setLoadingInjuries(false);
            }
        }

        fetchProfileData();
    }, []);

    function populateForm(data) {
        if (!data) return;
        setSport(data.sport ?? "");
        setPosition(data.position ?? "");
        setDominantLeg(data.dominant_leg ?? "Right");
        setAge(data.age != null ? String(data.age) : "");
        setHeight(data.height != null ? String(data.height) : "");
        setWeight(data.weight != null ? String(data.weight) : "");
        setSessionsPerWeek(data.training_sessions_per_week != null ? String(data.training_sessions_per_week) : "");
        setSessionDuration(data.average_session_duration != null ? String(data.average_session_duration) : "");
        setSessionRpe(data.average_session_rpe != null ? String(data.average_session_rpe) : "");
        setFatigueLevel(data.current_fatigue_level != null ? String(data.current_fatigue_level) : "");
        setHasInjuryHistory(data.has_injury_history ?? "UNKNOWN");
    }

    // Lock background scrolling when modal is open
    useEffect(() => {
        if (isEditing) {
            document.body.classList.add("modal-open");
        } else {
            document.body.classList.remove("modal-open");
        }
        return () => {
            document.body.classList.remove("modal-open");
        };
    }, [isEditing]);

    // Calculate derived weekly workload
    const calcWorkload =
        sessionsPerWeek !== "" && sessionDuration !== "" && sessionRpe !== ""
            ? Number(sessionsPerWeek) * Number(sessionDuration) * Number(sessionRpe)
            : null;

    // Save handler
    async function handleSave(event) {
        event.preventDefault();
        setSaving(true);
        setSaveMsg({ type: "", text: "" });

        const payload = {
            sport: sport.trim() || null,
            position: position.trim() || null,
            dominant_leg: dominantLeg || null,
            age: age !== "" ? Number(age) : null,
            height: height !== "" ? Number(height) : null,
            weight: weight !== "" ? Number(weight) : null,
            training_sessions_per_week: sessionsPerWeek !== "" ? Number(sessionsPerWeek) : null,
            average_session_duration: sessionDuration !== "" ? Number(sessionDuration) : null,
            average_session_rpe: sessionRpe !== "" ? Number(sessionRpe) : null,
            current_fatigue_level: fatigueLevel !== "" ? Number(fatigueLevel) : null,
            has_injury_history: hasInjuryHistory || "UNKNOWN",
        };

        try {
            const updated = await upsertMyAthleteProfile(payload);
            setProfile(updated);
            setSaveMsg({ type: "success", text: "Athlete profile saved successfully!" });
            setIsEditing(false);
        } catch (err) {
            const detail =
                err.response?.data?.detail ||
                "Unable to save profile. Please check inputs and try again.";
            setSaveMsg({ type: "error", text: detail });
        } finally {
            setSaving(false);
        }
    }

    async function handleAddInjury(e) {
        e.preventDefault();
        if (!newInjuryType.trim()) return;

        setAddingInjury(true);
        try {
            const created = await addMyInjuryRecord({
                injury_type: newInjuryType.trim(),
                body_part: newBodyPart,
                injury_date: newInjuryDate || null,
                status: newInjuryStatus,
            });
            setInjuries((prev) => [created, ...prev]);
            setHasInjuryHistory("YES");
            setNewInjuryType("");
            setNewInjuryDate("");
        } catch (err) {
            alert(err.response?.data?.detail || "Could not add injury record.");
        } finally {
            setAddingInjury(false);
        }
    }

    async function handleDeleteInjury(injuryId) {
        if (!confirm("Are you sure you want to delete this injury record?")) return;

        try {
            await deleteMyInjuryRecord(injuryId);
            const remaining = injuries.filter((i) => i.injury_id !== injuryId);
            setInjuries(remaining);
            if (remaining.length === 0 && hasInjuryHistory === "YES") {
                setHasInjuryHistory("NO");
            }
        } catch (err) {
            alert("Failed to delete injury record.");
        }
    }

    function handleOpenEdit() {
        populateForm(profile);
        setSaveMsg({ type: "", text: "" });
        setIsEditing(true);
    }

    function handleCancel() {
        setIsEditing(false);
        setSaveMsg({ type: "", text: "" });
        populateForm(profile);
    }

    const completedFieldsCount = CORE_FIELDS.filter(
        (f) => profile && profile[f] !== null && profile[f] !== undefined && profile[f] !== ""
    ).length;

    const completionPercentage = Math.round((completedFieldsCount / CORE_FIELDS.length) * 100);
    const isComplete = completionPercentage === 100;

    const bmi =
        profile?.height && profile?.weight
            ? (profile.weight / Math.pow(profile.height / 100, 2)).toFixed(1)
            : null;

    return (
        <div className="app-layout">
            <main className="dashboard">
                {isAthlete ? (
                    <>
                        {/* ── Page Header ─────────────────────────────────────────────── */}
                        <div className="page-header">
                            <div>
                                <span className="eyebrow">ATHLETE WORKSPACE</span>
                                <h1>Athlete Profile & Risk Context</h1>
                                <p>Manage physical biometrics, training workload, fatigue indicators, and medical injury history.</p>
                            </div>

                            <button
                                type="button"
                                onClick={handleOpenEdit}
                                className="primary-button"
                                id="edit-profile-btn"
                                disabled={loadingProfile}
                            >
                                <Edit3 size={16} />
                                Edit Profile
                            </button>
                        </div>

                        {loadingProfile && (
                            <div className="loading-container" style={{ padding: "40px 0" }}>
                                <div className="spinner" />
                                <span>Loading athlete profile…</span>
                            </div>
                        )}

                        {profileError && (
                            <div className="error-box" style={{ marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
                                <AlertCircle size={16} />
                                <span>{profileError}</span>
                            </div>
                        )}

                        {saveMsg.text && (
                            <div className={saveMsg.type === "success" ? "success-box" : "error-box"} style={{ marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
                                {saveMsg.type === "success" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                                <span>{saveMsg.text}</span>
                            </div>
                        )}

                        {/* ── Profile Header Card ──────────────────────────────────────── */}
                        <div className="profile-header-card">
                            <div className="profile-avatar-large">
                                {user?.name ? user.name.slice(0, 2).toUpperCase() : "AT"}
                            </div>

                            <div className="profile-header-info">
                                <div className="profile-name-row">
                                    <h2>{user?.name || "Athlete Account"}</h2>
                                    <span className="role-badge">{user?.role || "Athlete"}</span>
                                </div>
                                <p className="profile-email">{user?.email || "—"}</p>
                                <p className="profile-subtitle">
                                    {profile?.sport
                                        ? `${profile.sport} • ${profile.position || "General Player"} • Leg: ${profile.dominant_leg || "Right"}`
                                        : "Athlete Profile Configured"}
                                </p>
                            </div>

                            <div className="profile-completion-box">
                                <div className="completion-ring-meta">
                                    <span className="completion-title">Profile Completeness</span>
                                    <strong className={`completion-pct ${isComplete ? "text-emerald" : "text-amber"}`}>
                                        {completionPercentage}%
                                    </strong>
                                </div>
                                <div className="completion-track">
                                    <div
                                        className={`completion-fill ${isComplete ? "bg-emerald" : "bg-amber"}`}
                                        style={{ width: `${completionPercentage}%` }}
                                    />
                                </div>
                                <span className="completion-subtext">
                                    {isComplete
                                        ? "Full biometrics active for AI risk scoring"
                                        : `${CORE_FIELDS.length - completedFieldsCount} field(s) required for optimal scoring`}
                                </span>
                            </div>
                        </div>

                        {/* ── Profile Info Cards Grid (5 Sections for Athlete) ───────── */}
                        <div className="profile-cards-grid">
                            {/* Section 1: Basic Information */}
                            <section className="panel card-panel">
                                <div className="panel-header">
                                    <div>
                                        <h2>1. Basic & Biometric Information</h2>
                                        <p>Age, height, weight, and calculated BMI</p>
                                    </div>
                                    <UserCheck size={20} className="text-purple" />
                                </div>

                                <div className="physical-stats-grid">
                                    <div className="physical-stat-box">
                                        <div className="box-icon">
                                            <Calendar size={18} />
                                        </div>
                                        <span className="box-label">Age</span>
                                        <strong className="box-val">{profile?.age != null ? `${profile.age} yrs` : "—"}</strong>
                                    </div>

                                    <div className="physical-stat-box">
                                        <div className="box-icon">
                                            <Ruler size={18} />
                                        </div>
                                        <span className="box-label">Height</span>
                                        <strong className="box-val">{profile?.height != null ? `${profile.height} cm` : "—"}</strong>
                                    </div>

                                    <div className="physical-stat-box">
                                        <div className="box-icon">
                                            <WeightIcon size={18} />
                                        </div>
                                        <span className="box-label">Weight</span>
                                        <strong className="box-val">{profile?.weight != null ? `${profile.weight} kg` : "—"}</strong>
                                    </div>

                                    <div className="physical-stat-box">
                                        <div className="box-icon">
                                            <Sparkles size={18} />
                                        </div>
                                        <span className="box-label">Calculated BMI</span>
                                        <strong className="box-val">{bmi ? `${bmi}` : "—"}</strong>
                                    </div>
                                </div>
                            </section>

                            {/* Section 2: Sport Information */}
                            <section className="panel card-panel">
                                <div className="panel-header">
                                    <div>
                                        <h2>2. Sport Information</h2>
                                        <p>Sport discipline, position, and dominant limb</p>
                                    </div>
                                    <Dumbbell size={20} className="text-purple" />
                                </div>

                                <div className="profile-detail-rows">
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Sport Discipline</span>
                                        <strong className="detail-value">{profile?.sport || "Not configured"}</strong>
                                    </div>

                                    <div className="profile-detail-row">
                                        <span className="detail-label">Position / Event</span>
                                        <strong className="detail-value">{profile?.position || "Not configured"}</strong>
                                    </div>

                                    <div className="profile-detail-row">
                                        <span className="detail-label">Dominant Leg</span>
                                        <strong className="detail-value">{profile?.dominant_leg || "Not specified"}</strong>
                                    </div>
                                </div>
                            </section>

                            {/* Section 3: Training Information */}
                            <section className="panel card-panel">
                                <div className="panel-header">
                                    <div>
                                        <h2>3. Training Information</h2>
                                        <p>Weekly session volume, duration, RPE, and workload</p>
                                    </div>
                                    <Activity size={20} className="text-purple" />
                                </div>

                                <div className="profile-detail-rows">
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Sessions / Week</span>
                                        <strong className="detail-value">
                                            {profile?.training_sessions_per_week != null ? `${profile.training_sessions_per_week} sessions` : "Not provided"}
                                        </strong>
                                    </div>

                                    <div className="profile-detail-row">
                                        <span className="detail-label">Avg Session Duration</span>
                                        <strong className="detail-value">
                                            {profile?.average_session_duration != null ? `${profile.average_session_duration} mins` : "Not provided"}
                                        </strong>
                                    </div>

                                    <div className="profile-detail-row">
                                        <span className="detail-label">Typical Effort (RPE)</span>
                                        <strong className="detail-value">
                                            {profile?.average_session_rpe != null ? `${profile.average_session_rpe} / 10` : "Not provided"}
                                        </strong>
                                    </div>

                                    <div className="profile-detail-row" style={{ background: "rgba(124, 58, 237, 0.05)", borderRadius: 6, padding: "8px 12px" }}>
                                        <span className="detail-label" style={{ fontWeight: 700, color: "#7c3aed" }}>Weekly Training Load</span>
                                        <strong className="detail-value" style={{ color: "#7c3aed", fontSize: 16 }}>
                                            {profile?.weekly_training_load != null
                                                ? `${profile.weekly_training_load} AU`
                                                : profile?.training_load != null
                                                    ? `${profile.training_load} AU`
                                                    : "Unavailable"}
                                        </strong>
                                    </div>
                                </div>
                            </section>

                            {/* Section 4: Current Fatigue */}
                            <section className="panel card-panel">
                                <div className="panel-header">
                                    <div>
                                        <h2>4. Current Fatigue</h2>
                                        <p>Self-reported fatigue indicator scale (1–10)</p>
                                    </div>
                                    <Flame size={20} className="text-amber" />
                                </div>

                                <div style={{ padding: "12px 0" }}>
                                    {profile?.current_fatigue_level != null ? (
                                        <div className="fatigue-display-card">
                                            <div className="fatigue-score-pill">
                                                Level {profile.current_fatigue_level} / 10
                                            </div>
                                            <p className="fatigue-desc">
                                                {FATIGUE_DESCRIPTORS[profile.current_fatigue_level] || `Level ${profile.current_fatigue_level}`}
                                            </p>
                                        </div>
                                    ) : (
                                        <p className="text-muted" style={{ fontSize: 14 }}>Fatigue level has not been reported.</p>
                                    )}
                                </div>
                            </section>

                            {/* Section 5: Injury History */}
                            <section className="panel card-panel full-width-panel">
                                <div className="panel-header">
                                    <div>
                                        <h2>5. Injury History</h2>
                                        <p>Confirmed prior musculoskeletal injuries and recovery status</p>
                                    </div>
                                    <Shield size={20} className="text-purple" />
                                </div>

                                <div className="injury-history-container">
                                    <div className="injury-status-summary" style={{ marginBottom: 16 }}>
                                        <span>Previous Injury Confirmed: </span>
                                        <strong style={{ textTransform: "uppercase", color: profile?.has_injury_history === "YES" ? "#ea580c" : profile?.has_injury_history === "NO" ? "#16a34a" : "#64748b" }}>
                                            {profile?.has_injury_history || "UNKNOWN / NOT PROVIDED"}
                                        </strong>
                                    </div>

                                    {injuries.length > 0 ? (
                                        <div className="injury-table-wrapper">
                                            <table className="injury-table">
                                                <thead>
                                                    <tr>
                                                        <th>Injury Type</th>
                                                        <th>Body Region</th>
                                                        <th>Approximate Date</th>
                                                        <th>Status</th>
                                                        <th>Action</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {injuries.map((inj) => (
                                                        <tr key={inj.injury_id}>
                                                            <td><strong>{inj.injury_type || "—"}</strong></td>
                                                            <td>{inj.body_part || "—"}</td>
                                                            <td>{inj.injury_date || "Approximate"}</td>
                                                            <td>
                                                                <span className={`status-badge ${inj.status === "Currently affected" ? "status-affected" : "status-recovered"}`}>
                                                                    {inj.status || "Recovered"}
                                                                </span>
                                                            </td>
                                                            <td>
                                                                <button
                                                                    type="button"
                                                                    onClick={() => handleDeleteInjury(inj.injury_id)}
                                                                    className="icon-btn-danger"
                                                                    title="Delete Record"
                                                                >
                                                                    <Trash2 size={14} />
                                                                </button>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : (
                                        <div className="empty-injury-box">
                                            <p>No prior injury records registered in database.</p>
                                        </div>
                                    )}
                                </div>
                            </section>
                        </div>
                    </>
                ) : (
                    /* ── COACH PROFILE VIEW (ROLE-SPECIFIC & PROFESSIONAL) ───── */
                    <>
                        {/* ── Page Header ─────────────────────────────────────────────── */}
                        <div className="page-header">
                            <div>
                                <span className="eyebrow">COACH WORKSPACE</span>
                                <h1>Coach Profile & Staff Details</h1>
                                <p>Manage personal details, staff identity, roster administration credentials, and account security.</p>
                            </div>
                        </div>

                        {/* ── Profile Header Card ──────────────────────────────────────── */}
                        <div className="profile-header-card">
                            <div className="profile-avatar-large" style={{ background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)" }}>
                                {user?.name ? user.name.slice(0, 2).toUpperCase() : "CH"}
                            </div>

                            <div className="profile-header-info">
                                <div className="profile-name-row">
                                    <h2>{user?.name || "Coach Account"}</h2>
                                    <span className="role-badge" style={{ background: "rgba(99, 102, 241, 0.2)", color: "#818cf8", border: "1px solid #6366f1" }}>
                                        {user?.role || "Coach"}
                                    </span>
                                </div>
                                <p className="profile-email">{user?.email || "—"}</p>
                                <p className="profile-subtitle">
                                    Head Coach & Roster Supervisor • PreHab AI Clinical Monitoring
                                </p>
                            </div>

                            <div className="profile-completion-box" style={{ minWidth: 220 }}>
                                <div className="completion-ring-meta">
                                    <span className="completion-title">Account Status</span>
                                    <strong className="completion-pct text-emerald">Active Staff ✓</strong>
                                </div>
                                <div className="completion-track">
                                    <div className="completion-fill bg-emerald" style={{ width: "100%" }} />
                                </div>
                                <span className="completion-subtext" style={{ marginTop: 6 }}>
                                    Full Coach & Roster Management Access
                                </span>
                            </div>
                        </div>

                        {/* ── 3 Clear Sections for Coach ────────────────────────────── */}
                        <div className="profile-cards-grid">
                            {/* Section 1: Personal Information */}
                            <section className="panel card-panel">
                                <div className="panel-header">
                                    <div>
                                        <h2>1. Personal Information</h2>
                                        <p>Contact details and identity information</p>
                                    </div>
                                    <UserCheck size={20} className="text-purple" />
                                </div>

                                <div className="profile-detail-rows">
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Full Name</span>
                                        <strong className="detail-value">{user?.name || "—"}</strong>
                                    </div>
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Email Address</span>
                                        <strong className="detail-value">{user?.email || "—"}</strong>
                                    </div>
                                    <div className="profile-detail-row">
                                        <span className="detail-label">User Role</span>
                                        <strong className="detail-value">{user?.role || "Coach"}</strong>
                                    </div>
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Phone / Contact</span>
                                        <strong className="detail-value">{user?.phone || "Not specified"}</strong>
                                    </div>
                                </div>
                            </section>

                            {/* Section 2: Coaching Information */}
                            <section className="panel card-panel">
                                <div className="panel-header">
                                    <div>
                                        <h2>2. Coaching & Specialization</h2>
                                        <p>Primary focus and team roster oversight</p>
                                    </div>
                                    <Dumbbell size={20} className="text-purple" />
                                </div>

                                <div className="profile-detail-rows">
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Staff Designation</span>
                                        <strong className="detail-value">Head Coach & Roster Supervisor</strong>
                                    </div>
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Primary Specialization</span>
                                        <strong className="detail-value">Biomechanical Risk & Movement Analysis</strong>
                                    </div>
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Roster Access Scope</span>
                                        <strong className="detail-value">Assigned Team Roster & Movement Assessments</strong>
                                    </div>
                                </div>
                            </section>

                            {/* Section 3: Account & Security */}
                            <section className="panel card-panel full-width-panel">
                                <div className="panel-header">
                                    <div>
                                        <h2>3. Account & Security</h2>
                                        <p>Security credentials and authentication details</p>
                                    </div>
                                    <Shield size={20} className="text-purple" />
                                </div>

                                <div className="profile-detail-rows" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Account Verification Status</span>
                                        <strong className="detail-value" style={{ color: "#10b981" }}>
                                            Active & Verified Staff
                                        </strong>
                                    </div>
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Member Since</span>
                                        <strong className="detail-value">
                                            {user?.created_at
                                                ? new Date(user.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
                                                : "Active Account"}
                                        </strong>
                                    </div>
                                    <div className="profile-detail-row">
                                        <span className="detail-label">Authentication Method</span>
                                        <strong className="detail-value">OAuth2 JWT Bearer Security</strong>
                                    </div>
                                </div>
                            </section>
                        </div>
                    </>
                )}
            </main>

            {/* ── Edit Profile Modal ─────────────────────────────────────────── */}
            {isEditing && (
                <div
                    className="modal-overlay"
                    onClick={() => !saving && handleCancel()}
                    role="dialog"
                    aria-modal="true"
                    aria-label="Edit Athlete Profile & Biometrics"
                >
                    <div
                        className="modal-content profile-edit-modal-large"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="modal-header profile-modal-header">
                            <div className="profile-modal-header-text">
                                <div className="profile-modal-icon">
                                    <Edit3 size={18} />
                                </div>
                                <div>
                                    <h3 className="profile-modal-title">Edit Athlete Profile</h3>
                                    <p className="profile-modal-subtitle">
                                        Configure physical, sport, training workload, fatigue, and injury history
                                    </p>
                                </div>
                            </div>
                            <button
                                type="button"
                                className="modal-close-btn"
                                onClick={handleCancel}
                                title="Close"
                                disabled={saving}
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <form onSubmit={handleSave}>
                            <div className="modal-body profile-modal-body">
                                {saveMsg.type === "error" && saveMsg.text && (
                                    <div className="error-box" style={{ marginBottom: 18 }}>
                                        <AlertCircle size={15} />
                                        <span>{saveMsg.text}</span>
                                    </div>
                                )}

                                {/* Section 1: Basic Biometrics */}
                                <div className="form-section">
                                    <h4 className="form-section-heading">1. Basic Information</h4>
                                    <div className="form-grid">
                                        <div className="form-group">
                                            <label htmlFor="field-age">Age (years)</label>
                                            <input
                                                id="field-age"
                                                type="number"
                                                min={1}
                                                max={120}
                                                placeholder="e.g. 22"
                                                value={age}
                                                onChange={(e) => setAge(e.target.value)}
                                            />
                                        </div>

                                        <div className="form-group">
                                            <label htmlFor="field-height">Height (cm)</label>
                                            <input
                                                id="field-height"
                                                type="number"
                                                min={1}
                                                max={300}
                                                step="0.1"
                                                placeholder="e.g. 182"
                                                value={height}
                                                onChange={(e) => setHeight(e.target.value)}
                                            />
                                        </div>

                                        <div className="form-group">
                                            <label htmlFor="field-weight">Weight (kg)</label>
                                            <input
                                                id="field-weight"
                                                type="number"
                                                min={1}
                                                max={500}
                                                step="0.1"
                                                placeholder="e.g. 78"
                                                value={weight}
                                                onChange={(e) => setWeight(e.target.value)}
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Section 2: Sport Info */}
                                <div className="form-section">
                                    <h4 className="form-section-heading">2. Sport Information</h4>
                                    <div className="form-grid">
                                        <div className="form-group">
                                            <label htmlFor="field-sport">Sport / Discipline</label>
                                            <input
                                                id="field-sport"
                                                type="text"
                                                placeholder="e.g. Football, Running, Basketball, Other"
                                                value={sport}
                                                onChange={(e) => setSport(e.target.value)}
                                            />
                                        </div>

                                        <div className="form-group">
                                            <label htmlFor="field-position">Position / Event</label>
                                            <input
                                                id="field-position"
                                                type="text"
                                                placeholder="e.g. Midfielder, Sprinter, Guard"
                                                value={position}
                                                onChange={(e) => setPosition(e.target.value)}
                                            />
                                        </div>

                                        <div className="form-group">
                                            <label htmlFor="field-leg">Dominant Leg</label>
                                            <select
                                                id="field-leg"
                                                value={dominantLeg}
                                                onChange={(e) => setDominantLeg(e.target.value)}
                                            >
                                                <option value="Right">Right</option>
                                                <option value="Left">Left</option>
                                                <option value="Ambidextrous">Ambidextrous</option>
                                                <option value="Unknown">Unknown</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>

                                {/* Section 3: Training Load */}
                                <div className="form-section">
                                    <h4 className="form-section-heading">3. Training Workload Inputs</h4>
                                    <div className="form-grid">
                                        <div className="form-group">
                                            <label htmlFor="field-sessions">Training Sessions / Week</label>
                                            <input
                                                id="field-sessions"
                                                type="number"
                                                min={0}
                                                max={50}
                                                placeholder="e.g. 4"
                                                value={sessionsPerWeek}
                                                onChange={(e) => setSessionsPerWeek(e.target.value)}
                                            />
                                        </div>

                                        <div className="form-group">
                                            <label htmlFor="field-duration">Avg Session Duration (min)</label>
                                            <input
                                                id="field-duration"
                                                type="number"
                                                min={0}
                                                max={1440}
                                                placeholder="e.g. 60"
                                                value={sessionDuration}
                                                onChange={(e) => setSessionDuration(e.target.value)}
                                            />
                                        </div>

                                        <div className="form-group">
                                            <label htmlFor="field-rpe">Typical Session Effort (RPE 1–10)</label>
                                            <select
                                                id="field-rpe"
                                                value={sessionRpe}
                                                onChange={(e) => setSessionRpe(e.target.value)}
                                            >
                                                <option value="">Select RPE scale...</option>
                                                {Object.entries(RPE_DESCRIPTORS).map(([val, label]) => (
                                                    <option key={val} value={val}>{label}</option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>

                                    {calcWorkload != null && (
                                        <div className="calc-workload-preview">
                                            <strong>Calculated Weekly Workload:</strong> {sessionsPerWeek} sessions × {sessionDuration} min × RPE {sessionRpe} = <strong>{calcWorkload} Arbitrary Units (AU)</strong>
                                        </div>
                                    )}
                                </div>

                                {/* Section 4: Current Fatigue */}
                                <div className="form-section">
                                    <h4 className="form-section-heading">4. Current Fatigue Level</h4>
                                    <div className="form-group">
                                        <label htmlFor="field-fatigue">Self-Reported Fatigue (1–10 Scale)</label>
                                        <select
                                            id="field-fatigue"
                                            value={fatigueLevel}
                                            onChange={(e) => setFatigueLevel(e.target.value)}
                                        >
                                            <option value="">Select fatigue level...</option>
                                            {Object.entries(FATIGUE_DESCRIPTORS).map(([val, label]) => (
                                                <option key={val} value={val}>{label}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                {/* Section 5: Injury History Confirmation & Entry */}
                                <div className="form-section">
                                    <h4 className="form-section-heading">5. Injury History</h4>

                                    <div className="form-group">
                                        <label>Previous Injury Status</label>
                                        <div className="radio-group-horizontal" style={{ display: "flex", gap: 16, marginTop: 6 }}>
                                            <label style={{ cursor: "pointer" }}>
                                                <input
                                                    type="radio"
                                                    name="has_injury"
                                                    value="NO"
                                                    checked={hasInjuryHistory === "NO"}
                                                    onChange={(e) => setHasInjuryHistory(e.target.value)}
                                                /> No previous injury
                                            </label>

                                            <label style={{ cursor: "pointer" }}>
                                                <input
                                                    type="radio"
                                                    name="has_injury"
                                                    value="YES"
                                                    checked={hasInjuryHistory === "YES"}
                                                    onChange={(e) => setHasInjuryHistory(e.target.value)}
                                                /> Yes, prior injury exists
                                            </label>

                                            <label style={{ cursor: "pointer" }}>
                                                <input
                                                    type="radio"
                                                    name="has_injury"
                                                    value="UNKNOWN"
                                                    checked={hasInjuryHistory === "UNKNOWN"}
                                                    onChange={(e) => setHasInjuryHistory(e.target.value)}
                                                /> Not provided / Unknown
                                            </label>
                                        </div>
                                    </div>

                                    {/* Add Injury Record Sub-form */}
                                    {hasInjuryHistory === "YES" && (
                                        <div className="add-injury-subform" style={{ marginTop: 14, background: "#f8fafc", padding: 14, borderRadius: 8, border: "1px solid #e2e8f0" }}>
                                            <h5 style={{ margin: "0 0 10px 0", fontSize: 14, fontWeight: 600 }}>Add Injury Record</h5>
                                            <div className="form-grid">
                                                <div className="form-group">
                                                    <label htmlFor="field-inj-type">Injury Type</label>
                                                    <input
                                                        id="field-inj-type"
                                                        type="text"
                                                        placeholder="e.g. ACL Tear, Ankle Sprain"
                                                        value={newInjuryType}
                                                        onChange={(e) => setNewInjuryType(e.target.value)}
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="field-inj-body">Body Region</label>
                                                    <select
                                                        id="field-inj-body"
                                                        value={newBodyPart}
                                                        onChange={(e) => setNewBodyPart(e.target.value)}
                                                    >
                                                        <option value="Knee">Knee</option>
                                                        <option value="Hip">Hip</option>
                                                        <option value="Ankle">Ankle</option>
                                                        <option value="Foot">Foot</option>
                                                        <option value="Hamstring">Hamstring</option>
                                                        <option value="Quadriceps">Quadriceps</option>
                                                        <option value="Calf">Calf</option>
                                                        <option value="Lower back">Lower back</option>
                                                        <option value="Shoulder">Shoulder</option>
                                                        <option value="Other">Other</option>
                                                    </select>
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="field-inj-date">Approximate Date</label>
                                                    <input
                                                        id="field-inj-date"
                                                        type="date"
                                                        value={newInjuryDate}
                                                        onChange={(e) => setNewInjuryDate(e.target.value)}
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="field-inj-status">Status</label>
                                                    <select
                                                        id="field-inj-status"
                                                        value={newInjuryStatus}
                                                        onChange={(e) => setNewInjuryStatus(e.target.value)}
                                                    >
                                                        <option value="Recovered">Recovered</option>
                                                        <option value="Currently affected">Currently affected</option>
                                                        <option value="Unknown">Unknown</option>
                                                    </select>
                                                </div>
                                            </div>

                                            <button
                                                type="button"
                                                onClick={handleAddInjury}
                                                disabled={addingInjury || !newInjuryType.trim()}
                                                className="secondary-button"
                                                style={{ marginTop: 10 }}
                                            >
                                                {addingInjury ? <Loader2 size={14} className="spinner-icon" /> : <Plus size={14} />}
                                                Add Injury Record
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Modal Footer */}
                            <div className="modal-footer">
                                <button
                                    type="button"
                                    className="secondary-button"
                                    onClick={handleCancel}
                                    disabled={saving}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="primary-button"
                                    disabled={saving}
                                >
                                    {saving ? (
                                        <>
                                            <Loader2 size={16} className="spinner-icon" />
                                            Saving…
                                        </>
                                    ) : (
                                        <>
                                            <Save size={16} />
                                            Save All Profile Changes
                                        </>
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Profile;