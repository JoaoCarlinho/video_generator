/**
 * BrandInfoForm - Form component for creating/editing brand profiles
 * Uses React Hook Form with Zod validation
 */

import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { brandSchema, type BrandFormData } from '../../schemas/brandSchema'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { MultiImageUpload } from './MultiImageUpload'
import { cn } from '../../utils/cn'
import { useState } from 'react'

export interface BrandInfoFormProps {
  onSubmit: (data: BrandFormData) => Promise<void>
  isSubmitting?: boolean
  initialData?: Partial<BrandFormData>
}

export const BrandInfoForm = ({
  onSubmit,
  isSubmitting = false,
  initialData,
}: BrandInfoFormProps) => {
  const [descriptionLength, setDescriptionLength] = useState(initialData?.description?.length || 0)
  const [guidelinesLength, setGuidelinesLength] = useState(initialData?.guidelines?.length || 0)

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
    watch,
  } = useForm<BrandFormData>({
    resolver: zodResolver(brandSchema),
    defaultValues: initialData || {
      company_name: '',
      brand_name: '',
      description: '',
      guidelines: '',
      logo_files: [],
    },
  })

  // Watch description and guidelines for character count
  const description = watch('description')
  const guidelines = watch('guidelines')

  // Update character counts
  useState(() => {
    if (description) setDescriptionLength(description.length)
    if (guidelines) setGuidelinesLength(guidelines.length)
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Company Name */}
      <Input
        label="Company Name"
        placeholder="Enter your company name"
        {...register('company_name')}
        error={errors.company_name?.message}
        required
        disabled={isSubmitting}
      />

      {/* Brand Name (Optional) */}
      <Input
        label="Brand Name"
        placeholder="Optional: If different from company name"
        {...register('brand_name')}
        error={errors.brand_name?.message}
        helpText="Leave blank to use company name"
        disabled={isSubmitting}
      />

      {/* Description */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Brand Description
          <span className="text-error-500 ml-1">*</span>
        </label>
        <textarea
          {...register('description', {
            onChange: (e) => setDescriptionLength(e.target.value.length),
          })}
          placeholder="Describe your brand story, values, and mission (50-1000 characters)"
          rows={4}
          disabled={isSubmitting}
          className={cn(
            'w-full px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 transition-all duration-150 resize-y min-h-[100px]',
            'focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
            'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
            'hover:border-gray-300',
            errors.description && 'border-error-500 focus:border-error-500 focus:ring-error-500/20'
          )}
        />
        <div className="flex justify-between items-center mt-1">
          <div>
            {errors.description && (
              <p className="text-error-500 text-xs">{errors.description.message}</p>
            )}
          </div>
          <p
            className={cn(
              'text-xs',
              descriptionLength < 50 || descriptionLength > 1000
                ? 'text-error-500'
                : 'text-gray-500'
            )}
          >
            {descriptionLength}/1000
          </p>
        </div>
      </div>

      {/* Guidelines (Rich Text Area) */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Brand Guidelines
          <span className="text-error-500 ml-1">*</span>
        </label>
        <textarea
          {...register('guidelines', {
            onChange: (e) => setGuidelinesLength(e.target.value.length),
          })}
          placeholder="Provide detailed brand guidelines including voice, tone, style notes, dos and don'ts (100-5000 characters)"
          rows={8}
          disabled={isSubmitting}
          className={cn(
            'w-full px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 transition-all duration-150 resize-y min-h-[200px]',
            'focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
            'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
            'hover:border-gray-300',
            errors.guidelines && 'border-error-500 focus:border-error-500 focus:ring-error-500/20'
          )}
        />
        <div className="flex justify-between items-center mt-1">
          <div>
            {errors.guidelines && (
              <p className="text-error-500 text-xs">{errors.guidelines.message}</p>
            )}
          </div>
          <p
            className={cn(
              'text-xs',
              guidelinesLength < 100 || guidelinesLength > 5000
                ? 'text-error-500'
                : 'text-gray-500'
            )}
          >
            {guidelinesLength}/5000
          </p>
        </div>
      </div>

      {/* Logo Upload */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Brand Logos
          <span className="text-error-500 ml-1">*</span>
        </label>
        <Controller
          name="logo_files"
          control={control}
          render={({ field }) => (
            <MultiImageUpload
              onImagesChange={field.onChange}
              maxFiles={5}
              maxSize={10}
              currentImages={field.value || []}
            />
          )}
        />
        {errors.logo_files && (
          <p className="text-error-500 text-xs mt-1">{errors.logo_files.message}</p>
        )}
        <p className="text-gray-500 text-xs mt-1">
          Upload 1-5 logo images (JPEG, PNG, or WebP, max 10MB each)
        </p>
      </div>

      {/* Submit Button */}
      <div className="flex justify-end gap-3 pt-4">
        <Button type="submit" disabled={isSubmitting} className="min-w-[200px]">
          {isSubmitting ? 'Creating Brand...' : 'Create Brand'}
        </Button>
      </div>
    </form>
  )
}
