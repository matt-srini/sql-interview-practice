import axios from 'axios';

function trimTrailingSlash(value) {
  return value.replace(/\/+$/, '');
}

function getApiBaseUrl() {
  const configuredBaseUrl = import.meta.env.VITE_BACKEND_URL?.trim();
  if (configuredBaseUrl) {
    return `${trimTrailingSlash(configuredBaseUrl)}/api`;
  }

  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location;
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';

    if (isLocalhost && port && port !== '8000') {
      return `${protocol}//${hostname}:8000/api`;
    }
  }

  return '/api';
}

const api = axios.create({
  baseURL: getApiBaseUrl(),
  // Required so the browser sends the session cookie on cross-origin requests
  // (e.g. Vite dev server on :5173 -> backend on :8000). Without this the
  // backend creates a new anonymous session on every request.
  withCredentials: true,
});

export default api;
