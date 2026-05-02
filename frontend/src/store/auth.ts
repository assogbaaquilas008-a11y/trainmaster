/**
 * Global auth store (Zustand).
 * Persists tokens to localStorage; hydrates on app load.
 */

import { create } from 'zustand'
import { authApi } from '../services/api'

interface User {
  id: number
  username: string
  email: string
  is_admin: boolean
}

interface AuthState {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
  hydrate: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isLoading: true,

  login: async (email, password) => {
    const { data } = await authApi.login({ email, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    const me = await authApi.me()
    set({ user: me.data })
  },

  register: async (username, email, password) => {
    await authApi.register({ username, email, password })
    // Auto-login after registration
    const { data } = await authApi.login({ email, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    const me = await authApi.me()
    set({ user: me.data })
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null })
  },

  hydrate: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      set({ isLoading: false })
      return
    }
    try {
      const { data } = await authApi.me()
      set({ user: data, isLoading: false })
    } catch {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, isLoading: false })
    }
  },
}))
