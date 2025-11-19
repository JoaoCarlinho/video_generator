/**
 * BrandOnboarding - Page for creating new brand profiles
 * Handles S3 logo uploads and brand creation
 * Uses Redux/RTK Query for state management
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BrandInfoForm } from '../components/forms/BrandInfoForm'
import { Card } from '../components/ui/Card'
import type { BrandFormData } from '../schemas/brandSchema'
import { useCreateBrandMutation } from '../store/api'
import { api } from '../services/api'
import axios from 'axios'

export const BrandOnboarding = () => {
  const navigate = useNavigate()
  const [createBrand, { isLoading: isSubmitting }] = useCreateBrandMutation()
  const [error, setError] = useState<string | null>(null)

  /**
   * Upload a single file to S3 using presigned URL
   */
  const uploadFileToS3 = async (file: File): Promise<string> => {
    try {
      // Request presigned URL from backend
      const presignedResponse = await api.post('/api/upload/presigned-url', {
        filename: file.name,
        content_type: file.type,
      })

      const { presigned_url, s3_key } = presignedResponse.data

      // Upload file directly to S3
      await axios.put(presigned_url, file, {
        headers: {
          'Content-Type': file.type,
        },
      })

      // Return S3 key for storage in database
      return s3_key
    } catch (error) {
      console.error('S3 upload error:', error)
      throw new Error(`Failed to upload ${file.name}`)
    }
  }

  /**
   * Handle form submission
   */
  const handleSubmit = async (data: BrandFormData) => {
    setError(null)

    try {
      // Upload logo files to S3
      let logoUrls: string[] = []
      if (data.logo_files && data.logo_files.length > 0) {
        console.log(`Uploading ${data.logo_files.length} logo files to S3...`)
        const uploadPromises = data.logo_files.map((file) => uploadFileToS3(file))
        logoUrls = await Promise.all(uploadPromises)
        console.log('Logo uploads complete:', logoUrls)
      }

      // Prepare brand data for API
      const brandData = {
        name: data.brand_name || data.company_name,
        logo_url: logoUrls.length > 0 ? logoUrls[0] : undefined,
        brand_guidelines_url: data.guidelines || undefined,
        primary_color: '#000000', // Default color - will be customizable in future stories
        secondary_color: undefined,
        target_audience: data.description || undefined,
      }

      // Create brand via RTK Query mutation
      console.log('Creating brand:', brandData)
      const createdBrand = await createBrand(brandData).unwrap()

      console.log('Brand created successfully:', createdBrand)

      // Show success toast (if toast system is available)
      if (window.showToast) {
        window.showToast('Brand created successfully!', 'success')
      }

      // Navigate to product management for this brand
      navigate(`/brands/${createdBrand.id}/products`)
    } catch (err: any) {
      console.error('Brand creation error:', err)

      // Extract error message
      let errorMessage = 'Failed to create brand. Please try again.'
      if (err.data?.detail) {
        errorMessage = err.data.detail
      } else if (err.message) {
        errorMessage = err.message
      }

      setError(errorMessage)

      // Show error toast (if toast system is available)
      if (window.showToast) {
        window.showToast(errorMessage, 'error')
      }
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Create Brand Profile</h1>
          <p className="text-gray-600 mt-1">
            Set up your brand identity to get started with video generation
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-8">
        <Card className="p-8">
          {error && (
            <div className="mb-6 p-4 bg-error-50 border border-error-200 rounded-lg">
              <p className="text-error-700 text-sm">{error}</p>
            </div>
          )}

          <BrandInfoForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
        </Card>
      </main>
    </div>
  )
}

// Type augmentation for global toast function (if not already defined)
declare global {
  interface Window {
    showToast?: (message: string, type: 'success' | 'error' | 'info') => void
  }
}
