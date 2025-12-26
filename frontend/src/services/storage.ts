/**
 * Storage Service
 * Handles file uploads for product images and scene backgrounds
 * Uses backend API with S3 storage
 */

// Get API URL from environment
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Get auth token from localStorage
 */
const getAuthToken = (): string | null => {
  return localStorage.getItem('authToken')
}

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
  const token = getAuthToken()

  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('asset_type', 'product')
    formData.append('campaign_id', campaignId)

    const response = await fetch(`${API_URL}/api/upload-asset`, {
      method: 'POST',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json()
      console.error(`Failed to upload ${file.name}:`, error)
      throw new Error(`Failed to upload ${file.name}: ${error.detail || 'Unknown error'}`)
    }

    const data = await response.json()
    urls.push(data.file_url)
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
  const token = getAuthToken()

  const formData = new FormData()
  formData.append('file', file)
  formData.append('asset_type', 'product') // Use 'product' type for scene backgrounds
  formData.append('campaign_id', campaignId)

  const response = await fetch(`${API_URL}/api/upload-asset`, {
    method: 'POST',
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json()
    console.error(`Failed to upload scene background for ${sceneId}:`, error)
    throw new Error(`Failed to upload scene background: ${error.detail || 'Unknown error'}`)
  }

  const data = await response.json()
  return data.file_url
}

/**
 * Delete files from storage (cleanup utility)
 * @param campaignId - Campaign ID to cleanup
 */
export const deleteFiles = async (campaignId: string): Promise<void> => {
  const token = getAuthToken()

  const response = await fetch(`${API_URL}/api/cleanup-campaign/${campaignId}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
  })

  if (!response.ok) {
    const error = await response.json()
    console.error('Failed to delete files:', error)
    throw new Error(`Failed to delete files: ${error.detail || 'Unknown error'}`)
  }
}
