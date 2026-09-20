import api from "./axios";

export async function getAthletes() {
    const response = await api.get("/athletes");

    return response.data;
}

export async function getAthlete(id) {
    const response = await api.get(`/athletes/${id}`);

    return response.data;
}

export async function updateAthlete(id, data) {
    const response = await api.patch(`/athletes/${id}`, data);

    return response.data;
}

/**
 * Fetch the authenticated athlete's own profile.
 * Throws AxiosError with status 404 when no profile exists yet.
 */
export async function getMyAthleteProfile() {
    const response = await api.get("/athletes/me");

    return response.data;
}

/**
 * Create or update the authenticated athlete's own profile.
 * Sends only the five editable fields — user_id and athlete_id
 * are controlled server-side from the JWT.
 */
export async function upsertMyAthleteProfile(data) {
    const response = await api.put("/athletes/me", data);

    return response.data;
}

/**
 * Register a new athlete account & profile (Coach action).
 */
export async function registerAthleteWithUser(data) {
    const response = await api.post("/athletes/register-athlete", data);
    return response.data;
}

/**
 * Assign or unassign an athlete to a coach or update status.
 */
export async function assignAthlete(id, assignData) {
    const response = await api.patch(`/athletes/${id}/assign`, assignData);
    return response.data;
}