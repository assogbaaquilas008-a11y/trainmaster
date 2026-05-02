/**
 * Configured Axios instance.
 * – Attaches Bearer token from localStorage automatically.
 * – On 401: attempts a silent token refresh, retries once.
 * – Exports typed service helpers for each domain.
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? ''

export const api = axios.create({ baseURL: BASE })

// Attach token
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Refresh on 401
let refreshing = false
api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status === 401 && !original._retry && !refreshing) {
      original._retry = true
      refreshing = true
      try {
        const refresh = localStorage.getItem('refresh_token')
        if (!refresh) throw new Error('no refresh token')
        const { data } = await axios.post(`${BASE}/api/auth/refresh`, null, {
          params: { refresh_token: refresh },
        })
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        original.headers!.Authorization = `Bearer ${data.access_token}`
        return api(original)
      } catch {
        localStorage.clear()
        window.location.href = '/login'
      } finally {
        refreshing = false
      }
    }
    return Promise.reject(error)
  }
)

// ─── Auth ───────────────────────────────────────────────────────────────────

export const authApi = {
  register: (data: { username: string; email: string; password: string }) =>
    api.post('/api/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/api/auth/login', data),
  me: () => api.get('/api/auth/me'),
}

// ─── Quizzes ─────────────────────────────────────────────────────────────────

export const quizApi = {
  list: ()                         => api.get('/api/quizzes'),
  get: (id: number)                => api.get(`/api/quizzes/${id}`),
  start: (id: number)              => api.post(`/api/quizzes/${id}/start`),
  answer: (id: number, payload: { question_id: number; submitted_text: string }) =>
    api.post(`/api/quizzes/${id}/answer`, payload),
  finish: (id: number)             => api.post(`/api/quizzes/${id}/finish`),
  history: (id: number)            => api.get(`/api/quizzes/${id}/history`),
}

// ─── Leaderboard ─────────────────────────────────────────────────────────────

export const leaderboardApi = {
  get: (limit = 50) => api.get('/api/leaderboard', { params: { limit } }),
}

// ─── Attempts (profile) ──────────────────────────────────────────────────────

export const attemptApi = {
  mine: ()                         => api.get('/api/attempts/mine'),
  detail: (id: number)             => api.get(`/api/attempts/mine/${id}`),
}

// ─── Flags ───────────────────────────────────────────────────────────────────

export const flagApi = {
  create: (data: { question_id: number; submitted_text: string; reason?: string }) =>
    api.post('/api/flags', data),
  mine: () => api.get('/api/flags/mine'),
}

// ─── Admin ───────────────────────────────────────────────────────────────────

export const adminApi = {
  createQuiz:  (data: object)         => api.post('/api/admin/quizzes', data),
  uploadQuiz:  (file: File)           => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/api/admin/quizzes/upload', fd)
  },
  listQuizzes: ()                     => api.get('/api/admin/quizzes'),
  updateQuiz:  (id: number, d: object) => api.put(`/api/admin/quizzes/${id}`, d),
  deleteQuiz:  (id: number)           => api.delete(`/api/admin/quizzes/${id}`),
  listFlags:   (status = 'pending')   => api.get('/api/admin/flags', { params: { status_filter: status } }),
  reviewFlag:  (id: number, d: object) => api.post(`/api/admin/flags/${id}/review`, d),
  listUsers:   ()                     => api.get('/api/admin/users'),
  grantPoints: (uid: number, pts: number) =>
    api.post(`/api/admin/users/${uid}/grant`, null, { params: { points: pts } }),
  stats:       ()                     => api.get('/api/admin/stats'),
}

// ─── Duel ────────────────────────────────────────────────────────────────────

export const duelApi = {
  create: (quiz_id: number) =>
    api.post('/ws/duel/new', null, {
      params: { quiz_id, token: localStorage.getItem('access_token') },
    }),
  status: (code: string) => api.get(`/ws/duel/${code}/status`),
}
