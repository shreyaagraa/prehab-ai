import api from "./axios";

export async function getMyInjuryHistory() {
    const response = await api.get("/injury-history/me");
    return response.data;
}

export async function addMyInjuryRecord(data) {
    const response = await api.post("/injury-history/me", data);
    return response.data;
}

export async function deleteMyInjuryRecord(injuryId) {
    await api.delete(`/injury-history/me/${injuryId}`);
}

export async function getAthleteInjuryHistory(athleteId) {
    const response = await api.get(`/injury-history/athlete/${athleteId}`);
    return response.data;
}
