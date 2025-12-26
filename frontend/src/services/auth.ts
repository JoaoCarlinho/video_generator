/**
 * Authentication Service
 * Handles user signup, login, logout, and session management
 * Uses backend API with JWT tokens
 */

import type { User } from '../types'

// Get API URL from environment
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface AuthResponse {
  access_token: string
  token_type: string
  user: {
    id: string
    email: string
    created_at: string
    is_verified: boolean
  }
}

/**
 * Sign up a new user
 */
export const signup = async (email: string, password: string): Promise<User> => {
  const response = await fetch(`${API_URL}/api/auth/signup`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Signup failed')
  }

  const data: AuthResponse = await response.json()

  // Store token and user
  localStorage.setItem('authToken', data.access_token)
  const user: User = {
    id: data.user.id,
    email: data.user.email,
    created_at: data.user.created_at,
  }
  localStorage.setItem('user', JSON.stringify(user))

  return user
}

/**
 * Sign in an existing user
 */
export const login = async (email: string, password: string): Promise<User> => {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Login failed')
  }

  const data: AuthResponse = await response.json()

  // Store token and user
  localStorage.setItem('authToken', data.access_token)
  const user: User = {
    id: data.user.id,
    email: data.user.email,
    created_at: data.user.created_at,
  }
  localStorage.setItem('user', JSON.stringify(user))

  return user
}

/**
 * Sign out current user
 */
export const logout = async (): Promise<void> => {
  const token = localStorage.getItem('authToken')

  // Call logout endpoint (optional, mainly for logging)
  if (token) {
    try {
      await fetch(`${API_URL}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
    } catch {
      // Ignore errors - we're logging out anyway
    }
  }

  // Clear local storage
  localStorage.removeItem('authToken')
  localStorage.removeItem('user')
}

/**
 * Get current session token
 */
export const getCurrentSession = async () => {
  const token = localStorage.getItem('authToken')
  if (!token) {
    return null
  }

  // Validate token by calling /me endpoint
  try {
    const response = await fetch(`${API_URL}/api/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      // Token is invalid, clear storage
      localStorage.removeItem('authToken')
      localStorage.removeItem('user')
      return null
    }

    return { access_token: token }
  } catch {
    return null
  }
}

/**
 * Get current user
 */
export const getCurrentUser = async (): Promise<User | null> => {
  // Try to get from localStorage first
  const stored = localStorage.getItem('user')
  const token = localStorage.getItem('authToken')

  if (!token) {
    localStorage.removeItem('user')
    return null
  }

  if (stored) {
    // Validate token is still valid
    try {
      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (response.ok) {
        return JSON.parse(stored)
      }
    } catch {
      // Token validation failed
    }

    // Clear invalid session
    localStorage.removeItem('authToken')
    localStorage.removeItem('user')
    return null
  }

  // No stored user, try to get from API
  try {
    const response = await fetch(`${API_URL}/api/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      localStorage.removeItem('authToken')
      return null
    }

    const data = await response.json()
    const user: User = {
      id: data.id,
      email: data.email,
      created_at: data.created_at,
    }

    localStorage.setItem('user', JSON.stringify(user))
    return user
  } catch {
    localStorage.removeItem('authToken')
    return null
  }
}

/**
 * Listen to auth state changes
 * Note: With JWT auth, we check on app load rather than realtime updates
 */
export const onAuthStateChange = (
  callback: (user: User | null) => void
) => {
  // Check current auth state immediately
  getCurrentUser().then(callback).catch(() => callback(null))

  // Return a mock subscription object for compatibility
  return {
    data: {
      subscription: {
        unsubscribe: () => {
          // No-op for JWT auth
        }
      }
    }
  }
}

/**
 * Refresh the access token
 */
export const refreshToken = async (): Promise<string | null> => {
  const token = localStorage.getItem('authToken')
  if (!token) {
    return null
  }

  try {
    const response = await fetch(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('user')
      return null
    }

    const data: AuthResponse = await response.json()
    localStorage.setItem('authToken', data.access_token)

    const user: User = {
      id: data.user.id,
      email: data.user.email,
      created_at: data.user.created_at,
    }
    localStorage.setItem('user', JSON.stringify(user))

    return data.access_token
  } catch {
    return null
  }
}
