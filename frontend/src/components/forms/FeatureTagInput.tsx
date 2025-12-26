/**
 * FeatureTagInput - Tag input component for entering app features
 * Allows adding/removing feature tags with Enter key support
 */

import { useState, useCallback, KeyboardEvent } from 'react'
import { X } from 'lucide-react'
import { cn } from '../../utils/cn'

export interface FeatureTagInputProps {
  value: string[]
  onChange: (features: string[]) => void
  maxFeatures?: number
  maxLength?: number
  placeholder?: string
  disabled?: boolean
  error?: string
}

export const FeatureTagInput = ({
  value = [],
  onChange,
  maxFeatures = 10,
  maxLength = 100,
  placeholder = 'Type a feature and press Enter',
  disabled = false,
  error,
}: FeatureTagInputProps) => {
  const [inputValue, setInputValue] = useState('')
  const [inputError, setInputError] = useState('')

  const handleAddFeature = useCallback(() => {
    const trimmedValue = inputValue.trim()

    // Validate input
    if (!trimmedValue) {
      return
    }

    if (trimmedValue.length > maxLength) {
      setInputError(`Feature must be ${maxLength} characters or less`)
      return
    }

    if (value.length >= maxFeatures) {
      setInputError(`Maximum ${maxFeatures} features allowed`)
      return
    }

    // Check for duplicates
    if (value.some(f => f.toLowerCase() === trimmedValue.toLowerCase())) {
      setInputError('This feature already exists')
      return
    }

    // Add feature
    onChange([...value, trimmedValue])
    setInputValue('')
    setInputError('')
  }, [inputValue, value, onChange, maxFeatures, maxLength])

  const handleRemoveFeature = useCallback((index: number) => {
    const newFeatures = value.filter((_, i) => i !== index)
    onChange(newFeatures)
    setInputError('')
  }, [value, onChange])

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddFeature()
    }
    // Allow backspace to remove last tag when input is empty
    if (e.key === 'Backspace' && !inputValue && value.length > 0) {
      handleRemoveFeature(value.length - 1)
    }
  }, [handleAddFeature, handleRemoveFeature, inputValue, value.length])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value)
    setInputError('')
  }

  return (
    <div className="w-full">
      {/* Tags Display */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {value.map((feature, index) => (
            <span
              key={index}
              className={cn(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm',
                'bg-primary-100 text-primary-700 border border-primary-200',
                disabled && 'opacity-50'
              )}
            >
              <span className="max-w-[200px] truncate">{feature}</span>
              {!disabled && (
                <button
                  type="button"
                  onClick={() => handleRemoveFeature(index)}
                  className="p-0.5 hover:bg-primary-200 rounded-full transition-colors"
                  aria-label={`Remove ${feature}`}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </span>
          ))}
        </div>
      )}

      {/* Input Field */}
      {value.length < maxFeatures && (
        <div className="relative">
          <input
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            maxLength={maxLength}
            className={cn(
              'w-full px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 transition-all duration-150',
              'focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
              'hover:border-gray-300',
              (error || inputError) && 'border-error-500 focus:border-error-500 focus:ring-error-500/20'
            )}
          />
          {inputValue && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">
              Press Enter to add
            </span>
          )}
        </div>
      )}

      {/* Error Messages */}
      {(error || inputError) && (
        <p className="text-error-500 text-xs mt-1">{error || inputError}</p>
      )}

      {/* Helper Text */}
      <p className="text-gray-500 text-xs mt-1">
        {value.length} / {maxFeatures} features added
        {value.length < maxFeatures && ' - Press Enter after typing each feature'}
      </p>
    </div>
  )
}
