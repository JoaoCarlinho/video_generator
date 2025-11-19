/**
 * SegmentedControl Component
 * iOS-style segmented control for selecting between multiple options
 */

import React from 'react'

export interface SegmentOption<T = string> {
  value: T
  label: string
  description?: string
}

interface SegmentedControlProps<T = string> {
  options: SegmentOption<T>[]
  value: T
  onChange: (value: T) => void
  label?: string
  className?: string
}

export function SegmentedControl<T = string>({
  options,
  value,
  onChange,
  label,
  className = '',
}: SegmentedControlProps<T>) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      )}

      <div className="inline-flex rounded-lg border border-gray-300 bg-gray-50 p-1">
        {options.map((option, index) => {
          const isSelected = option.value === value
          return (
            <button
              key={index}
              type="button"
              onClick={() => onChange(option.value)}
              className={`
                px-4 py-2 rounded-md text-sm font-medium transition-all duration-200
                ${
                  isSelected
                    ? 'bg-white text-purple-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }
              `}
            >
              <div className="flex flex-col items-center">
                <span>{option.label}</span>
                {option.description && (
                  <span className="text-xs text-gray-500 mt-0.5">{option.description}</span>
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
