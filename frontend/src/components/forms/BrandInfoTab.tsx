import React, { useState } from 'react'
import { Input } from '../ui/Input'
import { Check } from 'lucide-react'
import { cn } from '../../utils/cn'

export interface BrandInfoData {
  title: string
  brand_name: string
  brand_description: string
}

export interface BrandInfoTabProps {
  data: BrandInfoData
  onChange: (data: BrandInfoData) => void
}

export const BrandInfoTab: React.FC<BrandInfoTabProps> = ({ data, onChange }) => {
  const [charCount, setCharCount] = useState(data.brand_description?.length || 0)
  const maxChars = 500

  const handleChange = (field: keyof BrandInfoData, value: string) => {
    onChange({ ...data, [field]: value })
    if (field === 'brand_description') {
      setCharCount(value.length)
    }
  }

  const isTitleValid = data.title.trim().length >= 3
  const isBrandNameValid = data.brand_name.trim().length >= 2

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Instructions */}
      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold text-gray-900 mb-2">Tell us about your brand</h3>
        <p className="text-gray-600">
          Start by providing some basic information. This helps us understand your brand identity.
        </p>
      </div>

      {/* Project Title */}
      <div className="relative">
        <Input
          label="Project Title"
          placeholder="e.g., Premium Skincare - Summer Campaign"
          value={data.title}
          onChange={(e) => handleChange('title', e.target.value)}
          required
          helpText="Give your project a memorable name"
        />
        {isTitleValid && (
          <div className="absolute right-3 top-9 text-success-500">
            <Check className="w-5 h-5" />
          </div>
        )}
      </div>

      {/* Brand Name */}
      <div className="relative">
        <Input
          label="Brand Name"
          placeholder="Your brand name"
          value={data.brand_name}
          onChange={(e) => handleChange('brand_name', e.target.value)}
          required
          helpText="What's your brand called?"
        />
        {isBrandNameValid && (
          <div className="absolute right-3 top-9 text-success-500">
            <Check className="w-5 h-5" />
          </div>
        )}
      </div>

      {/* Brand Description */}
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Brand Description
          <span className="text-gray-500 font-normal ml-2">(Optional)</span>
        </label>
        <textarea
          placeholder="Tell us about your brand's story, values, and personality. Example: Premium skincare for conscious consumers who value sustainability and natural ingredients."
          value={data.brand_description}
          onChange={(e) => {
            if (e.target.value.length <= maxChars) {
              handleChange('brand_description', e.target.value)
            }
          }}
          rows={3}
          className={cn(
            'w-full px-4 py-3 bg-white border border-gray-200 rounded-lg',
            'text-gray-900 placeholder:text-gray-400',
            'focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
            'transition-all duration-150 resize-none'
          )}
        />
        <div className="flex justify-between items-center mt-1">
          <p className="text-xs text-gray-500">
            Help us understand your brand's personality and values
          </p>
          <p
            className={cn(
              'text-xs',
              charCount > maxChars * 0.9 ? 'text-warning-500' : 'text-gray-400'
            )}
          >
            {charCount}/{maxChars}
          </p>
        </div>
      </div>

      {/* Progress indicator */}
      <div className="pt-4">
        <div className="flex items-center gap-2 text-sm">
          <div
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-colors',
              isTitleValid && isBrandNameValid
                ? 'bg-success-500/10 text-success-600'
                : 'bg-gray-100 text-gray-500'
            )}
          >
            {isTitleValid && isBrandNameValid ? (
              <>
                <Check className="w-4 h-4" />
                <span className="font-medium">Ready to continue</span>
              </>
            ) : (
              <span>Complete required fields to continue</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
