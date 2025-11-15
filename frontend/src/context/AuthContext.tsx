/**
 * Auth Context: Manages authentication state globally
 * Provides user data and auth functions to all components
 */

import React, { createContext, useState, useEffect, useCallback } from 'react'
import type { User, AuthContextType } from '../types'
import { signup as authSignup, login as authLogin, logout as authLogout, onAuthStateChange } from '../services/auth'

// Create context
export const AuthContext = createContext<AuthContextType | undefined>(undefined)

export interface AuthProviderProps {
  children: React.ReactNode
}

/**
 * Auth Provider: Wraps app with authentication state
 */
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Check initial auth state
  useEffect(() => {
    const { data } = onAuthStateChange((authUser) => {
      setUser(authUser)
      setIsLoading(false)
    })

    return () => {
      data?.subscription?.unsubscribe()
    }
  }, [])

  // Sign up
  const signup = useCallback(async (email: string, password: string) => {
    try {
      setError(null)
      setIsLoading(true)
      const newUser = await authSignup(email, password)
      setUser(newUser)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Signup failed'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Login
  const login = useCallback(async (email: string, password: string) => {
    try {
      setError(null)
      setIsLoading(true)
      const authUser = await authLogin(email, password)
      setUser(authUser)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Logout
  const logout = useCallback(async () => {
    try {
      setError(null)
      setIsLoading(true)
      await authLogout()
      setUser(null)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Logout failed'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const value: AuthContextType = {
    user,
    isAuthenticated: user !== null,
    isLoading,
    login,
    signup,
    logout,
    error,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export default AuthContext

