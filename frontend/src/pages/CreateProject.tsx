import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Container, Header } from '@/components/layout'
import { Button, Card, CardContent, Modal } from '@/components/ui'
import { TabWizard, TabPanel, FormNavigation } from '@/components/ui'
import { BrandInfoTab } from '@/components/forms/BrandInfoTab'
import { CreativeVisionTab } from '@/components/forms/CreativeVisionTab'
import { AssetsTab } from '@/components/forms/AssetsTab'
import { useProjects } from '@/hooks/useProjects'
import { Zap } from 'lucide-react'
import type { AspectRatio } from '@/components/ui/AspectRatioSelector'

// Get API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Tab configuration
const TABS = [
  { id: 'brand-info', label: 'Brand Info' },
  { id: 'creative-vision', label: 'Creative Vision' },
  { id: 'assets', label: 'Assets' },
]

interface FormData {
  // Brand Info
  title: string
  brand_name: string
  brand_description: string

  // Creative Vision
  creative_prompt: string
  target_audience: string
  target_duration: number
  aspect_ratios: AspectRatio[]

  // Assets
  product_images: File[]
  logo_images: File[]
  guidelines_file: File | null
}

const INITIAL_FORM_DATA: FormData = {
  title: '',
  brand_name: '',
  brand_description: '',
  creative_prompt: '',
  target_audience: '',
  target_duration: 30,
  aspect_ratios: ['16:9'],
  product_images: [],
  logo_images: [],
  guidelines_file: null,
}

