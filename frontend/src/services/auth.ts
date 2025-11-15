/**
 * Supabase Authentication Service
 * Handles user signup, login, logout, and session management
 */

import { createClient } from '@supabase/supabase-js'
import type { User } from '../types'

// Get Supabase credentials from environment
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || ''
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

// Initialize Supabase client with error handling
export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
})

/**
 * Sign up a new user
 */
export const signup = async (email: string, password: string): Promise<User> => {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
  })

  if (error) {
    throw new Error(error.message)
  }

  if (!data.user) {
    throw new Error('User creation failed')
  }

  const user: User = {
    id: data.user.id,
    email: data.user.email || '',
    created_at: data.user.created_at,
  }

  return user
}

/**
 * Sign in an existing user
 */
export const login = async (email: string, password: string): Promise<User> => {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })

  if (error) {
    throw new Error(error.message)
  }

  if (!data.user || !data.session) {
    throw new Error('Login failed')
  }

  const user: User = {
    id: data.user.id,
    email: data.user.email || '',
    created_at: data.user.created_at,
  }

  // Store JWT token for API requests
  if (data.session.access_token) {
    localStorage.setItem('authToken', data.session.access_token)
    localStorage.setItem('user', JSON.stringify(user))
  }

  return user
}

/**
 * Sign out current user
 */
export const logout = async (): Promise<void> => {
  const { error } = await supabase.auth.signOut()

  if (error) {
    throw new Error(error.message)
  }

  // Clear local storage
  localStorage.removeItem('authToken')
  localStorage.removeItem('user')
}

/**
 * Get current session
 */
export const getCurrentSession = async () => {
  const { data, error } = await supabase.auth.getSession()

  if (error) {
    throw new Error(error.message)
  }

  return data.session
}

/**
 * Get current user
 */
export const getCurrentUser = async (): Promise<User | null> => {
  // Try to get from localStorage first
  const stored = localStorage.getItem('user')
  if (stored) {
    return JSON.parse(stored)
  }

  // Otherwise get from Supabase
  const { data, error } = await supabase.auth.getUser()

  if (error || !data.user) {
    return null
  }

  const user: User = {
    id: data.user.id,
    email: data.user.email || '',
    created_at: data.user.created_at,
  }

  localStorage.setItem('user', JSON.stringify(user))
  return user
}

/**
 * Listen to auth state changes with error handling
 */
export const onAuthStateChange = (
  callback: (user: User | null) => void
) => {
  try {
    return supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        const user: User = {
          id: session.user.id,
          email: session.user.email || '',
          created_at: session.user.created_at,
        }
        localStorage.setItem('authToken', session.access_token)
        localStorage.setItem('user', JSON.stringify(user))
        callback(user)
      } else {
        localStorage.removeItem('authToken')
        localStorage.removeItem('user')
        callback(null)
      }
    })
  } catch (error) {
    // If auth state change fails, treat as no user
    console.warn('Auth state change error:', error)
    localStorage.removeItem('authToken')
    localStorage.removeItem('user')
    callback(null)
  }
}

