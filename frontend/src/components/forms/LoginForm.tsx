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
        <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-300">{apiError}</p>
        </div>
      )}

      {/* Email Field */}
      <div className="space-y-1.5 sm:space-y-2">
        <label htmlFor="email" className="block text-xs sm:text-sm font-medium text-white">
          Email Address
        </label>
        <div className="relative">
          <Mail className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
          <input
            id="email"
            name="email"
            type="email"
            placeholder="you@example.com"
            value={formData.email}
            onChange={handleChange}
            className={`w-full pl-10 pr-4 py-2 sm:py-2.5 bg-slate-800 border rounded-lg text-sm sm:text-base text-white placeholder-slate-500 transition-all focus:outline-none ${
              errors.email ? 'border-red-500 ring-2 ring-red-500/20' : 'border-slate-700 focus:border-transparent focus:ring-2 focus:ring-cyan-500'
            }`}
            disabled={isLoading}
          />
        </div>
        {errors.email && <p className="text-xs sm:text-sm text-red-400">{errors.email}</p>}
      </div>

      {/* Password Field */}
      <div className="space-y-1.5 sm:space-y-2">
        <label htmlFor="password" className="block text-xs sm:text-sm font-medium text-white">
          Password
        </label>
        <div className="relative">
          <Lock className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
          <input
            id="password"
            name="password"
            type={showPassword ? 'text' : 'password'}
            placeholder="••••••••"
            value={formData.password}
            onChange={handleChange}
            className={`w-full pl-10 pr-12 py-2 sm:py-2.5 bg-slate-800 border rounded-lg text-sm sm:text-base text-white placeholder-slate-500 transition-all focus:outline-none ${
              errors.password ? 'border-red-500 ring-2 ring-red-500/20' : 'border-slate-700 focus:border-transparent focus:ring-2 focus:ring-cyan-500'
            }`}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-3 text-slate-500 hover:text-slate-300 transition-colors"
            tabIndex={-1}
          >
            {showPassword ? <EyeOff className="w-4 h-4 sm:w-5 sm:h-5" /> : <Eye className="w-4 h-4 sm:w-5 sm:h-5" />}
          </button>
        </div>
        {errors.password && <p className="text-xs sm:text-sm text-red-400">{errors.password}</p>}
      </div>

      {/* Remember Me */}
      <div className="flex items-center gap-2">
        <input
          id="rememberMe"
          name="rememberMe"
          type="checkbox"
          checked={formData.rememberMe || false}
          onChange={handleChange}
          className="w-4 h-4 bg-slate-800 border border-slate-700 rounded cursor-pointer accent-cyan-500"
          disabled={isLoading}
        />
        <label htmlFor="rememberMe" className="text-xs sm:text-sm text-slate-400 cursor-pointer">
          Remember me
        </label>
      </div>

      {/* Forgot Password Link */}
      <div className="text-right">
        <Link to="/forgot-password" className="text-xs sm:text-sm text-cyan-500 hover:text-cyan-400 transition-colors">
          Forgot password?
        </Link>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className={`w-full py-2 sm:py-2.5 px-4 rounded-lg font-semibold text-sm sm:text-base transition-all ${
          isLoading
            ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
            : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:shadow-lg hover:shadow-indigo-600/50 active:scale-95'
        }`}
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-slate-300 border-t-white rounded-full animate-spin"></div>
            Signing in...
          </span>
        ) : (
          'Sign in'
        )}
      </button>

      {/* Sign Up Link */}
      <p className="text-center text-xs sm:text-sm text-slate-400">
        Don't have an account?{' '}
        <Link to="/signup" className="text-cyan-500 hover:text-cyan-400 transition-colors font-medium">
          Sign up
        </Link>
      </p>
    </form>
  )
}

export default LoginForm

