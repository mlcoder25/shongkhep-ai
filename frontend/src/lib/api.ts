import axios, { AxiosError } from "axios";
import Cookies from "js-cookie";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = Cookies.get("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (error: AxiosError<{ detail: string }>) => {
    const msg = error.response?.data?.detail || error.message || "Unknown error";
    return Promise.reject(new Error(msg));
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  signup:         (data: { email: string; password: string }) => apiClient.post("/auth/signup", data).then(r => r.data),
  login:          (data: { email: string; password: string }) => apiClient.post("/auth/login", data).then(r => r.data),
  me:             ()                                          => apiClient.get("/auth/me").then(r => r.data),
  regenerateKey:  ()                                          => apiClient.post("/auth/regenerate-key").then(r => r.data),
};

// ── Summarize ─────────────────────────────────────────────────────────────────
export interface SummarizePayload {
  text: string;
  language?: "en" | "bn" | "auto";
  max_length?: number;
}

export const summarizeApi = {
  summarize:    (data: SummarizePayload)  => apiClient.post("/summarize", data).then(r => r.data),
  submitAsync:  (data: SummarizePayload)  => apiClient.post("/summarize/async", data).then(r => r.data),
  pollJob:      (jobId: string)           => apiClient.get(`/summarize/jobs/${jobId}`).then(r => r.data),
};

// ── Usage ─────────────────────────────────────────────────────────────────────
export const usageApi = {
  stats: (limit = 20) => apiClient.get(`/usage/stats?limit=${limit}`).then(r => r.data),
};

// ── Plans ─────────────────────────────────────────────────────────────────────
export const plansApi = {
  info:    ()               => apiClient.get("/plans/info").then(r => r.data),
  upgrade: (plan: string)   => apiClient.post("/plans/upgrade", { plan }).then(r => r.data),
};

// ── Webhooks ──────────────────────────────────────────────────────────────────
export interface WebhookCreatePayload {
  url: string;
  secret?: string;
  events?: string[];
}

export const webhooksApi = {
  list:   ()                               => apiClient.get("/webhooks").then(r => r.data),
  create: (data: WebhookCreatePayload)     => apiClient.post("/webhooks", data).then(r => r.data),
  delete: (id: string)                     => apiClient.delete(`/webhooks/${id}`),
  test:   (id: string)                     => apiClient.post(`/webhooks/${id}/test`).then(r => r.data),
};

// ── Admin ─────────────────────────────────────────────────────────────────────
export const adminApi = {
  stats:        ()                                      => apiClient.get("/admin/stats").then(r => r.data),
  users:        (params?: { plan?: string; skip?: number; limit?: number }) =>
                  apiClient.get("/admin/users", { params }).then(r => r.data),
  setPlan:      (userId: string, plan: string)          => apiClient.post(`/admin/users/${userId}/plan`, { plan }).then(r => r.data),
  deactivate:   (userId: string)                        => apiClient.post(`/admin/users/${userId}/deactivate`).then(r => r.data),
  resetUsage:   (userId: string)                        => apiClient.post(`/admin/users/${userId}/reset-usage`).then(r => r.data),
};

// ── URL Summarize ─────────────────────────────────────────────────────────────
export interface URLSummarizePayload {
  url: string;
  language?: string;
  max_length?: number;
}

export const urlSummarizeApi = {
  summarize: (data: URLSummarizePayload) =>
    apiClient.post("/summarize/url", data).then(r => r.data),
};

// ── PDF Summarize ─────────────────────────────────────────────────────────────
export const pdfSummarizeApi = {
  summarize: (file: File, language = "auto") => {
    const form = new FormData();
    form.append("file", file);
    form.append("language", language);
    return apiClient.post("/summarize/pdf", form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data);
  },
};