export const CreateProject = () => {
  const navigate = useNavigate()
  const { createProject, loading, error } = useProjects()

  const [currentTab, setCurrentTab] = useState(0)
  const [completedTabs, setCompletedTabs] = useState<number[]>([])
  const [formData, setFormData] = useState<FormData>(INITIAL_FORM_DATA)
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [autoGenerate, setAutoGenerate] = useState(true)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // Load draft from localStorage on mount
  useEffect(() => {
    const savedDraft = localStorage.getItem('draft-project')
    if (savedDraft) {
      try {
        const parsed = JSON.parse(savedDraft)
        setFormData({ ...INITIAL_FORM_DATA, ...parsed })
      } catch (e) {
        console.error('Failed to parse draft:', e)
      }
    }
  }, [])

  // Save draft to localStorage on change
  useEffect(() => {
    localStorage.setItem('draft-project', JSON.stringify(formData))
  }, [formData])

  // Validation functions
  const isTab1Valid = () => {
    return formData.title.trim().length >= 3 && formData.brand_name.trim().length >= 2
  }

  const isTab2Valid = () => {
    return formData.creative_prompt.trim().length >= 20 && formData.aspect_ratios.length > 0
  }

  const canProceedToNext = () => {
    if (currentTab === 0) return isTab1Valid()
    if (currentTab === 1) return isTab2Valid()
    return true // Tab 3 has no required fields
  }

  // Navigation handlers
  const handleNext = () => {
    if (canProceedToNext()) {
      if (!completedTabs.includes(currentTab)) {
        setCompletedTabs([...completedTabs, currentTab])
      }

      if (currentTab < TABS.length - 1) {
        setCurrentTab(currentTab + 1)
      } else {
        // Last tab - show confirmation
        setShowConfirmation(true)
      }
    }
  }

  const handleBack = () => {
    if (currentTab > 0) {
      setCurrentTab(currentTab - 1)
    }
  }

  const handleTabChange = (index: number) => {
    setCurrentTab(index)
  }

  const handleSaveDraft = () => {
    // Already saved via useEffect, just notify user
    alert('Draft saved! You can come back anytime.')
    navigate('/dashboard')
  }

  // File upload helper
  const uploadFileToBackend = async (
    file: File,
    assetType: 'logo' | 'product' | 'guidelines'
  ): Promise<string | null> => {
    try {
      const uploadFormData = new FormData()
      uploadFormData.append('file', file)
      uploadFormData.append('asset_type', assetType)

      // Get auth token from localStorage
      const token = localStorage.getItem('authToken')
      const headers: HeadersInit = {}
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const uploadResponse = await fetch(`${API_BASE_URL}/api/upload-asset`, {
        method: 'POST',
        body: uploadFormData,
        headers,
      })

      if (!uploadResponse.ok) {
        throw new Error(`Failed to upload file: ${uploadResponse.statusText}`)
      }

      const { file_path } = await uploadResponse.json()
      return file_path
    } catch (error) {
      console.error(`❌ Failed to upload ${assetType}:`, error)
      return null
    }
  }

  // Submit handler
  const handleConfirmCreate = async () => {
    setShowConfirmation(false)
    setSubmitError(null)

    try {
      // Upload assets in parallel
      const uploadPromises: Promise<any>[] = []
      let uploadedProductUrls: string[] = []
      let uploadedLogoUrls: string[] = []
      let uploadedGuidelinesUrl: string | null = null

      // Upload product images
      if (formData.product_images.length > 0) {
        formData.product_images.forEach((file) => {
          uploadPromises.push(
            uploadFileToBackend(file, 'product').then((url) => {
              if (url) uploadedProductUrls.push(url)
            })
          )
        })
      }

      // Upload logo images
      if (formData.logo_images.length > 0) {
        formData.logo_images.forEach((file) => {
          uploadPromises.push(
            uploadFileToBackend(file, 'logo').then((url) => {
              if (url) uploadedLogoUrls.push(url)
            })
          )
        })
      }

      // Upload guidelines
      if (formData.guidelines_file) {
        uploadPromises.push(
          uploadFileToBackend(formData.guidelines_file, 'guidelines').then((url) => {
            uploadedGuidelinesUrl = url
          })
        )
      }

      // Wait for all uploads
      await Promise.all(uploadPromises)

      // Create project
      const newProject = await createProject({
        title: formData.title,
        creative_prompt: formData.creative_prompt,
        brand_name: formData.brand_name,
        brand_description: formData.brand_description || undefined,
        target_audience: formData.target_audience || undefined,
        target_duration: formData.target_duration,
        aspect_ratio: formData.aspect_ratios[0], // Primary aspect ratio
        outputFormats: formData.aspect_ratios,
        product_image_url: uploadedProductUrls[0] || undefined,
        productImages: uploadedProductUrls.length > 0 ? uploadedProductUrls : undefined,
        logo_url: uploadedLogoUrls[0] || undefined,
        guidelines_url: uploadedGuidelinesUrl || undefined,
      } as any)

      // Clear draft
      localStorage.removeItem('draft-project')

      // Navigate
      if (autoGenerate) {
        navigate(`/projects/${newProject.id}/progress`)
      } else {
        navigate('/dashboard')
      }
    } catch (err) {
      console.error('❌ Error creating project:', err)
      const message = err instanceof Error ? err.message : 'Failed to create project'
      setSubmitError(message)
      setShowConfirmation(true)
    }
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 via-white to-gray-50 flex flex-col">
      <Header logo="GenAds" title="Create Project" />

      <div className="flex-1">
        <Container size="lg" className="py-12">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-8"
          >
            {/* Title */}
            <motion.div variants={itemVariants} className="text-center">
              <h2 className="text-3xl font-bold text-gray-900">Create New Project</h2>
              <p className="text-gray-600 mt-2">
                Follow the steps below to create your AI-generated ad video
              </p>
            </motion.div>

            {/* Tab Wizard */}
            <motion.div variants={itemVariants}>
              <Card>
                <CardContent className="p-8">
                  <TabWizard
                    tabs={TABS}
                    currentTab={currentTab}
                    onTabChange={handleTabChange}
                    completedTabs={completedTabs}
                  />

                  {/* Tab Content */}
                  <div className="mt-8">
                    <TabPanel isActive={currentTab === 0} tabId="brand-info">
                      <BrandInfoTab
                        data={{
                          title: formData.title,
                          brand_name: formData.brand_name,
                          brand_description: formData.brand_description,
                        }}
                        onChange={(data) =>
                          setFormData((prev) => ({ ...prev, ...data }))
                        }
                      />
                    </TabPanel>

                    <TabPanel isActive={currentTab === 1} tabId="creative-vision">
                      <CreativeVisionTab
                        data={{
                          creative_prompt: formData.creative_prompt,
                          target_audience: formData.target_audience,
                          target_duration: formData.target_duration,
                          aspect_ratios: formData.aspect_ratios,
                        }}
                        onChange={(data) =>
                          setFormData((prev) => ({ ...prev, ...data }))
                        }
                      />
                    </TabPanel>

                    <TabPanel isActive={currentTab === 2} tabId="assets">
                      <AssetsTab
                        data={{
                          product_images: formData.product_images,
                          logo_images: formData.logo_images,
                          guidelines_file: formData.guidelines_file,
                        }}
                        onChange={(data) =>
                          setFormData((prev) => ({ ...prev, ...data }))
                        }
                      />
                    </TabPanel>
                  </div>

                  {/* Navigation */}
                  <FormNavigation
                    onBack={currentTab > 0 ? handleBack : undefined}
                    onNext={handleNext}
                    onSaveDraft={handleSaveDraft}
                    canProceed={canProceedToNext()}
                    backLabel={currentTab > 0 ? '← Back' : undefined}
                    nextLabel={
                      currentTab === TABS.length - 1 ? 'Review & Create →' : 'Continue →'
                    }
                    isLoading={loading}
                  />
                </CardContent>
              </Card>
            </motion.div>

            {/* Info Box */}
            <motion.div variants={itemVariants}>
              <div className="p-4 bg-primary-500/10 border border-primary-500/20 rounded-lg">
                <p className="text-primary-600 text-sm">
                  💡 <strong>Pro Tip:</strong> Your progress is automatically saved. You can come
                  back anytime to continue where you left off.
                </p>
              </div>
            </motion.div>
          </motion.div>
        </Container>
      </div>

      {/* Confirmation Modal */}
      <Modal
        isOpen={showConfirmation}
        onClose={() => setShowConfirmation(false)}
        title="Review Your Project"
        description="Confirm the details before creating your project"
        size="lg"
      >
        <div className="space-y-6">
          {/* Error Message */}
          {submitError && (
            <div className="p-4 bg-error-500/10 border border-error-500/50 rounded-lg text-error-600 text-sm">
              {submitError}
            </div>
          )}

          {/* Project Details */}
          <div className="space-y-4 bg-gray-50 p-4 rounded-lg">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase">
                  Project Title
                </label>
                <p className="text-gray-900 mt-1">{formData.title}</p>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase">Brand Name</label>
                <p className="text-gray-900 mt-1">{formData.brand_name}</p>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-500 uppercase">
                Creative Vision
              </label>
              <p className="text-gray-900 mt-1 text-sm">{formData.creative_prompt}</p>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase">Duration</label>
                <p className="text-gray-900 mt-1">{formData.target_duration}s</p>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase">
                  Output Formats
                </label>
                <p className="text-gray-900 mt-1 text-sm">
                  {formData.aspect_ratios
                    .map((ar) =>
                      ar === '9:16' ? '📱 Vertical' : ar === '1:1' ? '⬜ Square' : '🖥️ Horizontal'
                    )
                    .join(', ')}
                </p>
              </div>
            </div>

            {/* Assets */}
            {(formData.product_images.length > 0 ||
              formData.logo_images.length > 0 ||
              formData.guidelines_file) && (
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase mb-2 block">
                  Uploaded Assets
                </label>
                <div className="flex flex-wrap gap-2">
                  {formData.product_images.length > 0 && (
                    <span className="px-3 py-1 bg-primary-500/10 text-primary-600 rounded-full text-xs">
                      ✓ {formData.product_images.length} Product Image
                      {formData.product_images.length > 1 ? 's' : ''}
                    </span>
                  )}
                  {formData.logo_images.length > 0 && (
                    <span className="px-3 py-1 bg-secondary-500/10 text-secondary-600 rounded-full text-xs">
                      ✓ {formData.logo_images.length} Logo{formData.logo_images.length > 1 ? 's' : ''}
                    </span>
                  )}
                  {formData.guidelines_file && (
                    <span className="px-3 py-1 bg-success-500/10 text-success-600 rounded-full text-xs">
                      ✓ Brand Guidelines
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Cost Estimate */}
          <div className="bg-success-500/10 border border-success-500/20 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-success-600" />
              <span className="text-xs font-semibold text-success-600 uppercase">
                Estimated Cost
              </span>
            </div>
            <p className="text-2xl font-bold text-success-600">$0.19 - $0.43</p>
            <p className="text-xs text-success-700 mt-1">Final cost may vary based on complexity</p>
          </div>

          {/* Auto-Generate Toggle */}
          <div className="flex items-center gap-3 p-3 bg-primary-500/10 border border-primary-500/20 rounded-lg">
            <input
              type="checkbox"
              id="autoGenerate"
              checked={autoGenerate}
              onChange={(e) => setAutoGenerate(e.target.checked)}
              className="w-4 h-4 rounded accent-primary-500 cursor-pointer"
            />
            <label htmlFor="autoGenerate" className="flex-1 cursor-pointer">
              <p className="text-sm font-medium text-gray-900">Start generation immediately</p>
              <p className="text-xs text-gray-600">
                {autoGenerate
                  ? 'You will be taken to the progress page'
                  : 'Project will be saved as draft'}
              </p>
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4 border-t border-gray-200">
            <Button
              type="button"
              variant="outline"
              fullWidth
              onClick={() => setShowConfirmation(false)}
              disabled={loading}
            >
              Edit
            </Button>
            <Button
              type="button"
              variant="default"
              fullWidth
              onClick={handleConfirmCreate}
              disabled={loading}
              isLoading={loading}
            >
              {loading ? 'Creating...' : 'Create Project'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
