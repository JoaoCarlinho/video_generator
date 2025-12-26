/**
 * VideoUpload - Component for uploading screen recording videos
 * Supports MP4, MOV, WebM with 50MB max size limit
 */

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Film, X, AlertCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/cn'

export interface VideoUploadProps {
  value: File | null
  onChange: (file: File | null) => void
  maxSize?: number // in MB
  disabled?: boolean
  error?: string
}

const ACCEPTED_VIDEO_TYPES = {
  'video/mp4': ['.mp4'],
  'video/quicktime': ['.mov'],
  'video/webm': ['.webm'],
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export const VideoUpload = ({
  value,
  onChange,
  maxSize = 50,
  disabled = false,
  error,
}: VideoUploadProps) => {
  const [uploadError, setUploadError] = useState('')
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null)

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      setUploadError('')

      // Handle rejected files
      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0]
        if (rejection.errors?.[0]?.code === 'file-too-large') {
          setUploadError(`Video must be under ${maxSize}MB`)
        } else if (rejection.errors?.[0]?.code === 'file-invalid-type') {
          setUploadError('Only MP4, MOV, and WebM videos are supported')
        } else {
          setUploadError('Invalid file. Please try again.')
        }
        return
      }

      if (acceptedFiles.length === 0) {
        return
      }

      const file = acceptedFiles[0]
      const maxSizeBytes = maxSize * 1024 * 1024

      // Double-check file size
      if (file.size > maxSizeBytes) {
        setUploadError(`Video must be under ${maxSize}MB`)
        return
      }

      // Validate video type
      const validTypes = ['video/mp4', 'video/quicktime', 'video/webm']
      if (!validTypes.includes(file.type)) {
        setUploadError('Only MP4, MOV, and WebM videos are supported')
        return
      }

      // Create preview URL
      const previewUrl = URL.createObjectURL(file)
      setVideoPreviewUrl(previewUrl)
      onChange(file)
    },
    [maxSize, onChange]
  )

  const handleRemove = useCallback(() => {
    if (videoPreviewUrl) {
      URL.revokeObjectURL(videoPreviewUrl)
    }
    setVideoPreviewUrl(null)
    onChange(null)
    setUploadError('')
  }, [videoPreviewUrl, onChange])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_VIDEO_TYPES,
    maxFiles: 1,
    maxSize: maxSize * 1024 * 1024,
    disabled: disabled || !!value,
    multiple: false,
  })

  return (
    <div className="w-full space-y-3">
      {/* Upload Zone or Preview */}
      <AnimatePresence mode="wait">
        {!value ? (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div
              {...getRootProps()}
              className={cn(
                'border-2 border-dashed rounded-lg p-6 transition-all cursor-pointer',
                isDragActive
                  ? 'border-primary-500 bg-primary-500/10'
                  : 'border-gray-300 bg-gray-50 hover:bg-gray-100 hover:border-gray-400',
                disabled && 'opacity-50 cursor-not-allowed',
                (error || uploadError) && 'border-error-500 bg-error-50'
              )}
            >
              <input {...getInputProps()} />
              <div className="flex flex-col items-center justify-center text-center">
                <Upload
                  className={cn(
                    'w-8 h-8 mb-2',
                    isDragActive ? 'text-primary-500' : 'text-gray-400'
                  )}
                />
                <p className="text-sm font-medium text-gray-700 mb-1">
                  {isDragActive
                    ? 'Drop video here'
                    : 'Drag & drop a screen recording, or click to select'}
                </p>
                <p className="text-xs text-gray-500">
                  MP4, MOV, or WebM - Max {maxSize}MB
                </p>
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="preview"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="relative rounded-lg border border-gray-200 bg-gray-50 p-4"
          >
            <div className="flex items-start gap-4">
              {/* Video Icon or Preview */}
              <div className="flex-shrink-0 w-16 h-16 rounded-lg bg-gray-200 flex items-center justify-center overflow-hidden">
                {videoPreviewUrl ? (
                  <video
                    src={videoPreviewUrl}
                    className="w-full h-full object-cover"
                    muted
                  />
                ) : (
                  <Film className="w-8 h-8 text-gray-400" />
                )}
              </div>

              {/* File Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {value.name}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {formatFileSize(value.size)}
                </p>
                <p className="text-xs text-primary-600 mt-1">
                  Ready for upload
                </p>
              </div>

              {/* Remove Button */}
              {!disabled && (
                <button
                  type="button"
                  onClick={handleRemove}
                  className="flex-shrink-0 p-1.5 text-gray-400 hover:text-error-500 hover:bg-error-50 rounded-full transition-colors"
                  aria-label="Remove video"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Message */}
      {(error || uploadError) && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 text-error-500 text-xs"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error || uploadError}</span>
        </motion.div>
      )}
    </div>
  )
}
