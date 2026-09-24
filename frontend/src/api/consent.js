import api from "./axios";

export async function getConsentStatus() {
  const response = await api.get("/consent/status");
  return response.data;
}

export async function grantConsent(consents) {
  const response = await api.post("/consent/grant", { consents });
  return response.data;
}

export async function withdrawConsent(purpose) {
  const response = await api.post("/consent/withdraw", { purpose });
  return response.data;
}
