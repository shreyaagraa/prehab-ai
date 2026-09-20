import api from "./axios";

/**
 * Upload a video file for the authenticated athlete.
 *
 * Sends the file as multipart/form-data to POST /videos.
 * The JWT is automatically attached by the axios request interceptor.
 * athlete_id is derived server-side from the JWT — never passed from here.
 *
 * @param {File} file  - The video File object from an <input type="file" />.
 * @param {Function} [onUploadProgress] - Optional axios progress callback.
 * @returns {Promise<Object>} Metadata response from the server (includes video_url).
 */
export async function uploadVideoFile(file, onUploadProgress) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post("/videos", formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
            if (typeof onUploadProgress === "function") {
                let percent = 0;
                if (typeof progressEvent === "number") {
                    percent = progressEvent;
                } else if (progressEvent && typeof progressEvent === "object") {
                    if (progressEvent.total) {
                        percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    } else if (progressEvent.progress != null) {
                        percent = Math.round(progressEvent.progress * 100);
                    }
                }
                onUploadProgress(Math.min(100, Math.max(0, percent || 0)));
            }
        },
    });

    return response.data;
}

/**
 * Trigger background pose estimation analysis for an uploaded video.
 *
 * POST /videos/{videoId}/analyze
 *
 * @param {string} videoId - UUID of the uploaded video.
 * @returns {Promise<{analysis_id: string, video_id: string, status: string, message: string}>}
 */
export async function triggerAnalysis(videoId) {
    const response = await api.post(`/videos/${videoId}/analyze`);
    return response.data;
}

/**
 * Poll the analysis status for a video.
 *
 * GET /videos/{videoId}/analysis
 *
 * Returns the most recent AnalysisResult for the video.
 * Call repeatedly until status is "COMPLETED" or "FAILED".
 *
 * @param {string} videoId - UUID of the video.
 * @returns {Promise<Object>} AnalysisStatusResponse from the server.
 */
export async function getAnalysisStatus(videoId) {
    const response = await api.get(`/videos/${videoId}/analysis`);
    return response.data;
}

/**
 * Fetch the extracted biomechanical feature vector for an analysis.
 *
 * GET /videos/{videoId}/features
 *
 * @param {string} videoId - UUID of the video.
 * @returns {Promise<Object>} AnalysisFeatureResponse from the server.
 */
export async function getAnalysisFeatures(videoId) {
    const response = await api.get(`/videos/${videoId}/features`);
    return response.data;
}

/**
 * Fetch the Landing Error Scoring System (LESS) approximation result for an analysis.
 *
 * GET /videos/{videoId}/less
 *
 * @param {string} videoId - UUID of the video.
 * @returns {Promise<Object>} AnalysisLESSResponse from the server.
 */
export async function getLessResult(videoId) {
    const response = await api.get(`/videos/${videoId}/less`);
    return response.data;
}

/**
 * Fetch the Corrective Action Plan / recommendations for an analyzed video.
 *
 * GET /videos/{videoId}/recommendations
 *
 * @param {string} videoId - UUID of the video.
 * @returns {Promise<Object>} CorrectiveActionPlanResponse from the server.
 */
export async function getRecommendations(videoId) {
    const response = await api.get(`/videos/${videoId}/recommendations`);
    return response.data;
}

/**
 * Fetch the detected AI pose landmarks for a specific video assessment.
 * Scoped to an exact analysisId to guarantee matching the active assessment.
 *
 * GET /videos/{videoId}/landmarks?analysis_id={analysisId}
 *
 * @param {string} videoId - UUID of the video.
 * @param {string} [analysisId] - Optional exact assessment UUID.
 * @returns {Promise<Object>} AnalysisPoseLandmarksResponse from the server.
 */
export async function getAnalysisLandmarks(videoId, analysisId = null) {
    const params = analysisId ? { analysis_id: analysisId } : {};
    const response = await api.get(`/videos/${videoId}/landmarks`, { params });
    return response.data;
}


/**
 * Fetch the analysis history for the authenticated athlete.
 *
 * GET /videos/my-history
 *
 * Returns all videos belonging to the athlete sorted newest first.
 * Each item includes the latest risk score/LESS score summary.
 * Does NOT trigger any new analysis.
 *
 * @returns {Promise<Array>} List of VideoHistoryItem objects.
 */
export async function getMyHistory() {
    const response = await api.get("/videos/my-history");
    return response.data;
}

/**
 * Fetch all team assessments (Staff action).
 * GET /videos/assessments
 */
export async function getAllAssessments() {
    const response = await api.get("/videos/assessments");
    return response.data;
}

/**
 * Delete a video assessment record.
 * DELETE /videos/{videoId}
 *
 * @param {string} videoId - UUID of the video assessment to delete.
 * @returns {Promise<Object>} Response object from the server.
 */
export async function deleteVideoAssessment(videoId) {
    const response = await api.delete(`/videos/${videoId}`);
    return response.data;
}

/**
 * Update video assessment title (rename).
 * PATCH /videos/{videoId}
 *
 * @param {string} videoId - UUID of the video assessment to update.
 * @param {Object} data - { title: string }
 * @returns {Promise<Object>} Response object from the server.
 */
export async function updateVideoAssessment(videoId, data) {
    const response = await api.patch(`/videos/${videoId}`, data);
    return response.data;
}

/**
 * Derive the media base URL from the configured API base URL.
 *
 * The API base is e.g. "http://127.0.0.1:8000/api/v1".
 * Video files are served from "http://127.0.0.1:8000/uploads/...".
 * This helper strips the "/api/v1" suffix to get the origin.
 *
 * @returns {string} Origin base, e.g. "http://127.0.0.1:8000"
 */
export function getMediaBaseUrl() {
    const apiBase =
        import.meta?.env?.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
    return apiBase.replace(/\/api\/v\d+\/?$/, "").replace(/\/$/, "");
}
