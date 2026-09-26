/**
 * API Client for FastAPI Backend
 * 
 * Wraps all HTTP calls to the backend with Firebase auth token injection.
 */

import axios from 'axios';
import { auth } from './firebase';

const API_BASE = '';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
});

// Automatically attach Firebase ID token to every request
api.interceptors.request.use(async (config) => {
  const user = auth.currentUser;
  if (user) {
    const token = await user.getIdToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid — could force logout here
      console.warn('Auth token expired');
    }
    return Promise.reject(error);
  }
);

// =====================================================
// AUTH API
// =====================================================

export const verifyAuth = () => api.post('/api/auth/verify');

// =====================================================
// COOKIE API
// =====================================================

export const loginWithCookie = (cookie) =>
  api.post('/api/cookie/login', { cookie });

export const loginWithBrowser = () =>
  api.post('/api/cookie/browser-login', {}, { timeout: 150000 });

export const getCookieStatus = () =>
  api.get('/api/cookie/status');

export const logoutCookie = () =>
  api.post('/api/cookie/logout');

// =====================================================
// GROUPS API
// =====================================================

export const fetchGroups = () =>
  api.get('/api/groups');

// =====================================================
// CAMPAIGN API
// =====================================================

export const startCampaign = (data) =>
  api.post('/api/campaign/start', data);

export const getCampaignStatus = () =>
  api.get('/api/campaign/status');

export const getCampaignHistory = () =>
  api.get('/api/campaign/history');

export const deleteCampaignHistory = () =>
  api.delete('/api/campaign/history');

export const exportCampaignExcel = () =>
  api.get('/api/campaign/export', { responseType: 'blob' });

export default api;
