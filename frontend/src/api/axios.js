import axios from "axios";

export function getApiBaseUrl() {
    const rawUrl =
        import.meta?.env?.VITE_API_URL ||
        import.meta?.env?.VITE_API_BASE_URL ||
        "http://localhost:8000/api/v1";

    const trimmed = rawUrl.trim().replace(/\/+$/, "");
    if (trimmed.endsWith("/api/v1")) {
        return trimmed;
    }
    return `${trimmed}/api/v1`;
}

const api = axios.create({
    baseURL: getApiBaseUrl()
});

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("access_token");

        if (token && !config.url?.includes("/auth/login") && !config.url?.includes("/auth/register")) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
    },
    (error) => Promise.reject(error)
);

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("user");
        }

        return Promise.reject(error);
    }
);

export default api;