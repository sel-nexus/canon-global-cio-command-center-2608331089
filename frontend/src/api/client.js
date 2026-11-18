/** Configure the shared API client and attach the current bearer token. */
import axios from 'axios';

export const TOKEN_KEY = 'cio_access_token';
export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1' });
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use((response) => response, (error) => {
  const url = error.config?.url || '';
  if (error.response?.status === 401 && !['/auth/login', '/auth/register'].includes(url)) {
    sessionStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event('session-expired'));
  }
  return Promise.reject(error);
});
