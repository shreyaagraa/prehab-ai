import api from "./axios";
import { getMyHistory, getAllAssessments } from "./videos";

export async function getAssessments() {
    try {
        return await getAllAssessments();
    } catch (err) {
        if (err.response?.status === 403 || err.response?.status === 404) {
            try {
                return await getMyHistory();
            } catch (innerErr) {
                return [];
            }
        }
        return [];
    }
}

export async function getAssessment(id) {
    try {
        const response = await api.get(`/videos/${id}/analysis`);
        return response.data;
    } catch (err) {
        if (err.response?.status === 404) {
            return null;
        }
        throw err;
    }
}

export async function uploadVideo(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post("/videos", formData, {
        headers: {
            "Content-Type": "multipart/form-data"
        }
    });

    return response.data;
}