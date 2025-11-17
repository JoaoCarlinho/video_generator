import React from 'react'
import { MultiImageUpload } from './MultiImageUpload'
import { Upload, X } from 'lucide-react'
import { cn } from '../../utils/cn'

export interface AssetsData {
  product_images: File[]
  logo_images: File[]
  guidelines_file: File | null
}

export interface AssetsTabProps {
  data: AssetsData
  onChange: (data: AssetsData) => void
}

export const AssetsTab: React.FC<AssetsTabProps> = ({ data, onChange }) => {
  const handleProductImagesChange = (files: File[]) => {
    onChange({ ...data, product_images: files })
  }

  const handleLogoImagesChange = (files: File[]) => {
    onChange({ ...data, logo_images: files })
  }

  const handleGuidelinesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        alert('Guidelines file must be less than 10MB')
        return
      }

      // Validate file type (PDF or TXT)
      if (!file.type.includes('pdf') && !file.type.includes('text')) {
        alert('Please select a PDF or TXT file for guidelines')
        return
      }

      onChange({ ...data, guidelines_file: file })
    }
  }

  const handleRemoveGuidelines = () => {
    onChange({ ...data, guidelines_file: null })
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Instructions */}
      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold text-gray-900 mb-2">Upload your brand assets</h3>
        <p className="text-gray-600">
          All uploads are optional, but they help create more accurate and on-brand videos.
        </p>
      </div>

      {/* Product Images */}
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-3">Product Images</label>
        <MultiImageUpload
          onImagesChange={handleProductImagesChange}
          maxFiles={10}
          maxSize={10}
          currentImages={data.product_images}
        />
        <p className="text-xs text-gray-500 mt-2">
          💡 Upload multiple product images to give the AI better understanding
        </p>
      </div>

      {/* Logo Images */}
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-3">
          Brand Logos
          <span className="ml-2 text-xs font-normal text-gray-500">(New)</span>
        </label>
        <MultiImageUpload
          onImagesChange={handleLogoImagesChange}
          maxFiles={5}
          maxSize={5}
          currentImages={data.logo_images}
        />
        <p className="text-xs text-gray-500 mt-2">
          Upload logo variations (main logo, icon, wordmark). PNG, SVG preferred for transparency.
        </p>
      </div>

      {/* Brand Guidelines */}
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-3">Brand Guidelines</label>
        {data.guidelines_file ? (
          <div className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-500/10 rounded-lg">
                <svg
                  className="w-5 h-5 text-primary-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <div>
                <p className="text-sm text-gray-900 font-medium">{data.guidelines_file.name}</p>
                <p className="text-xs text-gray-500">
                  {(data.guidelines_file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleRemoveGuidelines}
              className="p-2 bg-error-500 hover:bg-error-600 rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-gray-50" />
            </button>
          </div>
        ) : (
          <label className="flex items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50 hover:border-gray-400 transition-all">
            <div className="flex flex-col items-center justify-center">
              <Upload className="w-6 h-6 text-gray-400 mb-2" />
              <span className="text-sm text-gray-600">Upload brand guidelines</span>
              <span className="text-xs text-gray-400 mt-1">PDF, TXT (Max 10MB)</span>
            </div>
            <input
              type="file"
              accept=".pdf,.txt,text/plain,application/pdf"
              onChange={handleGuidelinesChange}
              className="hidden"
            />
          </label>
        )}
        <p className="text-xs text-gray-500 mt-2">
          💡 AI will follow your brand guidelines for tone and style
        </p>
      </div>

      {/* Summary */}
      {(data.product_images.length > 0 ||
        data.logo_images.length > 0 ||
        data.guidelines_file) && (
        <div className="bg-success-500/10 border border-success-500/20 rounded-lg p-4">
          <p className="text-sm text-success-700">
            ✓ <strong>Assets ready:</strong>{' '}
            {[
              data.product_images.length > 0 && `${data.product_images.length} product image(s)`,
              data.logo_images.length > 0 && `${data.logo_images.length} logo(s)`,
              data.guidelines_file && 'brand guidelines',
            ]
              .filter(Boolean)
              .join(', ')}
          </p>
        </div>
      )}

      {/* Help text if no assets */}
      {data.product_images.length === 0 &&
        data.logo_images.length === 0 &&
        !data.guidelines_file && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
            <p className="text-sm text-gray-600">
              No assets uploaded yet. You can skip this step and add them later, or upload now for
              better results.
            </p>
          </div>
        )}
    </div>
  )
}
