/**
 * Signup Page
 * Displays signup form in a centered card layout
 */

import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import SignupForm from '../components/forms/SignupForm'
import { Sparkles, Zap } from 'lucide-react'

export const SignupPage: React.FC = () => {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  // Redirect if already logged in
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard')
    }
  }, [isAuthenticated, navigate])

  return (
    <div className="relative w-full min-h-screen bg-gradient-light flex flex-col items-center justify-center px-4 py-8 sm:py-12 lg:py-16">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-100/40 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-50/60 rounded-full blur-3xl"></div>
      </div>

      {/* Content */}
      <div className="relative w-full max-w-sm sm:max-w-md lg:max-w-lg overflow-y-auto max-h-[90vh]">
        {/* Header */}
        <div className="text-center mb-6 sm:mb-8 lg:mb-10">
          <div className="flex items-center justify-center gap-2 mb-3 sm:mb-4">
            <div className="p-2 bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg shadow-md">
              <Zap className="w-5 h-5 sm:w-6 sm:h-6 text-gray-50" />
            </div>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900">GenAds</h1>
          </div>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-1 sm:mb-2">Get started</h2>
          <p className="text-xs sm:text-sm text-gray-600">Create an account to generate amazing ad videos</p>
        </div>

        {/* Form Card */}
        <div className="bg-white/80 backdrop-blur border border-gray-200/50 rounded-xl p-6 sm:p-8 lg:p-10 shadow-xl">
          <SignupForm />
        </div>

        {/* Footer */}
        <p className="text-center text-xs sm:text-sm text-gray-500 mt-4 sm:mt-6 lg:mt-8">
          Protected by Supabase Authentication
        </p>
      </div>
    </div>
  )
}

export default SignupPage

