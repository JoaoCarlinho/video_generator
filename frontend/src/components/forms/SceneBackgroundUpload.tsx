import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X } from 'lucide-react'
import { motion } from 'framer-motion'

export interface SceneBackgroundUploadProps {
  sceneId: string
  sceneName: string
  scenePrompt: string
  onUpload: (data: { sceneId: string; file: File | null }) => void
  currentFile?: File | null
}

export const SceneBackgroundUpload = ({
  sceneId,
  sceneName,
  scenePrompt,
  onUpload,
  currentFile = null,
}: SceneBackgroundUploadProps) => {
  const [file, setFile] = useState<File | null>(currentFile)
  const [preview, setPreview] = useState<string>('')
  const [error, setError] = useState<string>('')

  const generatePreview = useCallback((uploadedFile: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      setPreview(e.target?.result as string)
    }
    reader.readAsDataURL(uploadedFile)
  }, [])

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      setError('')

      if (acceptedFiles.length === 0) {
        return
      }

      const uploadedFile = acceptedFiles[0]

      // Validate file size (max 10MB)
      if (uploadedFile.size > 10 * 1024 * 1024) {
        setError('Image exceeds 10MB limit')
        return
      }

      // Validate file type
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(uploadedFile.type)) {
        setError('Only JPG, PNG, and WebP images are supported')
        return
      }

      // Handle rejected files
      if (rejectedFiles.length > 0) {
        setError('File was rejected. Please check file type and size.')
        return
      }

      setFile(uploadedFile)
      generatePreview(uploadedFile)
      onUpload({ sceneId, file: uploadedFile })
    },
    [sceneId, onUpload, generatePreview]
  )

  const handleRemove = () => {
    setFile(null)
    setPreview('')
    setError('')
    onUpload({ sceneId, file: null })
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp'],
    },
    maxFiles: 1,
    multiple: false,
  })

  return (
    <div className="space-y-3">
      {/* Scene Info */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-medium text-slate-300">{sceneName}</h4>
          <span className="px-2 py-0.5 bg-slate-700/50 rounded text-xs text-slate-400">
            Optional
          </span>
        </div>
        <p className="text-xs text-slate-500 line-clamp-2">{scenePrompt}</p>
      </div>

      {/* Upload Area or Preview */}
      {file && preview ? (
        <div className="relative">
          <div className="aspect-video rounded-lg overflow-hidden border border-slate-700 bg-slate-900">
            <img
              src={preview}
              alt={`${sceneName} background`}
              className="w-full h-full object-cover"
            />
          </div>
          <button
            type="button"
            onClick={handleRemove}
            className="absolute top-2 right-2 p-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors shadow-lg"
            aria-label="Remove background image"
          >
            <X className="w-4 h-4 text-white" />
          </button>
        </div>
      ) : (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-4 transition-all cursor-pointer ${
            isDragActive
              ? 'border-indigo-500 bg-indigo-500/10'
              : 'border-slate-700 bg-slate-800/30 hover:bg-slate-800/50 hover:border-slate-600'
          }`}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center justify-center text-center">
            <Upload
              className={`w-6 h-6 mb-2 ${
                isDragActive ? 'text-indigo-400' : 'text-slate-500'
              }`}
            />
            <p className="text-xs text-slate-400">
              {isDragActive ? 'Drop background image' : 'Upload custom background'}
            </p>
            <p className="text-xs text-slate-600 mt-1">
              JPG, PNG, WebP • Max 10MB
            </p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-2 bg-red-500/10 border border-red-500/50 rounded text-red-400 text-xs"
        >
          {error}
        </motion.div>
      )}
    </div>
  )
}
