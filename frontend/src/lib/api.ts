import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 90000,
  headers: { "Content-Type": "application/json" },
});

// ==========================================
// Refresh Token Concurrency Queue
// ==========================================
let isRefreshing = false;
let failedQueue: Array<{ resolve: (value?: unknown) => void; reject: (reason?: unknown) => void }> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401 &&
      typeof window !== "undefined" &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/refresh")
    ) {
      if (isRefreshing) {
        return new Promise(function (resolve, reject) {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers = {
              ...originalRequest.headers,
              Authorization: `Bearer ${token}`,
            };
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;
      const refreshToken = localStorage.getItem("refresh_token");

      if (refreshToken) {
        try {
          const res = await axios.post(`${API_URL}/auth/refresh`, { refresh_token: refreshToken });
          const { access_token, refresh_token: new_refresh_token } = res.data;

          localStorage.setItem("access_token", access_token);
          localStorage.setItem("refresh_token", new_refresh_token);

          originalRequest.headers = {
            ...originalRequest.headers,
            Authorization: `Bearer ${access_token}`,
          };

          processQueue(null, access_token);
          return api(originalRequest);
        } catch (refreshErr: any) {
          processQueue(refreshErr, null);
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
          return Promise.reject({
            status: refreshErr.response?.status,
            message: refreshErr.response?.data?.detail || refreshErr.message,
            data: refreshErr.response?.data,
          });
        } finally {
          isRefreshing = false;
        }
      } else {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
      }
    }

    return Promise.reject({
      status: error.response?.status,
      message: error.response?.data?.detail || error.message,
      data: error.response?.data,
    });
  }
);

// ==========================================
// API Endpoints
// ==========================================

export const authApi = {
  register: (data: { email: string; password: string; full_name: string; phone?: string }) =>
    api.post("/auth/register", data),
  login: (data: { email: string; password: string }) => api.post("/auth/login", data),
  refreshToken: (refresh_token: string) => api.post("/auth/refresh", { refresh_token }),
  logout: async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      try { await api.post("/auth/logout", { refresh_token: refreshToken }); } 
      catch (err) { console.error("Logout API failed", err); }
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },
  verifyOtp: (data: { email: string; otp: string }) => api.post("/auth/verify-otp", data),
  forgotPassword: (email: string) => api.post("/auth/forgot-password", { email }),
  resetPassword: (data: { email: string; otp: string; new_password: string }) =>
    api.post("/auth/reset-password", data),
  googleLogin: (id_token: string) => api.post("/auth/google", { id_token }),
  me: () => api.get("/auth/me"),
};

export const dashboardApi = {
  get: () => api.get("/dashboard"),
  addMetric: (data: { metric_type: string; value: number; unit: string; notes?: string }) =>
    api.post("/health-metrics", data),
  getMetrics: (type?: string) => api.get("/health-metrics", { params: { metric_type: type } }),
  getFamilyProfiles: () => api.get("/family-profiles"),
  addFamilyProfile: (data: Record<string, unknown>) => api.post("/family-profiles", data),
};

export const chatApi = {
  createSession: (language = "en") =>
    api.post("/chat/sessions", null, { params: { language }, timeout: 60000 }),
  listSessions: () => api.get("/chat/sessions"),
  getSession: (id: string) => api.get(`/chat/sessions/${id}`),
  sendMessage: (sessionId: string, content: string, language = "en") =>
    api.post(`/chat/sessions/${sessionId}/messages`, { content, language }, { timeout: 120000 }),
  voiceChat: (audio: File, language = "en") => {
    const form = new FormData();
    form.append("audio", audio);
    return api.post("/chat/voice", form, {
      params: { language },
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000,
    });
  },
};

// ==========================================
// Doctors (Patient-facing)
// ==========================================
export const doctorsApi = {
  list: (params?: Record<string, unknown>) => api.get("/doctors", { params }),
  get: (id: string) => api.get(`/doctors/${id}`),
  book: (data: { doctor_id: string; scheduled_at: string; notes?: string }) =>
    api.post("/appointments", data),
  appointments: () => api.get("/appointments"),
  cancel: (id: string) => api.patch(`/appointments/${id}/cancel`),
  generateSummary: (appointmentId: string) => api.post(`/appointments/${appointmentId}/summary`),
};

// ==========================================
// Doctor-facing portal (Phase 5)
// ==========================================
export const doctorApi = {
  myAppointments: (params?: Record<string, unknown>) => api.get("/doctor/appointments", { params }),
  getPatientSummary: (appointmentId: string) =>
    api.get(`/doctor/appointments/${appointmentId}/patient-summary`),
};

// ==========================================
// 🚀 NAYA LOCATION AWARE REPORT API
// ==========================================
export const medicalApi = {
  analyzeReport: (file: File, report_type: string, title: string, location?: {lat: number, lng: number}) => {
    const form = new FormData();
    form.append("file", file);
    
    // Agar location available hai, toh query parameters mein bhej do
    const params: any = { report_type, title };
    if (location) {
      params.lat = location.lat;
      params.lng = location.lng;
    }

    return api.post("/reports/analyze", form, {
      params: params,
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000,
    });
  },
  listReports: () => api.get("/reports"),
  scanPrescription: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/prescriptions/scan", form, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000,
    });
  },
  getMedicine: (name: string) => api.get(`/medicines/${name}`),
  getDisease: (name: string) => api.get(`/diseases/${name}`),
  analyzeNutrition: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/nutrition/analyze", form, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000,
    });
  },
  riskPrediction: () => api.get("/risk-prediction"),
};

export const emergencyApi = {
  trigger: (lat?: number, lng?: number) =>
    api.post("/emergency/trigger", null, { params: { latitude: lat, longitude: lng } }),
  nearby: (params?: Record<string, unknown>) => api.get("/emergency/nearby", { params }),
  addContact: (data: { name: string; phone: string; relation: string; is_primary?: boolean }) =>
    api.post("/emergency/contacts", data),
  listContacts: () => api.get("/emergency/contacts"),
};