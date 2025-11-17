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

// Reference Image Types (NEW)
export interface ExtractedStyle {
  colors: string[]
  mood: string
  lighting: string
  camera: string
  atmosphere: string
  texture: string
}

export interface ReferenceImage {
  localPath?: string
  uploadedAt?: string
  extractedStyle?: ExtractedStyle
  extractedAt?: string
}

// Project Types
export interface BrandConfig {
  name: string
  description?: string
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
  brief?: string
  brand_name: string
  mood?: string
  duration?: number
  product_image_url?: string
  logo_url?: string
  guidelines_url?: string
  creative_prompt?: string
  brand_description?: string
  target_audience?: string
  target_duration?: number
  // Phase 9: Perfume-specific fields
  perfume_name: string
  perfume_gender: 'masculine' | 'feminine' | 'unisex'
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

// PHASE 9: Video Style Types (Updated to 3 perfume styles only)
export type VideoStyleType = 'gold_luxe' | 'dark_elegance' | 'romantic_floral'

export interface VideoStyle {
  id: string
  name: string
  description: string
  short_description?: string
  keywords: string[]
  examples?: string[]
  best_for?: string[]
  icon?: string
  color?: string
}

export interface SelectedStyleConfig {
  style: VideoStyleType | null
  source?: 'user_selected' | 'llm_inferred'
  applied_at?: string
  display_name?: string
}

// PHASE 7: Update CreateProjectInput to include style
export interface CreateProjectInputWithStyle extends CreateProjectInput {
  selected_style?: VideoStyleType | null
}

