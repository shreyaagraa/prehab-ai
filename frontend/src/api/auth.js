import api from "./axios.js";

export async function loginUser(email, password) {
  const normalizedEmail = (email || "").trim().toLowerCase();
  const formData = new URLSearchParams();

  formData.append("username", normalizedEmail);
  formData.append("password", password);

  const response = await api.post("/auth/login", formData, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    }
  });

  return response.data;
}

export async function registerUser(data) {
  const payload = {
    ...data,
    email: (data.email || "").trim().toLowerCase()
  };

  const response = await api.post("/auth/register", payload);

  return response.data;
}

export async function googleLoginUser(credential, password = null) {
  const payload = { credential };
  if (password) {
    payload.password = password;
  }
  const response = await api.post("/auth/google", payload);
  return response.data;
}

export async function getCurrentUser() {
  const response = await api.get("/auth/me");

  return response.data;
}

export async function updateUserProfile(data) {
  const response = await api.patch("/auth/me", data);
  return response.data;
}

