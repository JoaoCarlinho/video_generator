/**
 * Zod validation schema for product creation and updates
 */

import { z } from 'zod'

export const productSchema = z.object({
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

  icp_segment: z
    .string()
    .min(1, 'ICP/target segment is required')
    .max(500, 'ICP segment must not exceed 500 characters')
    .trim(),

  image_files: z
    .array(z.instanceof(File))
    .min(1, 'At least 1 product image is required')
    .max(10, 'Maximum 10 product images allowed'),
})

export type ProductFormData = z.infer<typeof productSchema>

// Schema for product update (all fields optional except preserving constraints when provided)
export const productUpdateSchema = productSchema.partial()

export type ProductUpdateData = z.infer<typeof productUpdateSchema>
