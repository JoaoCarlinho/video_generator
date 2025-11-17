import React from 'react'
import { Input } from '../ui/Input'
import { AspectRatioSelector, type AspectRatio } from '../ui/AspectRatioSelector'
import { cn } from '../../utils/cn'

export interface CreativeVisionData {
  creative_prompt: string
  target_audience: string
  target_duration: number
  aspect_ratios: AspectRatio[]
}

export interface CreativeVisionTabProps {
  data: CreativeVisionData
  onChange: (data: CreativeVisionData) => void
}

export const CreativeVisionTab: React.FC<CreativeVisionTabProps> = ({ data, onChange }) => {
  const handleChange = (field: keyof CreativeVisionData, value: any) => {
    onChange({ ...data, [field]: value })
  }

  const isPromptValid = data.creative_prompt.trim().length >= 20
  const isAspectRatioValid = data.aspect_ratios.length > 0

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Instructions */}
      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold text-gray-900 mb-2">Describe your creative vision</h3>
        <p className="text-gray-600">
          Help our AI understand the story you want to tell and how it should look and feel.
        </p>
      </div>

      {/* Creative Vision */}
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Creative Vision
          <span className="text-error-500 ml-1">*</span>
        </label>
        <textarea
          placeholder="Describe your vision for the video. How should it look and feel? What story should it tell? Example: Create an energetic video that starts with a problem (tired skin), showcases our serum transforming skin in 7 days, and ends with confident customers. Use bright, clean aesthetics with dynamic camera movements."
          value={data.creative_prompt}
          onChange={(e) => handleChange('creative_prompt', e.target.value)}
          rows={6}
          className={cn(
            'w-full px-4 py-3 bg-white border rounded-lg',
            'text-gray-900 placeholder:text-gray-400',
            'focus:outline-none focus:ring-2 transition-all duration-150 resize-none',
            isPromptValid
              ? 'border-gray-200 focus:border-primary-500 focus:ring-primary-500/20'
              : 'border-gray-200 focus:border-primary-500 focus:ring-primary-500/20'
          )}
        />
        <div className="flex justify-between items-center mt-2">
          <p className="text-xs text-gray-500">
            💡 Be specific about mood, pacing, and key moments. The AI will bring your vision to
            life.
          </p>
          <p
            className={cn(
              'text-xs font-medium',
              isPromptValid ? 'text-success-600' : 'text-gray-400'
            )}
          >
            {data.creative_prompt.length >= 20 ? '✓' : ''} {data.creative_prompt.length} characters
          </p>
        </div>
        {!isPromptValid && data.creative_prompt.length > 0 && (
          <p className="text-xs text-warning-500 mt-1">
            Please write at least 20 characters to help us understand your vision
          </p>
        )}
      </div>

      {/* Target Audience */}
      <Input
        label="Target Audience"
        placeholder="e.g., Women 30-55 interested in natural beauty"
        value={data.target_audience}
        onChange={(e) => handleChange('target_audience', e.target.value)}
        helpText="Who is this video for? (Optional but helps with targeting)"
      />

      {/* Target Duration */}
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-3">
          Target Video Duration (seconds)
        </label>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="15"
            max="120"
            step="5"
            value={data.target_duration}
            onChange={(e) => handleChange('target_duration', parseInt(e.target.value))}
            className="flex-1 h-2 bg-gray-200 rounded-lg accent-primary-500 cursor-pointer"
          />
          <div className="w-20 text-center">
            <span className="text-2xl font-bold text-primary-500">{data.target_duration}s</span>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          ⏱️ The AI will pace scenes naturally around this target (±20% is OK)
        </p>
      </div>

      {/* Aspect Ratio Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-3">
          Output Formats
          <span className="text-error-500 ml-1">*</span>
        </label>
        <AspectRatioSelector
          selectedRatios={data.aspect_ratios}
          onChange={(ratios) => handleChange('aspect_ratios', ratios)}
          required={true}
        />
        {!isAspectRatioValid && (
          <p className="text-xs text-error-500 mt-2">Please select at least one aspect ratio</p>
        )}
      </div>

      {/* Summary box */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">📋 Your Video Plan</h4>
        <div className="space-y-1 text-sm text-gray-600">
          <p>
            • <span className="font-medium">Duration:</span> {data.target_duration} seconds
          </p>
          <p>
            • <span className="font-medium">Formats:</span>{' '}
            {data.aspect_ratios.length > 0 ? (
              data.aspect_ratios
                .map((ar) =>
                  ar === '9:16' ? '📱 Vertical' : ar === '1:1' ? '⬜ Square' : '🖥️ Horizontal'
                )
                .join(', ')
            ) : (
              <span className="text-gray-400">None selected</span>
            )}
          </p>
          {data.target_audience && (
            <p>
              • <span className="font-medium">Audience:</span> {data.target_audience}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
