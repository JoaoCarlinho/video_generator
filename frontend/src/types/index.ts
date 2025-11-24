/**
 * Core TypeScript type definitions for GenAds frontend
 */

// Auth Types
export interface User {
  id: string
  email: string
  created_at: string
}

// Brand Types (Epic 1)
export interface Brand {
  id: string
  user_id: string
  name: string
  logo_url?: string
  brand_guidelines_url?: string
  primary_color: string
  secondary_color?: string
  target_audience?: string
  created_at: string
  updated_at: string
}

// Product Types (Epic 1)
export interface Product {
  id: string
  brand_id: string
  product_type?: string
  name: string
  product_gender?: 'masculine' | 'feminine' | 'unisex'
  product_attributes?: Record<string, any>
  icp_segment: string
  image_urls?: string[]
  created_at: string
  updated_at: string
}

// Campaign Types (Epic 2)
export interface Cinematography {
  camera_aspect: string
  lighting: string
  mood: string
  transition: string
  environment: string
  setting: string
}

export interface SceneConfig {
  scene_number: number
  creative_vision: string
  reference_images: string[]  // Array of 3 S3 URLs
  cinematography: Cinematography
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

// Campaign Types - matches backend database model
export type AspectRatio = '9:16' | '16:9' | '1:1'

export interface SceneBackground {
  sceneId: string
  backgroundUrl: string
}

export interface Campaign {
  id: string
  product_id: string
  name: string
  seasonal_event: string
  year: number
  display_name: string
  duration: number  // 15, 30, 45, or 60 seconds
  scene_configs: SceneConfig[]
  status: 'draft' | 'generating' | 'completed' | 'failed'
  created_at: string
  updated_at: string
}

export interface CreateCampaignInput {
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
  // Phase 9: Product-specific fields
  product_name: string
  product_gender: 'masculine' | 'feminine' | 'unisex'
  // Phase 3: Multi-variation support
  num_variations?: 1 | 2 | 3 // Number of video variations (1-3)
}

// Generation Types
export interface GenerationJob {
  id: string
  campaignId: string
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

// PHASE 9: Video Style Types (Updated to 3 product styles only)
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

// PHASE 7: Update CreateCampaignInput to include style
export interface CreateCampaignInputWithStyle extends CreateCampaignInput {
  selected_style?: VideoStyleType | null
}

// PHASE 3: Scene Editing Types
export interface SceneInfo {
  scene_index: number
  scene_id: number
  role: string
  duration: number
  background_prompt: string
  video_url: string
  thumbnail_url?: string
  edit_count: number
  last_edited_at?: string
}

export interface EditSceneRequest {
  edit_prompt: string
}

export interface EditSceneResponse {
  job_id: string
  estimated_cost: number
  estimated_duration_seconds: number
  message: string
}

export interface EditHistoryRecord {
  edit_id: string
  timestamp: string
  scene_index: number
  edit_prompt: string
  changes_summary?: string
  cost: number
  duration_seconds: number
}

