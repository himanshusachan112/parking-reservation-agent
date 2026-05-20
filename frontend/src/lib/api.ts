import axios from "axios";
import type { ApiError } from "@/types";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || error.message || "An unexpected error occurred",
      status: error.response?.status || 500,
    };
    return Promise.reject(apiError);
  }
);

export default api;
