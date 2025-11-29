/**
 * CampaignCreation - Page for creating new marketing campaigns
 * Integrates campaign metadata, scene configuration, and auto-save
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, Save, AlertCircle } from 'lucide-react'
import { CampaignMetadataSection } from '../components/forms/CampaignMetadataSection'
import { SceneCountSelector } from '../components/forms/SceneCountSelector'
import { ScenePanel } from '../components/forms/ScenePanel'
import { DurationSelector } from '../components/forms/DurationSelector'
import { Button } from '../components/ui/Button'
import { useAutoSave } from '../hooks/useAutoSave'
import {
  useCreateCampaignMutation,
  useUpdateCampaignMutation,
  useGetCampaignByIdQuery,
} from '../store/api'
import { api } from '../services/api'
import axios from 'axios'
import type { SceneConfig, Cinematography, Campaign } from '../types'

// Type for creating campaigns (omits auto-generated fields)
type CreateCampaignData = Omit<Campaign, 'id' | 'product_id' | 'display_name' | 'status' | 'created_at' | 'updated_at'>

// Default cinematography values
const DEFAULT_CINEMATOGRAPHY: Cinematography = {
  camera_aspect: 'POV',
  lighting: 'natural',
  mood: 'energetic',
  transition: 'fade',
  environment: 'bright',
  setting: 'residential',
}

// Create default scene
const createDefaultScene = (sceneNumber: number): SceneConfig => ({
  scene_number: sceneNumber,
  creative_vision: '',
  reference_images: ['', '', ''],
  cinematography: { ...DEFAULT_CINEMATOGRAPHY },
})

export function CampaignCreation() {
  const { brandId, productId, campaignId } = useParams<{
    brandId: string
    productId: string
    campaignId?: string
  }>()
  const navigate = useNavigate()
  const location = useLocation()

  const isEditMode = !!campaignId
  const { data: existingCampaign, isLoading: isLoadingCampaign } = useGetCampaignByIdQuery(
    campaignId || '',
    { skip: !isEditMode }
  )

  // RTK Query mutations
  const [createCampaign, { isLoading: isCreating }] = useCreateCampaignMutation()
  const [updateCampaign, { isLoading: isUpdating }] = useUpdateCampaignMutation()

  // Form state
  const [selectedProductId, setSelectedProductId] = useState(productId || '')
  const [campaignName, setCampaignName] = useState('')
  const [seasonalEvent, setSeasonalEvent] = useState('')
  const [year, setYear] = useState(new Date().getFullYear())
  const [duration, setDuration] = useState(30)
  const [sceneCount, setSceneCount] = useState(1)
  const [scenes, setScenes] = useState<SceneConfig[]>([createDefaultScene(1)])
  const [expandedSceneIndex, setExpandedSceneIndex] = useState(0)
  const [savedCampaignId, setSavedCampaignId] = useState<string | undefined>(campaignId)

  // UI state
  const [errors, setErrors] = useState<Record<string, any>>({})
  const [globalError, setGlobalError] = useState<string | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // Load existing campaign data
  useEffect(() => {
    if (existingCampaign && isEditMode) {
      setSelectedProductId(existingCampaign.product_id)
      setCampaignName(existingCampaign.name)
      setSeasonalEvent(existingCampaign.seasonal_event)
      setYear(existingCampaign.year)
      setDuration(existingCampaign.duration)
      setScenes(existingCampaign.scene_configs as SceneConfig[])
      setSceneCount(existingCampaign.scene_configs.length)
    }
  }, [existingCampaign, isEditMode])

  // Track unsaved changes
  useEffect(() => {
    setHasUnsavedChanges(true)
  }, [campaignName, seasonalEvent, year, duration, sceneCount, scenes, selectedProductId])

  // Handle scene count change
  const handleSceneCountChange = (newCount: number) => {
    setSceneCount(newCount)

    if (newCount > scenes.length) {
      // Add new scenes
      const newScenes = [...scenes]
      for (let i = scenes.length; i < newCount; i++) {
        newScenes.push(createDefaultScene(i + 1))
      }
      setScenes(newScenes)
    } else if (newCount < scenes.length) {
      // Remove scenes
      setScenes(scenes.slice(0, newCount))
      // Adjust expanded index if necessary
      if (expandedSceneIndex >= newCount) {
        setExpandedSceneIndex(newCount - 1)
      }
    }
  }

  // Handle scene change
  const handleSceneChange = (index: number, scene: SceneConfig) => {
    const newScenes = [...scenes]
    newScenes[index] = scene
    setScenes(newScenes)
  }

  // Upload file to S3
  const uploadFileToS3 = async (file: File): Promise<string> => {
    try {
      // Request presigned URL from backend
      const presignedResponse = await api.post('/api/storage/presigned-url', {
        filename: file.name,
        content_type: file.type,
        asset_type: 'product',  // Reference images for campaigns
      })

      const { upload_url, file_url } = presignedResponse.data

      // Upload file directly to S3
      await axios.put(upload_url, file, {
        headers: {
          'Content-Type': file.type,
        },
      })

      // Return the public file URL
      return file_url
    } catch (error) {
      console.error('S3 upload error:', error)
      throw new Error(`Failed to upload ${file.name}`)
    }
  }

  // Handle image upload for scene
  const handleImageUpload = async (
    file: File,
    sceneNumber: number,
    imageIndex: number
  ): Promise<string> => {
    return await uploadFileToS3(file)
  }

  // Validate form
  const validateForm = (): boolean => {
    const newErrors: Record<string, any> = {}

    if (!selectedProductId) {
      newErrors.productId = 'Product is required'
    }
    if (!campaignName || campaignName.trim().length === 0) {
      newErrors.name = 'Campaign name is required'
    }
    if (!seasonalEvent || seasonalEvent.trim().length === 0) {
      newErrors.seasonal_event = 'Seasonal event is required'
    }
    if (!year) {
      newErrors.year = 'Year is required'
    }

    // Validate scenes
    scenes.forEach((scene, index) => {
      const sceneErrors: Record<string, string> = {}

      if (scene.creative_vision.length < 20) {
        sceneErrors.creative_vision = 'Creative vision must be at least 20 characters'
      }

      const filledImages = scene.reference_images.filter((url) => url !== '')
      if (filledImages.length !== 3) {
        sceneErrors.reference_images = 'All 3 reference images are required'
      }

      if (!scene.cinematography.camera_aspect) {
        sceneErrors.cinematography = 'Camera aspect is required'
      }

      if (Object.keys(sceneErrors).length > 0) {
        newErrors[`scene_${index}`] = sceneErrors
      }
    })

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Auto-save handler
  const handleAutoSave = useCallback(async () => {
    if (!selectedProductId || !campaignName || !seasonalEvent || !year) {
      return // Don't auto-save if required fields are missing
    }

    // Campaign data for creation/update
    const campaignData: CreateCampaignData = {
      name: campaignName,
      seasonal_event: seasonalEvent,
      year,
      duration,
      scene_configs: scenes,
    }

    try {
      if (savedCampaignId) {
        // Update existing campaign
        await updateCampaign({
          campaignId: savedCampaignId,
          data: campaignData as any,
        }).unwrap()
      } else {
        // Create new campaign
        const result = await createCampaign({
          productId: selectedProductId,
          data: campaignData as any,
        }).unwrap()
        setSavedCampaignId(result.id)
      }
      setHasUnsavedChanges(false)
    } catch (error) {
      console.error('Auto-save failed:', error)
      throw error
    }
  }, [
    selectedProductId,
    campaignName,
    seasonalEvent,
    year,
    duration,
    scenes,
    savedCampaignId,
    createCampaign,
    updateCampaign,
  ])

  // Auto-save hook
  const { isSaving, lastSaved, error: autoSaveError, saveNow } = useAutoSave({
    data: { campaignName, seasonalEvent, year, duration, scenes },
    onSave: handleAutoSave,
    debounceMs: 30000,
    enabled: !isCreating && !isUpdating,
  })

  // Handle manual save
  const handleManualSave = async () => {
    await saveNow()
  }

  // Handle generate video
  const handleGenerateVideo = async () => {
    if (!validateForm()) {
      setGlobalError('Please fix all errors before generating video')
      return
    }

    // Save first if there are unsaved changes
    if (hasUnsavedChanges) {
      await handleManualSave()
    }

    // Navigate to generation page or trigger generation
    if (savedCampaignId) {
      // TODO: Navigate to generation page or trigger generation
      console.log('Generate video for campaign:', savedCampaignId)
      if (window.showToast) {
        window.showToast('Campaign saved! Video generation coming soon...', 'success')
      }
    }
  }

  // Navigation guard
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ''
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])

  if (isLoadingCampaign) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate(`/brands/${brandId}/products`)}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Products
          </button>

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {isEditMode ? 'Edit Campaign' : 'Create New Campaign'}
              </h1>
              <p className="text-gray-600 mt-1">
                Configure your campaign metadata, scenes, and cinematography
              </p>
            </div>

            {/* Auto-save status */}
            <div className="flex items-center gap-3">
              {isSaving && (
                <span className="text-sm text-gray-600 flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-600"></div>
                  Saving...
                </span>
              )}
              {lastSaved && !isSaving && (
                <span className="text-sm text-green-600">
                  Saved {new Date(lastSaved).toLocaleTimeString()}
                </span>
              )}
              {autoSaveError && (
                <span className="text-sm text-red-600 flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  Save failed
                </span>
              )}
              <Button
                onClick={handleManualSave}
                variant="outline"
                size="sm"
                disabled={isSaving || !hasUnsavedChanges}
              >
                <Save className="w-4 h-4 mr-2" />
                Save Now
              </Button>
            </div>
          </div>
        </div>

        {/* Global Error */}
        {globalError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {globalError}
          </div>
        )}

        {/* Form */}
        <div className="space-y-8">
          {/* Campaign Metadata Section */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <CampaignMetadataSection
              brandId={brandId || ''}
              productId={selectedProductId}
              campaignName={campaignName}
              seasonalEvent={seasonalEvent}
              year={year}
              onProductIdChange={setSelectedProductId}
              onCampaignNameChange={setCampaignName}
              onSeasonalEventChange={setSeasonalEvent}
              onYearChange={setYear}
              errors={errors}
            />
          </div>

          {/* Duration Selector */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <DurationSelector value={duration} onChange={setDuration} />
          </div>

          {/* Scene Configuration */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Scene Configuration</h2>
              <p className="text-sm text-gray-600">
                Configure visual scenes for your campaign video. Each scene will be sequenced in
                order.
              </p>
            </div>

            {/* Scene Count Selector */}
            <SceneCountSelector count={sceneCount} onChange={handleSceneCountChange} />

            {/* Scene Panels */}
            <div className="mt-6 space-y-4">
              {scenes.map((scene, index) => (
                <ScenePanel
                  key={index}
                  sceneNumber={scene.scene_number}
                  scene={scene}
                  onChange={(updatedScene) => handleSceneChange(index, updatedScene)}
                  onImageUpload={handleImageUpload}
                  isExpanded={expandedSceneIndex === index}
                  onToggle={() =>
                    setExpandedSceneIndex(expandedSceneIndex === index ? -1 : index)
                  }
                  errors={errors[`scene_${index}`]}
                />
              ))}
            </div>
          </div>

          {/* Generate Button */}
          <div className="flex justify-end gap-4">
            <Button variant="outline" onClick={() => navigate(`/brands/${brandId}/products`)}>
              Cancel
            </Button>
            <Button
              onClick={handleGenerateVideo}
              disabled={isCreating || isUpdating || isSaving}
              className="min-w-[200px]"
            >
              {isCreating || isUpdating || isSaving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Saving...
                </>
              ) : (
                'Generate Video'
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
