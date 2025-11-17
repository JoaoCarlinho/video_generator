import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, Image as ImageIcon } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export interface MultiImageUploadProps {
  onImagesChange: (files: File[]) => void
  maxFiles?: number
  maxSize?: number // in MB
  currentImages?: File[]
}

export const MultiImageUpload = ({
  onImagesChange,
  maxFiles = 10,
  maxSize = 10,
  currentImages = [],
}: MultiImageUploadProps) => {
  const [images, setImages] = useState<File[]>(currentImages)
  const [previews, setPreviews] = useState<string[]>([])
  const [error, setError] = useState<string>('')

  // Generate previews when images change
  const generatePreviews = useCallback((files: File[]) => {
    const newPreviews: string[] = []
    files.forEach((file) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        newPreviews.push(e.target?.result as string)
        if (newPreviews.length === files.length) {
          setPreviews(newPreviews)
        }
      }
      reader.readAsDataURL(file)
    })
  }, [])

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      setError('')

      // Check if adding files would exceed max count
      if (images.length + acceptedFiles.length > maxFiles) {
        setError(`Maximum ${maxFiles} images allowed`)
        return
      }

      // Validate file sizes and types
      const validFiles: File[] = []
      const maxSizeBytes = maxSize * 1024 * 1024

      for (const file of acceptedFiles) {
        // Check file size
        if (file.size > maxSizeBytes) {
          setError(`Image exceeds ${maxSize}MB limit`)
          return
        }

        // Check file type
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
          setError('Only JPG, PNG, and WebP images are supported')
          return
        }

        validFiles.push(file)
      }

      // Handle rejected files
      if (rejectedFiles.length > 0) {
        setError('Some files were rejected. Please check file type and size.')
        return
      }

      // Update images
      const newImages = [...images, ...validFiles]
      setImages(newImages)
      generatePreviews(newImages)
      onImagesChange(newImages)
    },
    [images, maxFiles, maxSize, onImagesChange, generatePreviews]
  )

  const handleRemoveImage = (index: number) => {
    const newImages = images.filter((_, i) => i !== index)
    const newPreviews = previews.filter((_, i) => i !== index)
    setImages(newImages)
    setPreviews(newPreviews)
    onImagesChange(newImages)
    setError('')
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp'],
    },
    maxFiles: maxFiles - images.length,
    disabled: images.length >= maxFiles,
  })

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      {images.length < maxFiles && (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 transition-all cursor-pointer ${
            isDragActive
              ? 'border-indigo-500 bg-indigo-500/10'
              : 'border-slate-700 bg-slate-800/30 hover:bg-slate-800/50 hover:border-slate-600'
          }`}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center justify-center text-center">
            <Upload
              className={`w-10 h-10 mb-3 ${
                isDragActive ? 'text-indigo-400' : 'text-slate-500'
              }`}
            />
            <p className="text-sm font-medium text-slate-300 mb-1">
              {isDragActive
                ? 'Drop images here'
                : 'Drag & drop product images, or click to select'}
            </p>
            <p className="text-xs text-slate-500">
              Up to {maxFiles} images • JPG, PNG, WebP • Max {maxSize}MB each
            </p>
            <p className="text-xs text-slate-600 mt-2">
              {images.length} / {maxFiles} images uploaded
            </p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm"
        >
          {error}
        </motion.div>
      )}

      {/* Image Grid */}
      {images.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <AnimatePresence>
            {previews.map((preview, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.2 }}
                className="relative group"
              >
                <div className="aspect-square rounded-lg overflow-hidden border border-slate-700 bg-slate-900">
                  <img
                    src={preview}
                    alt={`Product ${index + 1}`}
                    className="w-full h-full object-cover"
                  />
                </div>
                {/* Delete Button - visible on hover */}
                <button
                  type="button"
                  onClick={() => handleRemoveImage(index)}
                  className="absolute top-2 right-2 p-2 bg-red-600 hover:bg-red-700 rounded-lg transition-all opacity-0 group-hover:opacity-100 shadow-lg"
                  aria-label={`Remove image ${index + 1}`}
                >
                  <X className="w-4 h-4 text-gray-50" />
                </button>
                {/* Image Count Badge */}
                <div className="absolute bottom-2 left-2 px-2 py-1 bg-slate-900/80 backdrop-blur-sm rounded text-xs text-slate-300 font-medium">
                  {index + 1}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Helper Text */}
      {images.length > 0 && images.length < maxFiles && (
        <p className="text-xs text-slate-500">
          💡 Add more images to give the AI better product understanding
        </p>
      )}
      {images.length === maxFiles && (
        <p className="text-xs text-emerald-400">
          ✅ Maximum number of images uploaded
        </p>
      )}
    </div>
  )
}
