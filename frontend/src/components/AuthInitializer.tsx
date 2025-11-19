/**
 * AuthInitializer - Initializes and manages auth state with Redux
 * Replaces AuthContext provider with Redux-based state management
 */

import { useEffect, type ReactNode } from 'react'
import { useAppDispatch } from '../store/hooks'
import { initializeAuth, setUser } from '../store/slices/authSlice'
import { onAuthStateChange } from '../services/auth'

interface AuthInitializerProps {
  children: ReactNode
}

export const AuthInitializer = ({ children }: AuthInitializerProps) => {
  const dispatch = useAppDispatch()

  useEffect(() => {
    // Initialize auth state from localStorage or Supabase
    dispatch(initializeAuth())

    // Listen to auth state changes
    const { data } = onAuthStateChange((user) => {
      dispatch(setUser(user))
    })

    // Cleanup subscription on unmount
    return () => {
      data?.subscription?.unsubscribe()
    }
  }, [dispatch])

  return <>{children}</>
}
