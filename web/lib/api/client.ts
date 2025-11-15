import axios, { AxiosError, AxiosInstance } from "axios";
import type { ApiError } from "@/lib/types/api";

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token here when implemented
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError<ApiError>) => {
    // Handle common errors
    if (error.response) {
      // Server responded with error
      const apiError = error.response.data;

      if (error.response.status === 401) {
        // Unauthorized - redirect to login when auth is implemented
        console.error("Unauthorized access");
      } else if (error.response.status === 404) {
        console.error("Resource not found");
      } else if (error.response.status === 500) {
        console.error("Server error:", apiError?.message || "Unknown error");
      }

      // Return structured error
      return Promise.reject({
        message: apiError?.message || "An error occurred",
        details: apiError?.details,
        status: error.response.status,
      });
    } else if (error.request) {
      // Request made but no response
      return Promise.reject({
        message: "Network error - no response from server",
        details: "Please check your connection and try again",
        status: 0,
      });
    } else {
      // Something else happened
      return Promise.reject({
        message: error.message || "An unexpected error occurred",
        details: "",
        status: 0,
      });
    }
  }
);

export default apiClient;

// Helper to handle file uploads
export const createFormDataClient = () => {
  return axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
    // Don't set Content-Type header - let axios set it with the boundary parameter
    timeout: 300000, // 5 minutes for large file uploads
  });
};
