import api from "./axios";

export async function getReportSharingStatus() {
  const response = await api.get("/reports/sharing");
  return response.data;
}

export async function updateReportSharing(target_role, is_authorized) {
  const response = await api.post("/reports/sharing/update", {
    target_role,
    is_authorized,
  });
  return response.data;
}
