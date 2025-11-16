import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

export type AspectRatio = '9:16' | '16:9' | '1:1'

export interface AspectRatioSelectorProps {
  selectedRatios: AspectRatio[]
  onChange: (ratios: AspectRatio[]) => void
  required?: boolean
}

interface RatioOption {
  value: AspectRatio
  label: string
  icon: string
  description: string
  resolution: string
}

const ratioOptions: RatioOption[] = [
  {
    value: '9:16',
    label: 'Vertical',
    icon: '📱',
    description: 'Instagram Reels, TikTok, Stories',
    resolution: '1080×1920',
  },
  {
    value: '16:9',
    label: 'Horizontal',
    icon: '🖥️',
    description: 'YouTube, Facebook, LinkedIn',
    resolution: '1920×1080',
  },
  {
    value: '1:1',
    label: 'Square',
    icon: '⬜',
    description: 'Instagram Feed, Facebook Posts',
    resolution: '1080×1080',
  },
]

export const AspectRatioSelector = ({
  selectedRatios,
  onChange,
  required = true,
}: AspectRatioSelectorProps) => {
  const [error, setError] = useState<string>('')

  useEffect(() => {
    // Validate that at least one is selected if required
    if (required && selectedRatios.length === 0) {
      setError('Please select at least one aspect ratio')
    } else {
      setError('')
    }
  }, [selectedRatios, required])

  const handleToggle = (ratio: AspectRatio) => {
    const isSelected = selectedRatios.includes(ratio)

    if (isSelected) {
      // Prevent deselecting if it's the last one and required
      if (required && selectedRatios.length === 1) {
        setError('Please select at least one aspect ratio')
        return
      }
      onChange(selectedRatios.filter((r) => r !== ratio))
    } else {
      onChange([...selectedRatios, ratio])
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-slate-300">
          Output Formats {required && <span className="text-red-400">*</span>}
        </label>
        {selectedRatios.length > 0 && (
          <span className="text-xs text-slate-500">
            {selectedRatios.length} selected
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {ratioOptions.map((option) => {
          const isSelected = selectedRatios.includes(option.value)

          return (
            <motion.button
              key={option.value}
              type="button"
              onClick={() => handleToggle(option.value)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`p-4 rounded-lg border-2 transition-all text-left ${
                isSelected
                  ? 'border-indigo-500 bg-indigo-500/20'
                  : 'border-slate-700 bg-slate-800/30 hover:border-slate-600'
              }`}
              aria-label={`${isSelected ? 'Deselect' : 'Select'} ${option.label} format`}
              aria-pressed={isSelected}
            >
              {/* Checkbox indicator */}
              <div className="flex items-start gap-3">
                <div
                  className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-500'
                      : 'border-slate-600 bg-slate-900'
                  }`}
                >
                  {isSelected && (
                    <svg
                      className="w-3 h-3 text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={3}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">{option.icon}</span>
                    <span
                      className={`font-semibold text-sm ${
                        isSelected ? 'text-indigo-200' : 'text-slate-300'
                      }`}
                    >
                      {option.label}
                    </span>
                  </div>

                  <p
                    className={`text-xs mb-1 ${
                      isSelected ? 'text-indigo-300' : 'text-slate-400'
                    }`}
                  >
                    {option.value}
                  </p>

                  <p className="text-xs text-slate-500 mb-1">
                    {option.description}
                  </p>

                  <p className="text-xs text-slate-600">{option.resolution}</p>
                </div>
              </div>
            </motion.button>
          )
        })}
      </div>

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

      {/* Helper Text */}
      <p className="text-xs text-slate-500">
        💡 Select all formats you need - videos will be generated for each aspect ratio
      </p>
    </div>
  )
}
