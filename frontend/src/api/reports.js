/**
 * frontend/src/api/reports.js
 * ----------------------------
 * API client methods for Reports & Exports System.
 */
import api from "./axios";

export async function getReportOptions() {
    const response = await api.get("/reports/options");
    return response.data;
}

export async function getReportData(reportType, athleteId, videoId = null) {
    const params = { report_type: reportType, athlete_id: athleteId };
    if (videoId) {
        params.video_id = videoId;
    }
    const response = await api.get("/reports/data", { params });
    return response.data;
}

export async function getReportsList() {
    const response = await api.get("/reports/list");
    return response.data;
}

export async function downloadReportPdf(reportType, athleteId, videoId = null, filename = null) {
    const params = { report_type: reportType, athlete_id: athleteId };
    if (videoId) {
        params.video_id = videoId;
    }
    const response = await api.get("/reports/export/pdf", {
        params,
        responseType: "blob",
    });

    const blob = new Blob([response.data], { type: "application/pdf" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename || `PreHabAI_${reportType}_${new Date().toISOString().slice(0, 10)}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode.removeChild(link);
    window.URL.revokeObjectURL(url);
}

export async function downloadReportExcel(reportType, athleteId, videoId = null, filename = null) {
    const params = { report_type: reportType, athlete_id: athleteId };
    if (videoId) {
        params.video_id = videoId;
    }
    const response = await api.get("/reports/export/excel", {
        params,
        responseType: "blob",
    });

    const blob = new Blob([response.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename || `PreHabAI_${reportType}_${new Date().toISOString().slice(0, 10)}.xlsx`);
    document.body.appendChild(link);
    link.click();
    link.parentNode.removeChild(link);
    window.URL.revokeObjectURL(url);
}
