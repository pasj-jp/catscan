import axios from 'axios';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/+$/, '');

const api = axios.create({
    // Keep local requests relative so Vite's /api proxy handles them.
    // Set VITE_API_BASE_URL when the frontend and API are deployed separately.
    baseURL: configuredBaseUrl || undefined,
});

export default api;
