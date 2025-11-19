/**
 * ReferenceImageUpload Component
 * Upload component for scene reference images (exactly 3: theme, start, end)
 */

import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, Image as ImageIcon } from 'lucide-react'

interface ReferenceImageUploadProps {
  images: string[] // Array of 3 S3 URLs or empty strings
  onImagesChange: (images: string[]) => void
  onFileSelected: (file: File, index: number) => Promise<string> // Upload handler returns S3 URL
}

const IMAGE_LABELS = [
  { index: 0, label: 'Theme Image', description: 'Overall visual theme and style' },
  { index: 1, label: 'Start Interpolation', description: 'Starting point for animation' },
  { index: 2, label: 'End Interpolation', description: 'Ending point for animation' },
]

export function ReferenceImageUpload({
  images,
  onImagesChange,
  onFileSelected,
}: ReferenceImageUploadProps) {
  const [uploadingIndex, setUploadingIndex] = useState<number | null>(null)
  const [error, setError] = useState<string>('')

  const handleDrop = useCallback(
    async (acceptedFiles: File[], index: number) => {
      if (acceptedFiles.length === 0) return

      const file = acceptedFiles[0]
      setError('')
      setUploadingIndex(index)

      try {
        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
          setError('Image exceeds 10MB limit')
          setUploadingIndex(null)
          return
        }

        // Validate file type
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
          setError('Only JPG, PNG, and WebP images are supported')
          setUploadingIndex(null)
          return
        }

        // Upload file and get S3 URL
        const s3Url = await onFileSelected(file, index)

        // Update images array
        const newImages = [...images]
        newImages[index] = s3Url
        onImagesChange(newImages)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to upload image')
      } finally {
        setUploadingIndex(null)
      }
    },
    [images, onFileSelected, onImagesChange]
  )

  const handleRemove = (index: number) => {
    const newImages = [...images]
    newImages[index] = ''
    onImagesChange(newImages)
    setError('')
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Reference Images
          <span className="text-red-500 ml-1">*</span>
        </label>
        <p className="text-xs text-gray-600 mb-3">
          Upload 3 reference images to guide the visual generation for this scene
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Image Upload Slots */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {IMAGE_LABELS.map(({ index, label, description }) => {
          const imageUrl = images[index]
          const isUploading = uploadingIndex === index

          return (
            <ImageSlot
              key={index}
              label={label}
              description={description}
              imageUrl={imageUrl}
              isUploading={isUploading}
              onDrop={(files) => handleDrop(files, index)}
              onRemove={() => handleRemove(index)}
            />
          )
        })}
      </div>
    </div>
  )
}

// Individual image slot component
interface ImageSlotProps {
  label: string
  description: string
  imageUrl: string
  isUploading: boolean
  onDrop: (files: File[]) => void
  onRemove: () => void
}

function ImageSlot({
  label,
  description,
  imageUrl,
  isUploading,
  onDrop,
  onRemove,
}: ImageSlotProps) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp'],
    },
    maxFiles: 1,
    disabled: isUploading,
  })

  return (
    <div className="space-y-2">
      <div className="text-sm">
        <p className="font-medium text-gray-900">{label}</p>
        <p className="text-xs text-gray-500">{description}</p>
      </div>

      {!imageUrl ? (
        // Upload dropzone
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-6 transition-all cursor-pointer aspect-square flex flex-col items-center justify-center
            ${
              isDragActive
                ? 'border-purple-500 bg-purple-50'
                : 'border-gray-300 bg-gray-50 hover:bg-gray-100 hover:border-gray-400'
            }
            ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <input {...getInputProps()} />
          {isUploading ? (
            <>
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mb-2"></div>
              <p className="text-xs text-gray-600">Uploading...</p>
            </>
          ) : (
            <>
              <Upload
                className={`w-8 h-8 mb-2 ${isDragActive ? 'text-purple-600' : 'text-gray-400'}`}
              />
              <p className="text-xs text-gray-600 text-center">
                {isDragActive ? 'Drop here' : 'Drag & drop or click'}
              </p>
            </>
          )}
        </div>
      ) : (
        // Image preview
        <div className="relative group aspect-square">
          <div className="w-full h-full rounded-lg overflow-hidden border-2 border-gray-300 bg-gray-100">
            <img src={imageUrl} alt={label} className="w-full h-full object-cover" />
          </div>
          <button
            type="button"
            onClick={onRemove}
            className="absolute top-2 right-2 p-1.5 bg-red-600 hover:bg-red-700 rounded-full transition-all shadow-lg hover:scale-110"
            aria-label={`Remove ${label}`}
          >
            <X className="w-4 h-4 text-white" />
          </button>
        </div>
      )}
    </div>
  )
}
