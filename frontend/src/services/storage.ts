/**
 * Supabase Storage Service
 * Handles file uploads for product images and scene backgrounds
 */

import { supabase } from './auth'

const STORAGE_BUCKET = 'campaign-assets' // You may need to create this bucket in Supabase

/**
 * Upload multiple product images for a campaign
 * @param campaignId - The campaign ID for folder organization
 * @param files - Array of image files to upload
 * @returns Array of public URLs for uploaded images
 */
export const uploadProductImages = async (
  campaignId: string,
  files: File[]
): Promise<string[]> => {
  const urls: string[] = []

  for (const file of files) {
    const timestamp = Date.now()
    const fileName = `${timestamp}_${file.name.replace(/[^a-zA-Z0-9.-]/g, '_')}`
    const filePath = `campaigns/${campaignId}/products/${fileName}`

    const { data, error } = await supabase.storage
      .from(STORAGE_BUCKET)
      .upload(filePath, file, {
        cacheControl: '3600',
        upsert: false,
      })

    if (error) {
      console.error(`Failed to upload ${file.name}:`, error)
      throw new Error(`Failed to upload ${file.name}: ${error.message}`)
    }

    // Get public URL
    const {
      data: { publicUrl },
    } = supabase.storage.from(STORAGE_BUCKET).getPublicUrl(data.path)

    urls.push(publicUrl)
  }

  return urls
}

/**
 * Upload a single scene background image
 * @param campaignId - The campaign ID for folder organization
 * @param sceneId - The scene ID
 * @param file - The background image file
 * @returns Public URL for the uploaded image
 */
export const uploadSceneBackground = async (
  campaignId: string,
  sceneId: string,
  file: File
): Promise<string> => {
  const timestamp = Date.now()
  const fileName = `${sceneId}_${timestamp}_${file.name.replace(/[^a-zA-Z0-9.-]/g, '_')}`
  const filePath = `campaigns/${campaignId}/scenes/${fileName}`

  const { data, error } = await supabase.storage
    .from(STORAGE_BUCKET)
    .upload(filePath, file, {
      cacheControl: '3600',
      upsert: false,
    })

  if (error) {
    console.error(`Failed to upload scene background for ${sceneId}:`, error)
    throw new Error(`Failed to upload scene background: ${error.message}`)
  }

  // Get public URL
  const {
    data: { publicUrl },
  } = supabase.storage.from(STORAGE_BUCKET).getPublicUrl(data.path)

  return publicUrl
}

/**
 * Delete files from storage (cleanup utility)
 * @param paths - Array of file paths to delete
 */
export const deleteFiles = async (paths: string[]): Promise<void> => {
  const { error } = await supabase.storage.from(STORAGE_BUCKET).remove(paths)

  if (error) {
    console.error('Failed to delete files:', error)
    throw new Error(`Failed to delete files: ${error.message}`)
  }
}
