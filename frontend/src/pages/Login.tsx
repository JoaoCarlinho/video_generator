/**
 * Login Page
 * Displays login form in a centered card layout
 */

import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import LoginForm from '../components/forms/LoginForm'
import { Sparkles } from 'lucide-react'

export const LoginPage: React.FC = () => {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  // Redirect if already logged in
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard')
    }
  }, [isAuthenticated, navigate])

  return (
    <div className="relative w-full min-h-screen bg-gradient-hero flex flex-col items-center justify-center px-4 py-8 sm:py-12 lg:py-16">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gold-silky/10 rounded-full blur-3xl"></div>
        <div className="absolute inset-0 bg-gradient-to-br from-gold/5 via-transparent to-transparent" />
      </div>

      {/* Content */}
      <div className="relative w-full max-w-sm sm:max-w-md lg:max-w-lg">
        {/* Header */}
        <div className="text-center mb-6 sm:mb-8 lg:mb-10">
          <div className="flex items-center justify-center gap-2 mb-3 sm:mb-4">
            <div className="p-2 bg-gold rounded-lg shadow-gold">
              <Sparkles className="w-5 h-5 sm:w-6 sm:h-6 text-gold-foreground" />
            </div>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gradient-gold">GenAds</h1>
          </div>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-off-white mb-1 sm:mb-2">Welcome back</h2>
          <p className="text-sm sm:text-base text-muted-gray">Sign in to your account to continue</p>
        </div>

        {/* Form Card */}
        <div className="bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-xl p-6 sm:p-8 lg:p-10 shadow-gold-lg">
          <LoginForm />
        </div>

        {/* Footer */}
        <p className="text-center text-xs sm:text-sm text-muted-gray mt-4 sm:mt-6 lg:mt-8">
          Protected by Supabase Authentication
        </p>
      </div>
    </div>
  )
}

export default LoginPage

