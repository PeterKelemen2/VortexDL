// src/utils/env.js
// In development, API calls use relative URLs proxied by Vite (see vite.config.js).
// In production, set VITE_BACKEND_URL to the backend's base URL if it differs from the frontend origin.
export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || ''
