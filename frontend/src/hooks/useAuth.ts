/**
 * useAuth Hook: Access authentication state and functions
 * Usage: const { user, login, signup, logout } = useAuth()
 */

import { useContext } from 'react'
import { AuthContext } from '../context/AuthContext'
import type { AuthContextType } from '../types'

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }

  return context
}

export default useAuth

