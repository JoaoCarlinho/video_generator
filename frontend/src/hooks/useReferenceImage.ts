/**
 * Hook for uploading and managing reference images
 * Handles the upload process to POST /api/projects/{projectId}/reference-image
 */

import { useState } from 'react'
import api from '@/services/api'

interface UseReferenceImageReturn {
  isLoading: boolean
  error: string | null
  uploadReferenceImage: (file: File, projectId: string) => Promise<boolean>
  clearError: () => void
}

export function useReferenceImage(): UseReferenceImageReturn {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const uploadReferenceImage = async (file: File, projectId: string): Promise<boolean> => {
    setIsLoading(true)
    setError(null)

    try {
      // Validate file
      const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
      if (!allowedTypes.includes(file.type)) {
        setError('Please select an image file (JPEG, PNG, or WebP)')
        return false
      }

      if (file.size > 5 * 1024 * 1024) {
        setError('Image must be less than 5MB')
        return false
      }

      console.log(`📤 Uploading reference image: ${file.name}`)

      // Create FormData for multipart upload
      const formData = new FormData()
      formData.append('file', file)

      // Upload to backend endpoint
      const response = await api.post(
        `/api/projects/${projectId}/reference-image`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )

      if (response.status === 200 && response.data.success) {
        console.log('✅ Reference image uploaded successfully')
        console.log(`📝 Message: ${response.data.message}`)
        return true
      } else {
        setError('Failed to upload reference image')
        return false
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to upload reference image'
      console.error('❌ Error uploading reference image:', err)
      setError(message)
      return false
    } finally {
      setIsLoading(false)
    }
  }

  const clearError = () => {
    setError(null)
  }

  return {
    isLoading,
    error,
    uploadReferenceImage,
    clearError,
  }
}

