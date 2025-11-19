/**
 * CinematographyControls Component
 * Controls for the 6 cinematography dimensions per scene
 */

import React from 'react'
import { TypeAheadDropdown } from '../ui/TypeAheadDropdown'
import type { Cinematography } from '../../types'

interface CinematographyControlsProps {
  value: Cinematography
  onChange: (cinematography: Cinematography) => void
}

// Cinematography options
const CAMERA_ASPECTS = ['POV', 'near Birds Eye', 'satellite', 'follow']

const LIGHTING_OPTIONS = [
  'natural',
  'golden hour',
  'dramatic',
  'soft',
  'high contrast',
  'studio',
  'dim',
  'bright',
]

const MOOD_OPTIONS = [
  'energetic',
  'calm',
  'suspenseful',
  'playful',
  'professional',
  'intimate',
  'powerful',
]

const TRANSITION_OPTIONS = ['cut', 'fade', 'dissolve', 'wipe', 'slide']

const ENVIRONMENT_OPTIONS = [
  'bright',
  'dim',
  'foggy',
  'clear',
  'urban',
  'natural',
  'indoor',
  'outdoor',
]

const SETTING_OPTIONS = [
  'residential',
  'office',
  'beach',
  'park',
  'urban street',
  'cafe',
  'gym',
  'studio',
  'kitchen',
  'living room',
  'bedroom',
  'bathroom',
  'rooftop',
  'warehouse',
  'restaurant',
  'bar',
  'shopping mall',
  'airport',
  'train station',
  'countryside',
  'mountain',
  'forest',
  'desert',
  'lake',
  'river',
  'industrial',
  'futuristic',
  'vintage',
  'minimalist',
  'luxury',
]

export function CinematographyControls({ value, onChange }: CinematographyControlsProps) {
  const handleChange = (field: keyof Cinematography, newValue: string) => {
    onChange({
      ...value,
      [field]: newValue,
    })
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-3">Cinematography Style</h4>
        <p className="text-xs text-gray-600 mb-4">
          Configure the visual style and camera work for this scene
        </p>
      </div>

      {/* Camera Aspect - Radio Group */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Camera Angle
          <span className="text-red-500 ml-1">*</span>
        </label>
        <div className="grid grid-cols-2 gap-2">
          {CAMERA_ASPECTS.map((aspect) => (
            <button
              key={aspect}
              type="button"
              onClick={() => handleChange('camera_aspect', aspect)}
              className={`
                px-4 py-2 rounded-lg border text-sm font-medium transition-all
                ${
                  value.camera_aspect === aspect
                    ? 'bg-purple-600 text-white border-purple-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:border-purple-400'
                }
              `}
            >
              {aspect}
            </button>
          ))}
        </div>
      </div>

      {/* Lighting */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Lighting
          <span className="text-red-500 ml-1">*</span>
        </label>
        <select
          value={value.lighting}
          onChange={(e) => handleChange('lighting', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="">Select lighting</option>
          {LIGHTING_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      {/* Mood */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Mood
          <span className="text-red-500 ml-1">*</span>
        </label>
        <select
          value={value.mood}
          onChange={(e) => handleChange('mood', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="">Select mood</option>
          {MOOD_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      {/* Transition */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Transition to Next Scene
          <span className="text-red-500 ml-1">*</span>
        </label>
        <select
          value={value.transition}
          onChange={(e) => handleChange('transition', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="">Select transition</option>
          {TRANSITION_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      {/* Environment */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Environment
          <span className="text-red-500 ml-1">*</span>
        </label>
        <select
          value={value.environment}
          onChange={(e) => handleChange('environment', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="">Select environment</option>
          {ENVIRONMENT_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      {/* Setting - TypeAheadDropdown with 30+ options */}
      <TypeAheadDropdown
        options={SETTING_OPTIONS}
        value={value.setting}
        onChange={(newValue) => handleChange('setting', newValue)}
        placeholder="Select or type custom setting"
        label="Physical Setting"
        allowCustom={true}
        required={true}
      />
    </div>
  )
}
