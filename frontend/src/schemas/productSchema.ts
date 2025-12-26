/**
 * Zod validation schema for product creation and updates
 */

import { z } from 'zod'

// Visual style options for mobile app
export const appVisualStyleValues = [
  'modern_minimal',
  'dark_mode',
  'vibrant_colorful',
  'professional_corporate',
  'playful_friendly',
] as const

// Base schema without refinements (for type inference)
const baseProductSchema = z.object({
  product_type: z
    .string()
    .max(100, 'Product type must not exceed 100 characters')
    .trim()
    .optional()
    .or(z.literal('')),

  name: z
    .string()
    .min(1, 'Product name is required')
    .max(200, 'Product name must not exceed 200 characters')
    .trim(),

  product_gender: z
    .union([
      z.enum(['masculine', 'feminine', 'unisex']),
      z.literal('')
    ])
    .optional(),

  product_attributes: z
    .record(z.string(), z.any())
    .optional(),

  icp_segment: z
    .string()
    .min(1, 'ICP/target segment is required')
    .max(500, 'ICP segment must not exceed 500 characters')
    .trim(),

  image_files: z
    .array(z.instanceof(File))
    .max(10, 'Maximum 10 product images allowed')
    .optional(),

  // Mobile App specific fields
  app_input_mode: z
    .enum(['screenshots', 'generated'])
    .optional(),

  app_description: z
    .string()
    .max(2000, 'App description must not exceed 2000 characters')
    .optional()
    .or(z.literal('')),

  key_features: z
    .array(z.string().max(100, 'Each feature must be 100 characters or less'))
    .max(10, 'Maximum 10 features allowed')
    .optional(),

  app_visual_style: z
    .enum(appVisualStyleValues)
    .optional(),

  screen_recording: z
    .custom<File | null | undefined>()
    .optional(),
})

// Export the type from base schema
export type ProductFormData = z.infer<typeof baseProductSchema>

// Full schema with conditional validations
export const productSchema = baseProductSchema.superRefine((data, ctx) => {
  // For mobile_app with screenshots mode, require at least 1 image
  if (data.product_type === 'mobile_app' && data.app_input_mode === 'screenshots') {
    if (!data.image_files || data.image_files.length < 1) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Screenshots required for screenshot mode',
        path: ['image_files'],
      })
    }
  }

  // For mobile_app with generated mode, require app_description (min 20 chars)
  if (data.product_type === 'mobile_app' && data.app_input_mode === 'generated') {
    if (!data.app_description || data.app_description.trim().length < 20) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'App description must be at least 20 characters for generated mode',
        path: ['app_description'],
      })
    }
  }

  // For non-mobile_app products, require at least 1 image
  if (data.product_type !== 'mobile_app') {
    if (!data.image_files || data.image_files.length < 1) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'At least 1 product image is required',
        path: ['image_files'],
      })
    }
  }
})

// Schema for product update (all fields optional)
export const productUpdateSchema = baseProductSchema.partial()

export type ProductUpdateData = z.infer<typeof productUpdateSchema>
