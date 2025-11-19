/**
 * Zod validation schema for brand creation and updates
 */

import { z } from 'zod'

export const brandSchema = z.object({
  company_name: z
    .string()
    .min(2, 'Company name must be at least 2 characters')
    .max(200, 'Company name must not exceed 200 characters')
    .trim(),

  brand_name: z
    .string()
    .max(200, 'Brand name must not exceed 200 characters')
    .trim()
    .optional()
    .or(z.literal('')),

  description: z
    .string()
    .min(50, 'Description must be at least 50 characters')
    .max(1000, 'Description must not exceed 1000 characters')
    .trim(),

  guidelines: z
    .string()
    .min(100, 'Guidelines must be at least 100 characters')
    .max(5000, 'Guidelines must not exceed 5000 characters')
    .trim(),

  logo_files: z
    .array(z.instanceof(File))
    .min(1, 'At least 1 logo image is required')
    .max(5, 'Maximum 5 logo images allowed')
    .optional(),
})

export type BrandFormData = z.infer<typeof brandSchema>

// Schema for brand update (all fields optional except preserving constraints when provided)
export const brandUpdateSchema = brandSchema.partial()

export type BrandUpdateData = z.infer<typeof brandUpdateSchema>
