import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui'
import { StepIndicator } from '@/components/ui/StepIndicator'
import { StyleSelector } from '@/components/ui/StyleSelector'
import { useProjects } from '@/hooks/useProjects'
import { useReferenceImage } from '@/hooks/useReferenceImage'
import { useStyleSelector } from '@/hooks/useStyleSelector'
import { Upload, X, Sparkles, ArrowRight, ArrowLeft, FileText, Image as ImageIcon, Video, Palette, UploadCloud } from 'lucide-react'
import { Slider } from '@/components/ui/slider'

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

  // Provider Selection
  video_provider: string

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
  video_provider: 'replicate',
  product_images: [],
  logo_images: [],
  guidelines_file: null,
}

export const CreateProject = () => {
  const navigate = useNavigate()
  const { createProject, loading, error } = useProjects()
  const { uploadReferenceImage, isLoading: isUploadingReference } = useReferenceImage()
  const { styles, selectedStyle, setSelectedStyle, clearSelection, isLoading: isLoadingStyles } = useStyleSelector()

  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState({
    title: '',
    brand_name: '',
    brand_description: '',
    creative_prompt: '',
    target_audience: '',
    target_duration: 30,
    perfume_name: '',
    perfume_gender: 'unisex' as 'masculine' | 'feminine' | 'unisex',
    num_variations: 1 as 1 | 2 | 3, // Phase 3: Multi-variation support
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
    { label: 'Project Info', description: 'Basic details' },
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
        setSubmitError('Project title is required')
        return false
      }
      if (!formData.brand_name.trim()) {
        setSubmitError('Brand name is required')
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
      if (!formData.perfume_name.trim()) {
        setSubmitError('Perfume name is required')
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

      const newProject = await createProject({
        title: formData.title,
        creative_prompt: formData.creative_prompt,
        brand_name: formData.brand_name,
        brand_description: formData.brand_description || undefined,
        target_audience: formData.target_audience || undefined,
        target_duration: formData.target_duration,
        perfume_name: formData.perfume_name,
        perfume_gender: formData.perfume_gender,
        logo_url: uploadedLogoUrl || undefined,
        product_image_url: uploadedProductUrl || undefined,
        guidelines_url: uploadedGuidelinesUrl || undefined,
        selected_style: selectedStyle || undefined,
        num_variations: formData.num_variations, // Phase 3: Include variation count
      } as any)

      if (referenceImage) {
        await uploadReferenceImage(referenceImage, newProject.id)
      }

      setUploading(false)
      navigate(`/projects/${newProject.id}/progress`)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create project'
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
    <div className="min-h-screen bg-gradient-hero">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gold-silky/10 rounded-full blur-3xl"></div>
        <div className="absolute inset-0 bg-gradient-to-br from-gold/5 via-transparent to-transparent" />
      </div>

      {/* Navigation Header */}
      <nav className="relative z-10 border-b border-olive-600/50 backdrop-blur-md bg-olive-950/50 sticky top-0">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 hover:bg-olive-800/50 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-muted-gray hover:text-gold" />
              </button>
              <div className="flex items-center gap-2">
                <div className="p-2 bg-gold rounded-lg shadow-gold">
                  <Sparkles className="h-5 w-5 text-gold-foreground" />
                </div>
                <span className="text-xl font-bold text-gradient-gold">GenAds</span>
              </div>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-sm font-semibold text-off-white">Create New Project</h1>
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
              className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm backdrop-blur-sm"
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
                className="bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-2xl p-5 sm:p-6 shadow-gold-lg"
              >
                <div className="space-y-4">
                  <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-off-white mb-1">Project Information</h2>
                    <p className="text-sm text-muted-gray">Tell us about your project and brand</p>
                  </div>

                  <div className="space-y-4">
                    {/* Project Title */}
                    <div>
                      <label className="block text-sm font-semibold text-off-white mb-1.5">
                        Project Title <span className="text-red-400">*</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g., Chanel Noir TikTok Ad"
                        value={formData.title}
                        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                        className="w-full px-3 py-2 bg-olive-700/50 border border-olive-600 rounded-lg text-sm text-off-white placeholder-muted-gray focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/30 transition-all"
                        required
                      />
                    </div>

                    {/* Brand Name */}
                    <div>
                      <label className="block text-sm font-semibold text-off-white mb-1.5">
                        Brand Name <span className="text-red-400">*</span>
                      </label>
                      <input
                        type="text"
                        placeholder="Your brand name"
                        value={formData.brand_name}
                        onChange={(e) => setFormData({ ...formData, brand_name: e.target.value })}
                        className="w-full px-3 py-2 bg-olive-700/50 border border-olive-600 rounded-lg text-sm text-off-white placeholder-muted-gray focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/30 transition-all"
                        required
                      />
                    </div>

                    {/* Brand Description */}
                    <div>
                      <label className="block text-sm font-semibold text-off-white mb-1.5">
                        Brand Description <span className="text-muted-gray text-xs font-normal">(Optional)</span>
                      </label>
                      <textarea
                        placeholder="Tell us about your brand's story, values, and personality..."
                        value={formData.brand_description}
                        onChange={(e) => setFormData({ ...formData, brand_description: e.target.value })}
                        rows={3}
                        className="w-full px-3 py-2 bg-olive-700/50 border border-olive-600 rounded-lg text-sm text-off-white placeholder-muted-gray focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/30 transition-all resize-none"
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
                className="bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-2xl p-5 sm:p-6 shadow-gold-lg"
              >
                <div className="space-y-4">
                  <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-off-white mb-1">Creative Vision</h2>
                    <p className="text-sm text-muted-gray">Define your video style and settings</p>
                  </div>

                  <div className="space-y-4">
                    {/* Creative Prompt */}
                    <div>
                      <label className="block text-sm font-semibold text-off-white mb-1.5">
                        Creative Vision <span className="text-red-400">*</span>
                      </label>
                      <textarea
                        placeholder="Describe your vision for the video. How should it look and feel? What story should it tell?"
                        value={formData.creative_prompt}
                        onChange={(e) => setFormData({ ...formData, creative_prompt: e.target.value })}
                        rows={3}
                        className="w-full px-3 py-2 bg-olive-700/50 border border-olive-600 rounded-lg text-sm text-off-white placeholder-muted-gray focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/30 transition-all resize-none"
                        required
                      />
                    </div>

                    {/* Target Audience */}
                    <div>
                      <label className="block text-sm font-semibold text-off-white mb-1.5">
                        Target Audience <span className="text-muted-gray text-xs font-normal">(Optional)</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g., Women 30-55 interested in natural beauty"
                        value={formData.target_audience}
                        onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
                        className="w-full px-3 py-2 bg-olive-700/50 border border-olive-600 rounded-lg text-sm text-off-white placeholder-muted-gray focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/30 transition-all"
                      />
                    </div>

                    {/* Video Style Selector */}
                    <div className="p-3 bg-olive-700/30 rounded-lg border border-olive-600/50">
                      <StyleSelector
                        styles={styles}
                        selectedStyle={selectedStyle}
                        onSelectStyle={setSelectedStyle}
                        onClearStyle={clearSelection}
                        isLoading={isLoadingStyles}
                      />
                    </div>

                    {/* Perfume Name */}
                    <div>
                      <label className="block text-sm font-semibold text-off-white mb-1.5">
                        Perfume Name <span className="text-red-400">*</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g., Noir Élégance"
                        value={formData.perfume_name}
                        onChange={(e) => setFormData({ ...formData, perfume_name: e.target.value })}
                        className="w-full px-3 py-2 bg-olive-700/50 border border-olive-600 rounded-lg text-sm text-off-white placeholder-muted-gray focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/30 transition-all"
                        required
                      />
                    </div>

                    {/* Perfume Gender */}
                    <div>
                      <label className="block text-sm font-semibold text-off-white mb-2">
                        Perfume Gender <span className="text-red-400">*</span>
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        {(['masculine', 'feminine', 'unisex'] as const).map((gender) => (
                          <button
                            key={gender}
                            type="button"
                            onClick={() => setFormData({ ...formData, perfume_gender: gender })}
                            className={`p-2.5 rounded-lg border-2 transition-all duration-200 ${
                              formData.perfume_gender === gender
                                ? 'border-gold bg-gold/10 shadow-gold'
                                : 'border-olive-600 bg-olive-700/30 hover:border-olive-500'
                            }`}
                          >
                            <div className={`text-sm font-semibold capitalize ${formData.perfume_gender === gender ? 'text-gold' : 'text-off-white'}`}>
                              {gender}
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Duration Slider */}
                    <div>
                      <label className="block text-sm font-semibold text-off-white mb-2">
                        Target Duration: <span className="text-gold font-bold">{formData.target_duration}s</span>
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
                        <div className="flex justify-between text-xs text-muted-gray">
                          <span>15s</span>
                          <span>30s</span>
                          <span>60s</span>
                        </div>
                      </div>
                    </div>

                    {/* Variation Count Selector */}
                    <div className="p-4 bg-olive-700/30 rounded-lg border border-olive-600/50">
                      <label className="block text-sm font-semibold text-off-white mb-3">
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
                                ? 'bg-gold text-gold-foreground shadow-gold'
                                : 'bg-olive-700/50 text-off-white hover:bg-olive-600/50 border border-olive-600'
                            }`}
                          >
                            {num} Variation{num > 1 ? 's' : ''}
                          </button>
                        ))}
                      </div>
                      <p className="text-xs text-muted-gray mt-3">
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
                className="bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-2xl p-5 sm:p-6 shadow-gold-lg"
              >
                <div className="space-y-4">
                  <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-off-white mb-1">Upload Assets</h2>
                    <p className="text-sm text-muted-gray">Add images and files to enhance your video (all optional)</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Product Image */}
                    <div className="space-y-2">
                      <label className="block text-sm font-semibold text-off-white">
                        <ImageIcon className="w-4 h-4 inline mr-2 text-gold" />
                        Product Image
                      </label>
                      {imagePreview ? (
                        <div className="relative group">
                          <img
                            src={imagePreview}
                            alt="Product preview"
                            className="w-full h-32 object-cover rounded-lg border border-olive-600"
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
                        <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-olive-600 rounded-lg cursor-pointer hover:border-gold/50 hover:bg-olive-700/20 transition-all duration-200 group">
                          <UploadCloud className="w-6 h-6 text-muted-gray group-hover:text-gold mb-1 transition-colors" />
                          <span className="text-xs text-muted-gray group-hover:text-gold transition-colors">Upload product</span>
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
                      <label className="block text-sm font-semibold text-off-white">
                        <Sparkles className="w-4 h-4 inline mr-2 text-gold" />
                        Brand Logo
                      </label>
                      {logoPreview ? (
                        <div className="relative group">
                          <img
                            src={logoPreview}
                            alt="Logo preview"
                            className="w-full h-32 object-contain bg-olive-700/30 rounded-lg border border-olive-600 p-3"
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
                        <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-olive-600 rounded-lg cursor-pointer hover:border-gold/50 hover:bg-olive-700/20 transition-all duration-200 group">
                          <UploadCloud className="w-6 h-6 text-muted-gray group-hover:text-gold mb-1 transition-colors" />
                          <span className="text-xs text-muted-gray group-hover:text-gold transition-colors">Upload logo</span>
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
                    <label className="block text-sm font-semibold text-off-white">
                      <FileText className="w-4 h-4 inline mr-2 text-gold" />
                      Brand Guidelines
                    </label>
                    {guidelinesFile ? (
                      <div className="flex items-center justify-between p-3 bg-olive-700/30 border border-olive-600 rounded-lg">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 bg-gold/10 rounded-lg border border-gold/20">
                            <FileText className="w-4 h-4 text-gold" />
                          </div>
                          <div>
                            <p className="text-xs font-medium text-off-white">{guidelinesFile.name}</p>
                            <p className="text-xs text-muted-gray">
                              {(guidelinesFile.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeFile('guidelines')}
                          className="p-1.5 text-muted-gray hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-olive-600 rounded-lg cursor-pointer hover:border-gold/50 hover:bg-olive-700/20 transition-all duration-200 group">
                        <UploadCloud className="w-6 h-6 text-muted-gray group-hover:text-gold mb-1 transition-colors" />
                        <span className="text-xs text-muted-gray group-hover:text-gold transition-colors">Upload guidelines</span>
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
                    <label className="block text-sm font-semibold text-off-white">
                      <Palette className="w-4 h-4 inline mr-2 text-gold" />
                      Reference Image <span className="text-muted-gray text-xs font-normal">(Optional)</span>
                    </label>
                    {referencePreview ? (
                      <div className="relative group">
                        <img
                          src={referencePreview}
                          alt="Reference preview"
                          className="w-full h-32 object-cover rounded-lg border border-gold/30"
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
                      <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-olive-600 rounded-lg cursor-pointer hover:border-gold/50 hover:bg-olive-700/20 transition-all duration-200 group">
                        <UploadCloud className="w-6 h-6 text-muted-gray group-hover:text-gold mb-1 transition-colors" />
                        <span className="text-xs text-muted-gray group-hover:text-gold transition-colors">Upload reference</span>
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
                variant="hero"
                onClick={handleNext}
                className="gap-2 transition-transform duration-200 hover:scale-105"
              >
                Next
                <ArrowRight className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                type="button"
                variant="hero"
                onClick={handleSubmit}
                disabled={loading || uploading}
                className="gap-2 transition-transform duration-200 hover:scale-105"
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
