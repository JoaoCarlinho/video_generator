/**
 * ProductForm - Form component for creating/editing products
 * Uses React Hook Form with Zod validation
 */

import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { productSchema, type ProductFormData } from '../../schemas/productSchema'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { MultiImageUpload } from './MultiImageUpload'
import { FeatureTagInput } from './FeatureTagInput'
import { VideoUpload } from './VideoUpload'
import { cn } from '../../utils/cn'
import { useState } from 'react'

// Visual style options for mobile app UI generation
const APP_VISUAL_STYLES = [
  { value: 'modern_minimal', label: 'Modern Minimal' },
  { value: 'dark_mode', label: 'Dark Mode' },
  { value: 'vibrant_colorful', label: 'Vibrant Colorful' },
  { value: 'professional_corporate', label: 'Professional Corporate' },
  { value: 'playful_friendly', label: 'Playful Friendly' },
] as const

export interface ProductFormProps {
  onSubmit: (data: ProductFormData) => Promise<void>
  onCancel?: () => void
  isSubmitting?: boolean
  initialData?: Partial<ProductFormData>
  mode?: 'create' | 'edit'
}

export const ProductForm = ({
  onSubmit,
  onCancel,
  isSubmitting = false,
  initialData,
  mode = 'create',
}: ProductFormProps) => {
  const [icpLength, setIcpLength] = useState(initialData?.icp_segment?.length || 0)

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
    watch,
  } = useForm<ProductFormData>({
    resolver: zodResolver(productSchema),
    defaultValues: {
      product_type: 'fragrance',
      name: '',
      product_gender: undefined,
      product_attributes: undefined,
      icp_segment: '',
      image_files: [],
      // Mobile app specific defaults
      app_input_mode: 'screenshots',
      app_description: '',
      key_features: [],
      app_visual_style: 'modern_minimal',
      screen_recording: undefined,
      ...initialData,
    },
  })

  // Watch icp_segment for character count
  const icpSegment = watch('icp_segment')

  // Watch product_type to conditionally show mobile app fields
  const productType = watch('product_type')

  // Watch app_input_mode to conditionally show generated mode fields
  const appInputMode = watch('app_input_mode')

  // Determine if mobile app is selected
  const isMobileApp = productType === 'mobile_app'
  const isGeneratedMode = appInputMode === 'generated'

  // Update character count
  useState(() => {
    if (icpSegment) setIcpLength(icpSegment.length)
  })

  // Debug: Log form errors on submit attempt
  const onFormSubmit = handleSubmit(
    (data) => {
      console.log('✅ Form validation passed, submitting:', data)
      onSubmit(data)
    },
    (errors) => {
      console.error('❌ Form validation failed:', errors)
      // Alert user about validation errors
      const errorMessages = Object.entries(errors)
        .map(([field, error]) => `${field}: ${error?.message}`)
        .join('\n')
      alert(`Form validation failed:\n${errorMessages}`)
    }
  )

  return (
    <form onSubmit={onFormSubmit} className="space-y-6">
      {/* Product Type (Required) */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Product Type
          <span className="text-error-500 ml-1">*</span>
        </label>
        <select
          {...register('product_type')}
          disabled={isSubmitting}
          className={cn(
            'w-full px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 transition-all duration-150',
            'focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
            'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
            'hover:border-gray-300',
            errors.product_type && 'border-error-500 focus:border-error-500 focus:ring-error-500/20'
          )}
        >
          <option value="fragrance">Fragrance</option>
          <option value="car">Car/Automotive</option>
          <option value="watch">Watch/Timepiece</option>
          <option value="energy">Energy/Utilities</option>
          <option value="mobile_app">Mobile App</option>
        </select>
        {errors.product_type && (
          <p className="text-error-500 text-xs mt-1">{errors.product_type.message}</p>
        )}
      </div>

      {/* Product Name (Required) */}
      <Input
        label="Product Name"
        placeholder="Enter product name"
        {...register('name')}
        error={errors.name?.message}
        required
        disabled={isSubmitting}
      />

      {/* Product Gender (Available for all product types) */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Product Gender / Target Demographic
        </label>
        <select
          {...register('product_gender')}
          disabled={isSubmitting}
          className={cn(
            'w-full px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 transition-all duration-150',
            'focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
            'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
            'hover:border-gray-300',
            errors.product_gender && 'border-error-500 focus:border-error-500 focus:ring-error-500/20'
          )}
        >
          <option value="">Select target demographic (optional)</option>
          <option value="masculine">Masculine</option>
          <option value="feminine">Feminine</option>
          <option value="unisex">Unisex</option>
        </select>
        {errors.product_gender && (
          <p className="text-error-500 text-xs mt-1">{errors.product_gender.message}</p>
        )}
        <p className="text-gray-500 text-xs mt-1">
          Optional: Helps tailor the video style and visual language
        </p>
      </div>

      {/* Mobile App: Input Mode Selection */}
      {isMobileApp && (
        <div className="w-full">
          <label className="block text-sm font-medium text-gray-900 mb-2">
            App Visuals Source
            <span className="text-error-500 ml-1">*</span>
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                {...register('app_input_mode')}
                value="screenshots"
                disabled={isSubmitting}
                className="w-4 h-4 text-primary-600 border-gray-300 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">Upload Screenshots</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                {...register('app_input_mode')}
                value="generated"
                disabled={isSubmitting}
                className="w-4 h-4 text-primary-600 border-gray-300 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">Generate from Description</span>
            </label>
          </div>
          <p className="text-gray-500 text-xs mt-1">
            {appInputMode === 'generated'
              ? 'AI will generate UI mockups based on your app description'
              : 'Upload actual screenshots of your mobile app'}
          </p>
        </div>
      )}

      {/* Mobile App: Generated Mode Fields */}
      {isMobileApp && isGeneratedMode && (
        <>
          {/* App Description */}
          <div className="w-full">
            <label className="block text-sm font-medium text-gray-900 mb-2">
              App Description
              <span className="text-error-500 ml-1">*</span>
            </label>
            <textarea
              {...register('app_description')}
              placeholder="Describe your app's purpose, main features, and target users (minimum 20 characters)"
              rows={4}
              disabled={isSubmitting}
              className={cn(
                'w-full px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 transition-all duration-150 resize-y min-h-[100px]',
                'focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
                'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
                'hover:border-gray-300',
                errors.app_description && 'border-error-500 focus:border-error-500 focus:ring-error-500/20'
              )}
            />
            {errors.app_description && (
              <p className="text-error-500 text-xs mt-1">{errors.app_description.message}</p>
            )}
            <p className="text-gray-500 text-xs mt-1">
              This description will be used to generate realistic UI mockups
            </p>
          </div>

          {/* Key Features */}
          <div className="w-full">
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Key Features to Showcase
            </label>
            <Controller
              name="key_features"
              control={control}
              render={({ field }) => (
                <FeatureTagInput
                  value={field.value || []}
                  onChange={field.onChange}
                  maxFeatures={10}
                  placeholder="Type a feature and press Enter"
                  disabled={isSubmitting}
                  error={errors.key_features?.message}
                />
              )}
            />
          </div>

          {/* App Visual Style */}
          <div className="w-full">
            <label className="block text-sm font-medium text-gray-900 mb-2">
              App Visual Style
            </label>
            <select
              {...register('app_visual_style')}
              disabled={isSubmitting}
              className={cn(
                'w-full px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 transition-all duration-150',
                'focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
                'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
                'hover:border-gray-300',
                errors.app_visual_style && 'border-error-500 focus:border-error-500 focus:ring-error-500/20'
              )}
            >
              {APP_VISUAL_STYLES.map((style) => (
                <option key={style.value} value={style.value}>
                  {style.label}
                </option>
              ))}
            </select>
            <p className="text-gray-500 text-xs mt-1">
              Visual style for the generated UI mockups
            </p>
          </div>
        </>
      )}

      {/* ICP Segment (Required) */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Target Audience / ICP Segment
          <span className="text-error-500 ml-1">*</span>
        </label>
        <textarea
          {...register('icp_segment', {
            onChange: (e) => setIcpLength(e.target.value.length),
          })}
          placeholder="Describe your ideal customer profile or target audience (e.g., 'Mid-market B2B companies with 50-500 employees')"
          rows={3}
          disabled={isSubmitting}
          className={cn(
            'w-full px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 transition-all duration-150 resize-y min-h-[80px]',
            'focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
            'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
            'hover:border-gray-300',
            errors.icp_segment && 'border-error-500 focus:border-error-500 focus:ring-error-500/20'
          )}
        />
        <div className="flex justify-between items-center mt-1">
          <div>
            {errors.icp_segment && (
              <p className="text-error-500 text-xs">{errors.icp_segment.message}</p>
            )}
          </div>
          <p
            className={cn(
              'text-xs',
              icpLength > 500 ? 'text-error-500' : 'text-gray-500'
            )}
          >
            {icpLength}/500
          </p>
        </div>
      </div>

      {/* Product Images / App Screenshots (conditionally required) */}
      {(!isMobileApp || !isGeneratedMode) && (
        <div className="w-full">
          <label className="block text-sm font-medium text-gray-900 mb-2">
            {isMobileApp ? 'App Screenshots' : 'Product Images'}
            <span className="text-error-500 ml-1">*</span>
          </label>
          <Controller
            name="image_files"
            control={control}
            render={({ field }) => (
              <MultiImageUpload
                onImagesChange={field.onChange}
                maxFiles={10}
                maxSize={10}
                currentImages={field.value || []}
              />
            )}
          />
          {errors.image_files && (
            <p className="text-error-500 text-xs mt-1">{errors.image_files.message}</p>
          )}
          <p className="text-gray-500 text-xs mt-1">
            {isMobileApp
              ? 'Upload 1-10 app screenshots (JPEG, PNG, or WebP, max 10MB each)'
              : 'Upload 1-10 product images (JPEG, PNG, or WebP, max 10MB each)'}
          </p>
        </div>
      )}

      {/* Mobile App: Screen Recording (Optional) */}
      {isMobileApp && (
        <div className="w-full">
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Screen Recording
            <span className="text-gray-400 text-xs ml-2">(Optional)</span>
          </label>
          <Controller
            name="screen_recording"
            control={control}
            render={({ field }) => (
              <VideoUpload
                value={field.value || null}
                onChange={field.onChange}
                maxSize={50}
                disabled={isSubmitting}
                error={errors.screen_recording?.message}
              />
            )}
          />
          <p className="text-gray-500 text-xs mt-1">
            Optional: Upload a screen recording of your app in action (MP4, MOV, WebM, max 50MB)
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end gap-3 pt-4">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={isSubmitting} className="min-w-[200px]">
          {isSubmitting
            ? mode === 'edit'
              ? 'Updating Product...'
              : 'Creating Product...'
            : mode === 'edit'
            ? 'Update Product'
            : 'Create Product'}
        </Button>
      </div>
    </form>
  )
}
