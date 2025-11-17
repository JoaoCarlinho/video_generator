/**
 * Login Form Component
 * Email and password login with validation
 */

import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { z } from 'zod'
import { Mail, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react'

// Validation schema
const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
})

type LoginFormData = z.infer<typeof loginSchema>

export const LoginForm: React.FC = () => {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [formData, setFormData] = useState<LoginFormData>({ email: '', password: '', rememberMe: false })
  const [errors, setErrors] = useState<Partial<LoginFormData>>({})
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
    // Clear field error when user starts typing
    if (errors[name as keyof LoginFormData]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setApiError(null)

    try {
      // Validate form
      loginSchema.parse(formData)
      setErrors({})

      // Attempt login
      setIsLoading(true)
      await login(formData.email, formData.password)

      // On success, redirect to dashboard
      navigate('/dashboard')
    } catch (err) {
      if (err instanceof z.ZodError) {
        // Set validation errors
        const fieldErrors: Record<string, string> = {}
        err.issues.forEach((error) => {
          const path = String(error.path[0])
          fieldErrors[path] = error.message
        })
        setErrors(fieldErrors as Partial<LoginFormData>)
      } else {
        // API error
        const errorMessage = err instanceof Error ? err.message : 'Login failed. Please try again.'
        setApiError(errorMessage)
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5 lg:space-y-6">
      {/* API Error Alert */}
      {apiError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{apiError}</p>
        </div>
      )}

      {/* Email Field */}
      <div className="space-y-1.5 sm:space-y-2">
        <label htmlFor="email" className="block text-xs sm:text-sm font-medium text-gray-700">
          Email Address
        </label>
        <div className="relative">
          <Mail className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
          <input
            id="email"
            name="email"
            type="email"
            placeholder="you@example.com"
            value={formData.email}
            onChange={handleChange}
            className={`w-full pl-10 pr-4 py-2 sm:py-2.5 bg-white border rounded-lg text-sm sm:text-base text-gray-900 placeholder-gray-400 transition-all focus:outline-none ${
              errors.email ? 'border-red-500 ring-2 ring-red-500/20' : 'border-gray-300 focus:border-transparent focus:ring-2 focus:ring-blue-500'
            }`}
            disabled={isLoading}
          />
        </div>
        {errors.email && <p className="text-xs sm:text-sm text-red-600">{errors.email}</p>}
      </div>

      {/* Password Field */}
      <div className="space-y-1.5 sm:space-y-2">
        <label htmlFor="password" className="block text-xs sm:text-sm font-medium text-gray-700">
          Password
        </label>
        <div className="relative">
          <Lock className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
          <input
            id="password"
            name="password"
            type={showPassword ? 'text' : 'password'}
            placeholder="••••••••"
            value={formData.password}
            onChange={handleChange}
            className={`w-full pl-10 pr-12 py-2 sm:py-2.5 bg-white border rounded-lg text-sm sm:text-base text-gray-900 placeholder-gray-400 transition-all focus:outline-none ${
              errors.password ? 'border-red-500 ring-2 ring-red-500/20' : 'border-gray-300 focus:border-transparent focus:ring-2 focus:ring-blue-500'
            }`}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-3 text-gray-400 hover:text-gray-600 transition-colors"
            tabIndex={-1}
          >
            {showPassword ? <EyeOff className="w-4 h-4 sm:w-5 sm:h-5" /> : <Eye className="w-4 h-4 sm:w-5 sm:h-5" />}
          </button>
        </div>
        {errors.password && <p className="text-xs sm:text-sm text-red-600">{errors.password}</p>}
      </div>

      {/* Remember Me */}
      <div className="flex items-center gap-2">
        <input
          id="rememberMe"
          name="rememberMe"
          type="checkbox"
          checked={formData.rememberMe || false}
          onChange={handleChange}
          className="w-4 h-4 bg-white border border-gray-300 rounded cursor-pointer accent-blue-500"
          disabled={isLoading}
        />
        <label htmlFor="rememberMe" className="text-xs sm:text-sm text-gray-600 cursor-pointer">
          Remember me
        </label>
      </div>

      {/* Forgot Password Link */}
      <div className="text-right">
        <Link to="/forgot-password" className="text-xs sm:text-sm text-blue-600 hover:text-blue-700 transition-colors">
          Forgot password?
        </Link>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className={`w-full py-2 sm:py-2.5 px-4 rounded-lg font-semibold text-sm sm:text-base transition-all ${
          isLoading
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-gradient-to-r from-blue-600 to-blue-700 text-gray-50 hover:shadow-lg hover:shadow-blue-600/50 active:scale-95'
        }`}
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-gray-400 border-t-gray-600 rounded-full animate-spin"></div>
            Signing in...
          </span>
        ) : (
          'Sign in'
        )}
      </button>

      {/* Sign Up Link */}
      <p className="text-center text-xs sm:text-sm text-gray-600">
        Don't have an account?{' '}
        <Link to="/signup" className="text-blue-600 hover:text-blue-700 transition-colors font-medium">
          Sign up
        </Link>
      </p>
    </form>
  )
}

export default LoginForm

