/**
 * ScenePanel Component
 * Accordion panel for configuring individual scenes
 */

import React, { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { ReferenceImageUpload } from './ReferenceImageUpload'
import { CinematographyControls } from './CinematographyControls'
import type { SceneConfig, Cinematography } from '../../types'

interface ScenePanelProps {
  sceneNumber: number
  scene: SceneConfig
  onChange: (scene: SceneConfig) => void
  onImageUpload: (file: File, sceneNumber: number, imageIndex: number) => Promise<string>
  isExpanded: boolean
  onToggle: () => void
  errors?: {
    creative_vision?: string
    reference_images?: string
    cinematography?: Record<string, string>
  }
}

// Default cinematography values
const DEFAULT_CINEMATOGRAPHY: Cinematography = {
  camera_aspect: 'POV',
  lighting: 'natural',
  mood: 'energetic',
  transition: 'fade',
  environment: 'bright',
  setting: 'residential',
}

export function ScenePanel({
  sceneNumber,
  scene,
  onChange,
  onImageUpload,
  isExpanded,
  onToggle,
  errors = {},
}: ScenePanelProps) {
  const MAX_VISION_LENGTH = 2000
  const visionLength = scene.creative_vision.length

  // Check if scene is complete
  const isComplete =
    scene.creative_vision.length >= 20 &&
    scene.reference_images.length === 3 &&
    scene.reference_images.every((url) => url !== '') &&
    scene.cinematography.camera_aspect &&
    scene.cinematography.lighting &&
    scene.cinematography.mood &&
    scene.cinematography.transition &&
    scene.cinematography.environment &&
    scene.cinematography.setting

  const handleCreativeVisionChange = (value: string) => {
    if (value.length <= MAX_VISION_LENGTH) {
      onChange({
        ...scene,
        creative_vision: value,
      })
    }
  }

  const handleImagesChange = (images: string[]) => {
    onChange({
      ...scene,
      reference_images: images,
    })
  }

  const handleCinematographyChange = (cinematography: Cinematography) => {
    onChange({
      ...scene,
      cinematography,
    })
  }

  const handleImageUpload = async (file: File, imageIndex: number) => {
    return await onImageUpload(file, sceneNumber, imageIndex)
  }

  return (
    <div className="border border-gray-300 rounded-lg overflow-hidden">
      {/* Accordion Header */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-gray-900">Scene {sceneNumber}</span>
          {isComplete && (
            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded">
              Complete
            </span>
          )}
          {!isComplete && isExpanded && (
            <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs font-medium rounded">
              In Progress
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-gray-600" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-600" />
        )}
      </button>

      {/* Accordion Content */}
      {isExpanded && (
        <div className="p-6 space-y-6 bg-white">
          {/* Creative Vision */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Creative Vision
              <span className="text-red-500 ml-1">*</span>
            </label>
            <p className="text-xs text-gray-600 mb-2">
              Describe the visual narrative, action, and emotional tone for this scene (minimum 20
              characters)
            </p>
            <textarea
              value={scene.creative_vision}
              onChange={(e) => handleCreativeVisionChange(e.target.value)}
              placeholder="e.g., Energetic professional in modern kitchen preparing morning smoothie. Natural lighting streams through large windows. Camera follows subject's fluid movements as they blend ingredients. Product prominently featured on marble countertop..."
              rows={6}
              className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 resize-vertical ${
                errors.creative_vision ? 'border-red-500' : 'border-gray-300'
              }`}
            />
            <div className="flex items-center justify-between mt-1">
              <div>
                {errors.creative_vision && (
                  <p className="text-sm text-red-600">{errors.creative_vision}</p>
                )}
              </div>
              <p
                className={`text-xs ${
                  visionLength < 20
                    ? 'text-red-600'
                    : visionLength > MAX_VISION_LENGTH * 0.9
                    ? 'text-yellow-600'
                    : 'text-gray-500'
                }`}
              >
                {visionLength} / {MAX_VISION_LENGTH}
              </p>
            </div>
          </div>

          {/* Reference Images */}
          <ReferenceImageUpload
            images={scene.reference_images}
            onImagesChange={handleImagesChange}
            onFileSelected={handleImageUpload}
          />
          {errors.reference_images && (
            <p className="text-sm text-red-600">{errors.reference_images}</p>
          )}

          {/* Cinematography Controls */}
          <CinematographyControls
            value={scene.cinematography}
            onChange={handleCinematographyChange}
          />
        </div>
      )}
    </div>
  )
}
