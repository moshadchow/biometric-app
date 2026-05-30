import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const api = axios.create({
    baseURL,
    withCredentials: false,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      sessionStorage.removeItem("jwt_token");
    }
    return Promise.reject(error);
  }
);

export default api;
