import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui'
import { StepIndicator } from '@/components/ui/StepIndicator'
import { StyleSelector } from '@/components/ui/StyleSelector'
import { useCreatives } from '@/hooks/useCreatives'
import { useReferenceImage } from '@/hooks/useReferenceImage'
import { useStyleSelector } from '@/hooks/useStyleSelector'
import { X, Sparkles, ArrowRight, ArrowLeft, FileText, Image as ImageIcon, Video, Palette, UploadCloud } from 'lucide-react'
import { Slider } from '@/components/ui/slider'

export const CreateCreative = () => {
  const navigate = useNavigate()
  const { campaignId } = useParams<{ campaignId: string }>()
  const { createCreative, loading, error } = useCreatives()
  const { uploadReferenceImage, isLoading: isUploadingReference } = useReferenceImage()
  const { styles, selectedStyle, setSelectedStyle, clearSelection, isLoading: isLoadingStyles } = useStyleSelector()

  // Validate campaignId is present
  if (!campaignId) {
    return (
      <div className="min-h-screen bg-gradient-hero flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">Campaign ID is required to create a creative</p>
          <Button onClick={() => navigate('/dashboard')}>
            Go to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState({
    title: '',
    brand_name: '',
    product_name: '',
    creative_prompt: '',
    target_audience: '',
    target_duration: 30,
    num_variations: 1 as 1 | 2 | 3,
    video_provider: 'replicate' as 'replicate' | 'ecs',
  })

  const [productImage, setProductImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string>('')
  const [logoImage, setLogoImage] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string>('')
  const [guidelinesFile, setGuidelinesFile] = useState<File | null>(null)
  const [referenceImage, setReferenceImage] = useState<File | null>(null)
  const [referencePreview, setReferencePreview] = useState<string>('')
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const steps = [
    { label: 'Creative Info', description: 'Basic details' },
    { label: 'Creative Vision', description: 'Style & settings' },
    { label: 'Assets', description: 'Upload files' },
  ]

  // File handlers
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>, type: 'product' | 'logo' | 'reference') => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > 10 * 1024 * 1024) {
      setSubmitError(`${type === 'logo' ? 'Logo' : type === 'reference' ? 'Reference image' : 'Image'} must be less than 10MB`)
      return
    }

    if (!file.type.startsWith('image/')) {
      setSubmitError('Please select an image file')
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const preview = e.target?.result as string
      if (type === 'product') {
        setProductImage(file)
        setImagePreview(preview)
      } else if (type === 'logo') {
        setLogoImage(file)
        setLogoPreview(preview)
      } else {
        setReferenceImage(file)
        setReferencePreview(preview)
      }
    }
    reader.readAsDataURL(file)
    setSubmitError(null)
  }

  const handleGuidelinesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > 10 * 1024 * 1024) {
      setSubmitError('Guidelines file must be less than 10MB')
      return
    }

    if (!file.type.includes('pdf') && !file.type.includes('text')) {
      setSubmitError('Please select a PDF or TXT file')
      return
    }

    setGuidelinesFile(file)
    setSubmitError(null)
  }

  const removeFile = (type: 'product' | 'logo' | 'guidelines' | 'reference') => {
    if (type === 'product') {
      setProductImage(null)
      setImagePreview('')
    } else if (type === 'logo') {
      setLogoImage(null)
      setLogoPreview('')
    } else if (type === 'guidelines') {
      setGuidelinesFile(null)
    } else {
      setReferenceImage(null)
      setReferencePreview('')
    }
  }

  const validateStep = (step: number): boolean => {
    setSubmitError(null)

    if (step === 1) {
      if (!formData.title.trim()) {
        setSubmitError('Creative title is required')
        return false
      }
      if (!formData.brand_name.trim()) {
        setSubmitError('Brand name is required')
        return false
      }
      if (!formData.product_name.trim()) {
        setSubmitError('Product name is required')
        return false
      }
      return true
    }

    if (step === 2) {
      if (!formData.creative_prompt.trim()) {
        setSubmitError('Creative vision is required')
        return false
      }
      if (formData.creative_prompt.trim().length < 20) {
        setSubmitError('Creative vision must be at least 20 characters')
        return false
      }
      return true
    }

    return true
  }

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(Math.min(currentStep + 1, 3))
    }
  }

  const handleBack = () => {
    setCurrentStep(Math.max(currentStep - 1, 1))
  }

  const uploadFileToBackend = async (
    file: File,
    assetType: 'logo' | 'product' | 'guidelines'
  ): Promise<string | null> => {
    try {
      const uploadFormData = new FormData()
      uploadFormData.append('file', file)
      uploadFormData.append('asset_type', assetType)
      
      const uploadResponse = await fetch('http://localhost:8000/api/upload-asset', {
        method: 'POST',
        body: uploadFormData,
      })
      
      if (!uploadResponse.ok) {
        throw new Error(`Failed to upload file: ${uploadResponse.statusText}`)
      }
      
      const { file_path } = await uploadResponse.json()
      return file_path
    } catch (error) {
      console.error(`Failed to upload ${assetType}:`, error)
      return null
    }
  }

  const handleSubmit = async () => {
    if (!validateStep(3)) return

    setUploading(true)
    setSubmitError(null)

    try {
      let uploadedProductUrl = ''
      let uploadedLogoUrl = ''
      let uploadedGuidelinesUrl = ''

      // Upload files if provided
      if (productImage || logoImage || guidelinesFile) {
        const uploadPromises = []

        if (productImage) {
          uploadPromises.push(
            uploadFileToBackend(productImage, 'product').then(url => {
              if (url) uploadedProductUrl = url
            })
          )
        }

        if (logoImage) {
          uploadPromises.push(
            uploadFileToBackend(logoImage, 'logo').then(url => {
              if (url) uploadedLogoUrl = url
            })
          )
        }

        if (guidelinesFile) {
          uploadPromises.push(
            uploadFileToBackend(guidelinesFile, 'guidelines').then(url => {
              if (url) uploadedGuidelinesUrl = url
            })
          )
        }

        await Promise.all(uploadPromises)
      }

      // Create creative under the campaign
      const newCreative = await createCreative(campaignId!, {
        title: formData.title,
        creative_prompt: formData.creative_prompt,
        brand_name: formData.brand_name,
        product_name: formData.product_name,
        target_audience: formData.target_audience || undefined,
        target_duration: formData.target_duration,
        logo_url: uploadedLogoUrl || undefined,
        product_image_url: uploadedProductUrl || undefined,
        guidelines_url: uploadedGuidelinesUrl || undefined,
        selected_style: selectedStyle || undefined,
        num_variations: formData.num_variations,
        video_provider: formData.video_provider,
        output_formats: ['9:16'], // Default to TikTok format
      })

      // Upload reference image if provided
      if (referenceImage && newCreative.id) {
        await uploadReferenceImage(referenceImage, newCreative.id)
      }

      setUploading(false)

      // Navigate to creative progress page with campaignId
      navigate(`/campaigns/${campaignId}/creatives/${newCreative.id}/progress`)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create creative'
      setSubmitError(message)
      setUploading(false)
    }
  }

  const stepVariants = {
    hidden: { opacity: 0, x: 20 },
    visible: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -20 },
  }

  return (
    <div className="min-h-screen bg-gradient-light">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-100/50 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-50/50 rounded-full blur-3xl"></div>
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50/30 via-transparent to-transparent" />
      </div>

      {/* Navigation Header */}
      <nav className="relative z-50 border-b border-gray-200 backdrop-blur-md bg-white/80 sticky top-0">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-gray-600 hover:text-primary-600" />
              </button>
              <div className="flex items-center gap-2">
                <div className="p-2 bg-primary-500 rounded-lg shadow-md">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <span className="text-xl font-bold text-gray-900">GenAds</span>
              </div>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-sm font-semibold text-gray-900">Create New Creative</h1>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 max-w-4xl">
          {/* Step Indicator */}
          <div className="mb-4">
            <StepIndicator currentStep={currentStep} totalSteps={3} steps={steps} />
          </div>

          {/* Error Message */}
          {(error || submitError) && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm backdrop-blur-sm"
            >
              {error || submitError}
            </motion.div>
          )}

          {/* Step Content */}
          <AnimatePresence mode="wait">
            {currentStep === 1 && (
              <motion.div
                key="step1"
                variants={stepVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                transition={{ duration: 0.3 }}
                className="bg-white backdrop-blur-sm border border-gray-200 rounded-2xl p-5 sm:p-6 shadow-lg"
              >
                <div className="space-y-4">
                  <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">Campaign Information</h2>
                    <p className="text-sm text-gray-600">Tell us about your campaign and brand</p>
                  </div>

                  <div className="space-y-4">
                    {/* Campaign Title */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-900 mb-1.5">
                        Campaign Title <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g., Chanel Noir TikTok Ad"
                        value={formData.title}
                        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
                        required
                      />
                    </div>

                    {/* Brand Name */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-900 mb-1.5">
                        Brand Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        placeholder="Your brand name"
                        value={formData.brand_name}
                        onChange={(e) => setFormData({ ...formData, brand_name: e.target.value })}
                        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
                        required
                      />
                    </div>

                    {/* Brand Description */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-900 mb-1.5">
                        Brand Description <span className="text-gray-500 text-xs font-normal">(Optional)</span>
                      </label>
                      <textarea
                        placeholder="Tell us about your brand's story, values, and personality..."
                        rows={3}
                        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all resize-none"
                      />
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {currentStep === 2 && (
              <motion.div
                key="step2"
                variants={stepVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                transition={{ duration: 0.3 }}
                className="bg-white backdrop-blur-sm border border-gray-200 rounded-2xl p-5 sm:p-6 shadow-lg"
              >
                <div className="space-y-4">
                  <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">Creative Vision</h2>
                    <p className="text-sm text-gray-600">Define your video style and settings</p>
                  </div>

                  <div className="space-y-4">
                    {/* Creative Prompt */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-900 mb-1.5">
                        Creative Vision <span className="text-red-500">*</span>
                      </label>
                      <textarea
                        placeholder="Describe your vision for the video. How should it look and feel? What story should it tell?"
                        value={formData.creative_prompt}
                        onChange={(e) => setFormData({ ...formData, creative_prompt: e.target.value })}
                        rows={3}
                        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all resize-none"
                        required
                      />
                    </div>

                    {/* Target Audience */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-900 mb-1.5">
                        Target Audience <span className="text-gray-500 text-xs font-normal">(Optional)</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g., Women 30-55 interested in natural beauty"
                        value={formData.target_audience}
                        onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
                        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
                      />
                    </div>

                    {/* Video Style Selector */}
                    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <StyleSelector
                        styles={styles}
                        selectedStyle={selectedStyle}
                        onSelectStyle={setSelectedStyle}
                        onClearStyle={clearSelection}
                        isLoading={isLoadingStyles}
                      />
                    </div>

                    {/* Video Provider Selection */}
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <label className="block text-sm font-semibold text-gray-900 mb-3">
                        Video Generation Provider
                      </label>
                      <div className="grid grid-cols-2 gap-3">
                        {(['replicate', 'ecs'] as const).map((provider) => (
                          <button
                            key={provider}
                            type="button"
                            onClick={() => setFormData({ ...formData, video_provider: provider })}
                            className={`p-3 rounded-lg border-2 transition-all duration-200 ${
                              formData.video_provider === provider
                                ? 'border-primary-500 bg-primary-50 shadow-md'
                                : 'border-gray-300 bg-white hover:border-primary-300'
                            }`}
                          >
                            <div className={`text-sm font-semibold capitalize ${formData.video_provider === provider ? 'text-primary-700' : 'text-gray-900'}`}>
                              {provider === 'replicate' ? 'Replicate' : 'ECS (Custom)'}
                            </div>
                            <p className="text-xs text-gray-600 mt-1">
                              {provider === 'replicate' ? 'Cloud-based generation' : 'Self-hosted generation'}
                            </p>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Duration Slider */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-900 mb-2">
                        Target Duration: <span className="text-primary-600 font-bold">{formData.target_duration}s</span>
                      </label>
                      <div className="space-y-2">
                        <Slider
                          value={[formData.target_duration]}
                          onValueChange={(value) => setFormData({ ...formData, target_duration: value[0] })}
                          min={15}
                          max={60}
                          step={5}
                          className="w-full"
                        />
                        <div className="flex justify-between text-xs text-gray-600">
                          <span>15s</span>
                          <span>30s</span>
                          <span>60s</span>
                        </div>
                      </div>
                    </div>

                    {/* Variation Count Selector */}
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <label className="block text-sm font-semibold text-gray-900 mb-3">
                        How many variations would you like?
                      </label>
                      <div className="flex gap-3 flex-wrap">
                        {([1, 2, 3] as const).map((num) => (
                          <button
                            key={num}
                            type="button"
                            onClick={() => setFormData({ ...formData, num_variations: num })}
                            className={`px-5 py-2.5 rounded-lg font-semibold transition-all duration-200 ${
                              formData.num_variations === num
                                ? 'bg-primary-500 text-white shadow-md'
                                : 'bg-white text-gray-900 hover:bg-gray-100 border border-gray-300'
                            }`}
                          >
                            {num} Variation{num > 1 ? 's' : ''}
                          </button>
                        ))}
                      </div>
                      <p className="text-xs text-gray-600 mt-3">
                        {formData.num_variations === 1
                          ? 'Generate one video with your selected style.'
                          : `Generate ${formData.num_variations} videos with slightly different storylines. You'll select your favorite.`}
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {currentStep === 3 && (
              <motion.div
                key="step3"
                variants={stepVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                transition={{ duration: 0.3 }}
                className="bg-white backdrop-blur-sm border border-gray-200 rounded-2xl p-5 sm:p-6 shadow-lg"
              >
                <div className="space-y-4">
                  <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">Upload Assets</h2>
                    <p className="text-sm text-gray-600">Add images and files to enhance your video (all optional)</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Product Image */}
                    <div className="space-y-2">
                      <label className="block text-sm font-semibold text-gray-900">
                        <ImageIcon className="w-4 h-4 inline mr-2 text-primary-600" />
                        Product Image
                      </label>
                      {imagePreview ? (
                        <div className="relative group">
                          <img
                            src={imagePreview}
                            alt="Product preview"
                            className="w-full h-32 object-cover rounded-lg border border-gray-200"
                          />
                          <button
                            type="button"
                            onClick={() => removeFile('product')}
                            className="absolute top-2 right-2 p-1.5 bg-red-500/90 hover:bg-red-500 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                          >
                            <X className="w-3.5 h-3.5 text-white" />
                          </button>
                        </div>
                      ) : (
                        <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary-400 hover:bg-gray-50 transition-all duration-200 group">
                          <UploadCloud className="w-6 h-6 text-gray-400 group-hover:text-primary-600 mb-1 transition-colors" />
                          <span className="text-xs text-gray-600 group-hover:text-primary-600 transition-colors">Upload product</span>
                          <input
                            type="file"
                            accept="image/*"
                            onChange={(e) => handleImageChange(e, 'product')}
                            className="hidden"
                          />
                        </label>
                      )}
                    </div>

                    {/* Brand Logo */}
                    <div className="space-y-2">
                      <label className="block text-sm font-semibold text-gray-900">
                        <Sparkles className="w-4 h-4 inline mr-2 text-primary-600" />
                        Brand Logo
                      </label>
                      {logoPreview ? (
                        <div className="relative group">
                          <img
                            src={logoPreview}
                            alt="Logo preview"
                            className="w-full h-32 object-contain bg-gray-50 rounded-lg border border-gray-200 p-3"
                          />
                          <button
                            type="button"
                            onClick={() => removeFile('logo')}
                            className="absolute top-2 right-2 p-1.5 bg-red-500/90 hover:bg-red-500 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                          >
                            <X className="w-3.5 h-3.5 text-white" />
                          </button>
                        </div>
                      ) : (
                        <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary-400 hover:bg-gray-50 transition-all duration-200 group">
                          <UploadCloud className="w-6 h-6 text-gray-400 group-hover:text-primary-600 mb-1 transition-colors" />
                          <span className="text-xs text-gray-600 group-hover:text-primary-600 transition-colors">Upload logo</span>
                          <input
                            type="file"
                            accept="image/*"
                            onChange={(e) => handleImageChange(e, 'logo')}
                            className="hidden"
                          />
                        </label>
                      )}
                    </div>
                  </div>

                  {/* Brand Guidelines */}
                  <div className="space-y-2">
                    <label className="block text-sm font-semibold text-gray-900">
                      <FileText className="w-4 h-4 inline mr-2 text-primary-600" />
                      Brand Guidelines
                    </label>
                    {guidelinesFile ? (
                      <div className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 bg-primary-50 rounded-lg border border-primary-200">
                            <FileText className="w-4 h-4 text-primary-600" />
                          </div>
                          <div>
                            <p className="text-xs font-medium text-gray-900">{guidelinesFile.name}</p>
                            <p className="text-xs text-gray-600">
                              {(guidelinesFile.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeFile('guidelines')}
                          className="p-1.5 text-gray-600 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary-400 hover:bg-gray-50 transition-all duration-200 group">
                        <UploadCloud className="w-6 h-6 text-gray-400 group-hover:text-primary-600 mb-1 transition-colors" />
                        <span className="text-xs text-gray-600 group-hover:text-primary-600 transition-colors">Upload guidelines</span>
                        <input
                          type="file"
                          accept=".pdf,.txt,text/plain,application/pdf"
                          onChange={handleGuidelinesChange}
                          className="hidden"
                        />
                      </label>
                    )}
                  </div>

                  {/* Reference Image */}
                  <div className="space-y-2">
                    <label className="block text-sm font-semibold text-gray-900">
                      <Palette className="w-4 h-4 inline mr-2 text-primary-600" />
                      Reference Image <span className="text-gray-500 text-xs font-normal">(Optional)</span>
                    </label>
                    {referencePreview ? (
                      <div className="relative group">
                        <img
                          src={referencePreview}
                          alt="Reference preview"
                          className="w-full h-32 object-cover rounded-lg border border-primary-200"
                        />
                        <button
                          type="button"
                          onClick={() => removeFile('reference')}
                          className="absolute top-2 right-2 p-1.5 bg-red-500/90 hover:bg-red-500 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                        >
                          <X className="w-3.5 h-3.5 text-white" />
                        </button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary-400 hover:bg-gray-50 transition-all duration-200 group">
                        <UploadCloud className="w-6 h-6 text-gray-400 group-hover:text-primary-600 mb-1 transition-colors" />
                        <span className="text-xs text-gray-600 group-hover:text-primary-600 transition-colors">Upload reference</span>
                        <input
                          type="file"
                          accept="image/*"
                          onChange={(e) => handleImageChange(e, 'reference')}
                          className="hidden"
                          disabled={isUploadingReference}
                        />
                      </label>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Navigation Buttons */}
          <div className="flex items-center justify-between gap-4 mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={currentStep === 1 ? () => navigate('/dashboard') : handleBack}
              className="gap-2 border-olive-600 text-muted-gray hover:text-gold hover:border-gold transition-transform duration-200 hover:scale-105"
            >
              <ArrowLeft className="w-4 h-4" />
              {currentStep === 1 ? 'Cancel' : 'Back'}
            </Button>

            {currentStep < 3 ? (
              <Button
                type="button"
                onClick={handleNext}
                className="gap-2 bg-gold text-gold-foreground hover:bg-accent-gold-dark transition-transform duration-200 hover:scale-105"
              >
                Next
                <ArrowRight className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                type="button"
                onClick={handleSubmit}
                disabled={loading || uploading}
                className="gap-2 bg-gold text-gold-foreground hover:bg-accent-gold-dark disabled:opacity-50 transition-transform duration-200 hover:scale-105"
              >
                {loading || uploading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-gold-foreground/30 border-t-gold-foreground rounded-full animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Video className="w-4 h-4" />
                    Start Creating Video
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
