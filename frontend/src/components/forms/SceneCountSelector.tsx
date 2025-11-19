/**
 * SceneCountSelector Component
 * Selector for number of scenes (1-10)
 */

import React from 'react'

interface SceneCountSelectorProps {
  count: number
  onChange: (count: number) => void
  className?: string
}

export function SceneCountSelector({ count, onChange, className = '' }: SceneCountSelectorProps) {
  const sceneOptions = Array.from({ length: 10 }, (_, i) => i + 1)

  return (
    <div className={className}>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Number of Scenes
        <span className="text-red-500 ml-1">*</span>
      </label>
      <p className="text-xs text-gray-600 mb-3">
        Configure 1-10 scenes for your campaign. Each scene will be sequenced in order.
      </p>

      <div className="grid grid-cols-5 gap-2">
        {sceneOptions.map((num) => (
          <button
            key={num}
            type="button"
            onClick={() => onChange(num)}
            className={`
              px-4 py-2 rounded-lg border text-sm font-medium transition-all
              ${
                count === num
                  ? 'bg-purple-600 text-white border-purple-600 shadow-md'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-purple-400 hover:bg-purple-50'
              }
            `}
          >
            {num}
          </button>
        ))}
      </div>
    </div>
  )
}
