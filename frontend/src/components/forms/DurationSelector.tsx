/**
 * DurationSelector Component
 * Selector for video duration with TikTok optimization indicator
 */

import React from 'react'
import { SegmentedControl } from '../ui/SegmentedControl'
import type { SegmentOption } from '../ui/SegmentedControl'

interface DurationSelectorProps {
  value: number
  onChange: (duration: number) => void
  className?: string
}

const DURATION_OPTIONS: SegmentOption<number>[] = [
  {
    value: 15,
    label: '15s',
    description: 'TikTok optimized',
  },
  {
    value: 30,
    label: '30s',
    description: 'Standard',
  },
  {
    value: 45,
    label: '45s',
    description: 'Extended',
  },
  {
    value: 60,
    label: '60s',
    description: 'Full length',
  },
]

export function DurationSelector({ value, onChange, className = '' }: DurationSelectorProps) {
  return (
    <div className={className}>
      <SegmentedControl
        options={DURATION_OPTIONS}
        value={value}
        onChange={onChange}
        label="Video Duration"
      />

      {value === 15 && (
        <div className="mt-2 flex items-center gap-2 text-sm text-purple-600">
          <svg
            className="w-4 h-4"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <span>Optimized for TikTok and short-form content</span>
        </div>
      )}
    </div>
  )
}
