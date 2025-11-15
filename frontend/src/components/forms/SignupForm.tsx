/**
 * Signup Form Component
 * Email, password, and terms acceptance with validation
 */

import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { z } from 'zod'
import { Mail, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react'

// Validation schema
const signupSchema = z
  .object({
    email: z.string().email('Invalid email address'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Password must contain an uppercase letter')
      .regex(/[a-z]/, 'Password must contain a lowercase letter')
      .regex(/[0-9]/, 'Password must contain a number'),
    confirmPassword: z.string(),
    agreeToTerms: z.boolean().refine((val) => val === true, {
      message: 'You must agree to the terms',
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  })

type SignupFormData = z.infer<typeof signupSchema>

export const SignupForm: React.FC = () => {
  const navigate = useNavigate()
  const { signup } = useAuth()
  const [formData, setFormData] = useState<SignupFormData>({
    email: '',
    password: '',
    confirmPassword: '',
    agreeToTerms: false,
  })
  const [errors, setErrors] = useState<Partial<SignupFormData>>({})
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
    // Clear field error when user starts typing
    if (errors[name as keyof SignupFormData]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setApiError(null)

    try {
      // Validate form
      signupSchema.parse(formData)
      setErrors({})

      // Attempt signup
      setIsLoading(true)
      await signup(formData.email, formData.password)

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
        setErrors(fieldErrors as Partial<SignupFormData>)
      } else {
        // API error
        const errorMessage = err instanceof Error ? err.message : 'Signup failed. Please try again.'
        setApiError(errorMessage)
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* API Error Alert */}
      {apiError && (
        <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-300">{apiError}</p>
        </div>
      )}

      {/* Email Field */}
      <div className="space-y-2">
        <label htmlFor="email" className="block text-sm font-medium text-white">
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
            className={`w-full pl-10 pr-4 py-2.5 bg-slate-800 border rounded-lg text-white placeholder-slate-500 transition-all focus:outline-none ${
              errors.email ? 'border-red-500 ring-2 ring-red-500/20' : 'border-slate-700 focus:border-transparent focus:ring-2 focus:ring-cyan-500'
            }`}
            disabled={isLoading}
          />
        </div>
        {errors.email && <p className="text-sm text-red-400">{errors.email}</p>}
      </div>

      {/* Password Field */}
      <div className="space-y-2">
        <label htmlFor="password" className="block text-sm font-medium text-white">
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
            className={`w-full pl-10 pr-12 py-2.5 bg-slate-800 border rounded-lg text-white placeholder-slate-500 transition-all focus:outline-none ${
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
            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        </div>
        {errors.password && <p className="text-sm text-red-400">{errors.password}</p>}
        <p className="text-xs text-slate-500">
          Must contain: 8+ characters, uppercase, lowercase, and a number
        </p>
      </div>

      {/* Confirm Password Field */}
      <div className="space-y-2">
        <label htmlFor="confirmPassword" className="block text-sm font-medium text-white">
          Confirm Password
        </label>
        <div className="relative">
          <Lock className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
          <input
            id="confirmPassword"
            name="confirmPassword"
            type={showConfirmPassword ? 'text' : 'password'}
            placeholder="••••••••"
            value={formData.confirmPassword}
            onChange={handleChange}
            className={`w-full pl-10 pr-12 py-2.5 bg-slate-800 border rounded-lg text-white placeholder-slate-500 transition-all focus:outline-none ${
              errors.confirmPassword
                ? 'border-red-500 ring-2 ring-red-500/20'
                : 'border-slate-700 focus:border-transparent focus:ring-2 focus:ring-cyan-500'
            }`}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            className="absolute right-3 top-3 text-slate-500 hover:text-slate-300 transition-colors"
            tabIndex={-1}
          >
            {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        </div>
        {errors.confirmPassword && <p className="text-sm text-red-400">{errors.confirmPassword}</p>}
      </div>

      {/* Terms Agreement */}
      <div className="flex items-start gap-3 bg-slate-800/50 border border-slate-700 rounded-lg p-4">
        <input
          id="agreeToTerms"
          name="agreeToTerms"
          type="checkbox"
          checked={formData.agreeToTerms}
          onChange={handleChange}
          className="w-5 h-5 mt-0.5 bg-slate-700 border border-slate-600 rounded cursor-pointer accent-cyan-500"
          disabled={isLoading}
        />
        <label htmlFor="agreeToTerms" className="text-sm text-slate-300 cursor-pointer">
          I agree to the{' '}
          <a href="#" className="text-cyan-500 hover:text-cyan-400 transition-colors">
            Terms of Service
          </a>{' '}
          and{' '}
          <a href="#" className="text-cyan-500 hover:text-cyan-400 transition-colors">
            Privacy Policy
          </a>
        </label>
      </div>
      {errors.agreeToTerms && <p className="text-sm text-red-400">{errors.agreeToTerms}</p>}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className={`w-full py-2.5 px-4 rounded-lg font-semibold transition-all ${
          isLoading
            ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
            : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:shadow-lg hover:shadow-indigo-600/50 active:scale-95'
        }`}
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-slate-300 border-t-white rounded-full animate-spin"></div>
            Creating account...
          </span>
        ) : (
          'Create Account'
        )}
      </button>

      {/* Login Link */}
      <p className="text-center text-sm text-slate-400">
        Already have an account?{' '}
        <Link to="/login" className="text-cyan-500 hover:text-cyan-400 transition-colors font-medium">
          Sign in
        </Link>
      </p>
    </form>
  )
}

export default SignupForm

