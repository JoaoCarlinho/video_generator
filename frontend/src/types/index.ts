/**
 * Core TypeScript type definitions for GenAds frontend
 */

// Auth Types
export interface User {
  id: string
  email: string
  created_at: string
}

export interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  error: string | null
}

// Project Types
export interface BrandConfig {
  name: string
  primaryColor: string
  secondaryColor: string
}

export interface Scene {
  id: string
  name: string
  prompt: string
  duration: number
  productUsage: 'none' | 'static_insert' | 'animated_insert' | 'dominant_center'
}

export interface Project {
  id: string
  userId: string
  projectName: string
  brief: string
  brandConfig: BrandConfig
  targetAudience: string
  duration: number
  mood: string[]
  productImageUrl?: string
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed'
  adProjectJson?: Record<string, any>
  createdAt: string
  updatedAt: string
}

export interface CreateProjectInput {
  title: string
  brief: string
  brand_name: string
  mood: string
  duration: number
  primary_color: string
  secondary_color?: string
  product_image_url?: string
}

// Generation Types
export interface GenerationJob {
  id: string
  projectId: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  progress: number
  currentStep: string
  totalCost: number
  startedAt: string
  completedAt?: string
  error?: string
}

export interface ProgressUpdate {
  status: string
  progress: number
  currentStep: string
  totalCost: number
  estimatedTimeRemaining: number
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// Form Types
export interface LoginFormData {
  email: string
  password: string
  rememberMe?: boolean
}

export interface SignupFormData {
  email: string
  password: string
  confirmPassword: string
  agreeToTerms: boolean
}

