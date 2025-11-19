/**
 * useAuth Hook: Access authentication state and functions
 * Usage: const { user, login, signup, logout } = useAuth()
 * Migrated from AuthContext to Redux
 */

import { useCallback } from 'react'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import {
  login as loginAction,
  signup as signupAction,
  logout as logoutAction,
  clearError,
} from '../store/slices/authSlice'
import type { AuthContextType } from '../types'

export const useAuth = (): AuthContextType => {
  const dispatch = useAppDispatch()

  const user = useAppSelector((state) => state.auth.user)
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated)
  const isLoading = useAppSelector((state) => state.auth.isLoading)
  const error = useAppSelector((state) => state.auth.error)

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await dispatch(loginAction({ email, password }))
      if (loginAction.rejected.match(result)) {
        throw new Error(result.payload as string)
      }
    },
    [dispatch]
  )

  const signup = useCallback(
    async (email: string, password: string) => {
      const result = await dispatch(signupAction({ email, password }))
      if (signupAction.rejected.match(result)) {
        throw new Error(result.payload as string)
      }
    },
    [dispatch]
  )

  const logout = useCallback(async () => {
    const result = await dispatch(logoutAction())
    if (logoutAction.rejected.match(result)) {
      throw new Error(result.payload as string)
    }
  }, [dispatch])

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    signup,
    logout,
    error,
  }
}

export default useAuth

