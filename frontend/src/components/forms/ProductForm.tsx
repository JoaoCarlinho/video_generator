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
import { cn } from '../../utils/cn'
import { useState } from 'react'

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
    defaultValues: initialData || {
      product_type: 'fragrance',
      name: '',
      product_gender: undefined,
      product_attributes: undefined,
      icp_segment: '',
      image_files: [],
    },
  })

  // Watch icp_segment for character count
  const icpSegment = watch('icp_segment')

  // Watch product_type to conditionally show gender selector
  const productType = watch('product_type')

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

      {/* Product Images (Required, 1-10) */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Product Images
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
          Upload 1-10 product images (JPEG, PNG, or WebP, max 10MB each)
        </p>
      </div>

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
