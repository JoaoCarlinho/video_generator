import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Container, Header } from '@/components/layout'
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Select, Modal } from '@/components/ui'
import { useProjects } from '@/hooks/useProjects'
import { Upload, X, Zap } from 'lucide-react'

export const CreateProject = () => {
  const navigate = useNavigate()
  const { createProject, loading, error } = useProjects()

  const [formData, setFormData] = useState({
    title: '',
    creative_prompt: '',
    brand_name: '',
    brand_description: '',
    target_audience: '',
    target_duration: 30,
    aspect_ratio: '16:9' as '9:16' | '1:1' | '16:9',
    logo_url: '',
    product_image_url: '',
    guidelines_url: '',
  })

  const [productImage, setProductImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string>('')
  const [logoImage, setLogoImage] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string>('')
  const [guidelinesFile, setGuidelinesFile] = useState<File | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [autoGenerate, setAutoGenerate] = useState(true)
  const [uploading, setUploading] = useState(false)

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setSubmitError('Image must be less than 10MB')
        return
      }

      // Validate file type
      if (!file.type.startsWith('image/')) {
        setSubmitError('Please select an image file')
        return
      }

      setProductImage(file)
      setSubmitError(null)

      // Create preview
      const reader = new FileReader()
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleRemoveImage = () => {
    setProductImage(null)
    setImagePreview('')
  }

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file size (max 5MB for logo)
      if (file.size > 5 * 1024 * 1024) {
        setSubmitError('Logo must be less than 5MB')
        return
      }

      // Validate file type
      if (!file.type.startsWith('image/')) {
        setSubmitError('Please select an image file for logo')
        return
      }

      setLogoImage(file)
      setSubmitError(null)

      // Create preview
      const reader = new FileReader()
      reader.onload = (e) => {
        setLogoPreview(e.target?.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleRemoveLogo = () => {
    setLogoImage(null)
    setLogoPreview('')
  }

  const handleGuidelinesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setSubmitError('Guidelines file must be less than 10MB')
        return
      }

      // Validate file type (PDF or TXT)
      if (!file.type.includes('pdf') && !file.type.includes('text')) {
        setSubmitError('Please select a PDF or TXT file for guidelines')
        return
      }

      setGuidelinesFile(file)
      setSubmitError(null)
    }
  }

  const handleRemoveGuidelines = () => {
    setGuidelinesFile(null)
  }

  const validateForm = (): boolean => {
    if (!formData.title.trim()) {
      setSubmitError('Project title is required')
      return false
    }

    if (!formData.creative_prompt.trim()) {
      setSubmitError('Creative prompt is required')
      return false
    }

    if (formData.creative_prompt.trim().length < 20) {
      setSubmitError('Creative prompt must be at least 20 characters')
      return false
    }

    if (!formData.brand_name.trim()) {
      setSubmitError('Brand name is required')
      return false
    }

    if (formData.target_duration < 15 || formData.target_duration > 120) {
      setSubmitError('Duration must be between 15 and 120 seconds')
      return false
    }

    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitError(null)

    if (!validateForm()) {
      return
    }

    // Show confirmation modal instead of creating directly
    setShowConfirmation(true)
  }

  const uploadFileToBackend = async (
    file: File,
    assetType: 'logo' | 'product' | 'guidelines'
  ): Promise<string | null> => {
    try {
      console.log(`📤 Uploading ${assetType}: ${file.name}`)
      
      // Create FormData for multipart upload
      const uploadFormData = new FormData()
      uploadFormData.append('file', file)
      uploadFormData.append('asset_type', assetType)
      
      // Upload file to backend (local filesystem)
      const uploadResponse = await fetch('http://localhost:8000/api/upload-asset', {
        method: 'POST',
        body: uploadFormData,
        // Don't set Content-Type header - browser will set it with boundary for multipart
      })
      
      if (!uploadResponse.ok) {
        throw new Error(`Failed to upload file: ${uploadResponse.statusText}`)
      }
      
      const { file_path } = await uploadResponse.json()
      
      console.log(`✅ Uploaded ${assetType} to local filesystem: ${file_path}`)
      return file_path
      
    } catch (error) {
      console.error(`❌ Failed to upload ${assetType}:`, error)
      return null
    }
  }

  const handleConfirmCreate = async () => {
    setShowConfirmation(false)
    setUploading(true)
    setSubmitError(null)
    
    try {
      console.log('🚀 Creating project with data:', {
        title: formData.title,
        brand_name: formData.brand_name,
        target_duration: formData.target_duration,
      })

      // Upload files to S3 if selected
      let uploadedProductUrl = formData.product_image_url
      let uploadedLogoUrl = formData.logo_url
      let uploadedGuidelinesUrl = formData.guidelines_url
      
      if (productImage || logoImage || guidelinesFile) {
        console.log('📦 Uploading files to S3...')
        
        // Upload files in parallel
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
        
        // Wait for all uploads to complete
        await Promise.all(uploadPromises)
        console.log('✅ All files uploaded successfully')
      }

      const newProject = await createProject({
        title: formData.title,
        creative_prompt: formData.creative_prompt,
        brand_name: formData.brand_name,
        brand_description: formData.brand_description || undefined,
        target_audience: formData.target_audience || undefined,
        target_duration: formData.target_duration,
        aspect_ratio: formData.aspect_ratio,
        logo_url: uploadedLogoUrl || undefined,
        product_image_url: uploadedProductUrl || undefined,
        guidelines_url: uploadedGuidelinesUrl || undefined,
      })

      console.log('✅ Project created:', newProject)
      setUploading(false)

      // Navigate immediately or to dashboard based on autoGenerate
      if (autoGenerate) {
        console.log('📍 Navigating to progress page:', `/projects/${newProject.id}/progress`)
        navigate(`/projects/${newProject.id}/progress`)
      } else {
        console.log('📍 Navigating to dashboard')
        navigate('/dashboard')
      }
    } catch (err) {
      console.error('❌ Error creating project:', err)
      const message = err instanceof Error ? err.message : 'Failed to create project'
      setSubmitError(message)
      setUploading(false)
      setShowConfirmation(true) // Show modal again so user can retry
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
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 flex flex-col">
      {/* Header */}
      <Header logo="GenAds" title="Create Project" />

      {/* Main Content */}
      <div className="flex-1">
        <Container size="md" className="py-12">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-8"
          >
            {/* Title */}
            <motion.div variants={itemVariants}>
              <h2 className="text-3xl font-bold text-slate-100">New Project</h2>
              <p className="text-slate-400 mt-2">
                Create a new video project. Fill in the details below and we'll generate
                your ads.
              </p>
            </motion.div>

            {/* Form Card */}
            <motion.div variants={itemVariants}>
              <Card variant="glass">
                <CardHeader>
                  <CardTitle>Project Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Error Message */}
                    {(error || submitError) && (
                      <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
                        {error || submitError}
                      </div>
                    )}

                    {/* Project Title */}
                    <Input
                      label="Project Title"
                      placeholder="e.g., Premium Skincare - Summer Campaign"
                      value={formData.title}
                      onChange={(e) =>
                        setFormData({ ...formData, title: e.target.value })
                      }
                      required
                    />

                    {/* Brand Name */}
                    <Input
                      label="Brand Name"
                      placeholder="Your brand name"
                      value={formData.brand_name}
                      onChange={(e) =>
                        setFormData({ ...formData, brand_name: e.target.value })
                      }
                      required
                    />

                    {/* Brand Description (Optional) */}
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Brand Description <span className="text-slate-500">(Optional)</span>
                      </label>
                      <textarea
                        placeholder="Tell us about your brand's story, values, and personality. Example: Premium skincare for conscious consumers who value sustainability and natural ingredients."
                        value={formData.brand_description}
                        onChange={(e) =>
                          setFormData({ ...formData, brand_description: e.target.value })
                        }
                        rows={2}
                        className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                      />
                    </div>

                    {/* Creative Prompt */}
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Creative Vision <span className="text-red-400">*</span>
                      </label>
                      <textarea
                        placeholder="Describe your vision for the video. How should it look and feel? What story should it tell? Example: Create an energetic video that starts with a problem (tired skin), showcases our serum transforming skin in 7 days, and ends with confident customers. Use bright, clean aesthetics with dynamic camera movements."
                        value={formData.creative_prompt}
                        onChange={(e) =>
                          setFormData({ ...formData, creative_prompt: e.target.value })
                        }
                        rows={5}
                        className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                        required
                      />
                      <p className="text-xs text-slate-500 mt-1">
                        💡 Be specific about mood, pacing, and key moments. The AI will bring your vision to life.
                      </p>
                    </div>

                    {/* Target Audience (Optional) */}
                    <Input
                      label="Target Audience (Optional)"
                      placeholder="e.g., Women 30-55 interested in natural beauty"
                      value={formData.target_audience}
                      onChange={(e) =>
                        setFormData({ ...formData, target_audience: e.target.value })
                      }
                    />

                    {/* Duration */}
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Target Video Duration (seconds)
                      </label>
                      <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="15"
                        max="120"
                        step="5"
                        value={String(formData.target_duration)}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            target_duration: parseInt(e.target.value),
                          })
                        }
                          className="flex-1 h-2 bg-slate-800 rounded-lg accent-indigo-600 cursor-pointer"
                        />
                        <div className="w-20 text-center">
                          <span className="text-2xl font-bold text-indigo-400">
                            {formData.target_duration}s
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-500 mt-2">
                        ⏱️ The AI will pace scenes naturally around this target (±20% is OK)
                      </p>
                    </div>

                    {/* Aspect Ratio Selection */}
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Video Aspect Ratio
                      </label>
                      <div className="grid grid-cols-3 gap-3">
                        {(['9:16', '1:1', '16:9'] as const).map((ar) => (
                          <button
                            key={ar}
                            type="button"
                            onClick={() => setFormData({ ...formData, aspect_ratio: ar })}
                            className={`p-3 rounded-lg border-2 transition-all text-sm font-medium ${
                              formData.aspect_ratio === ar
                                ? 'border-indigo-500 bg-indigo-500/20 text-indigo-200'
                                : 'border-slate-700 bg-slate-800/30 text-slate-300 hover:border-slate-600'
                            }`}
                          >
                            <div className="font-semibold">
                              {ar === '9:16' ? '📱 Vertical' : ar === '1:1' ? '⬜ Square' : '🖥️ Horizontal'}
                            </div>
                            <div className="text-xs text-slate-400 mt-1">
                              {ar === '9:16' ? '1080×1920' : ar === '1:1' ? '1080×1080' : '1920×1080'}
                            </div>
                          </button>
                        ))}
                      </div>
                      <p className="text-xs text-slate-500 mt-2">
                        💡 Choose your video format based on your platform
                      </p>
                    </div>

                    {/* Asset Uploads Section */}
                    <div className="space-y-6 p-6 bg-slate-800/30 rounded-lg border border-slate-700">
                      <h3 className="text-lg font-semibold text-slate-200">
                        Assets <span className="text-slate-500 text-sm font-normal">(All Optional)</span>
                      </h3>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Product Image Upload */}
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-2">
                            Product Image
                          </label>
                          {imagePreview ? (
                            <div className="relative w-full">
                              <img
                                src={imagePreview}
                                alt="Product preview"
                                className="w-full h-40 object-cover rounded-lg border border-slate-700"
                              />
                              <button
                                type="button"
                                onClick={handleRemoveImage}
                                className="absolute top-2 right-2 p-1 bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
                              >
                                <X className="w-4 h-4 text-white" />
                              </button>
                            </div>
                          ) : (
                            <label className="flex items-center justify-center w-full h-40 border-2 border-dashed border-slate-700 rounded-lg cursor-pointer hover:bg-slate-800/50 transition-colors">
                              <div className="flex flex-col items-center justify-center">
                                <Upload className="w-6 h-6 text-slate-500 mb-1" />
                                <span className="text-sm text-slate-400">
                                  Upload product
                                </span>
                                <span className="text-xs text-slate-500 mt-1">
                                  PNG, JPG (Max 10MB)
                                </span>
                              </div>
                              <input
                                type="file"
                                accept="image/*"
                                onChange={handleImageChange}
                                className="hidden"
                              />
                            </label>
                          )}
                          <p className="text-xs text-slate-500 mt-2">
                            AI will composite your product into scenes
                          </p>
                        </div>

                        {/* Brand Logo Upload */}
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-2">
                            Brand Logo
                          </label>
                          {logoPreview ? (
                            <div className="relative w-full">
                              <img
                                src={logoPreview}
                                alt="Logo preview"
                                className="w-full h-40 object-contain bg-slate-900/50 rounded-lg border border-slate-700 p-4"
                              />
                              <button
                                type="button"
                                onClick={handleRemoveLogo}
                                className="absolute top-2 right-2 p-1 bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
                              >
                                <X className="w-4 h-4 text-white" />
                              </button>
                            </div>
                          ) : (
                            <label className="flex items-center justify-center w-full h-40 border-2 border-dashed border-slate-700 rounded-lg cursor-pointer hover:bg-slate-800/50 transition-colors">
                              <div className="flex flex-col items-center justify-center">
                                <Upload className="w-6 h-6 text-slate-500 mb-1" />
                                <span className="text-sm text-slate-400">
                                  Upload logo
                                </span>
                                <span className="text-xs text-slate-500 mt-1">
                                  PNG, SVG (Max 5MB)
                                </span>
                              </div>
                              <input
                                type="file"
                                accept="image/*"
                                onChange={handleLogoChange}
                                className="hidden"
                              />
                            </label>
                          )}
                          <p className="text-xs text-slate-500 mt-2">
                            AI will place logo strategically (usually final scene)
                          </p>
                        </div>
                      </div>

                      {/* Brand Guidelines Upload */}
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          Brand Guidelines
                        </label>
                        {guidelinesFile ? (
                          <div className="flex items-center justify-between p-4 bg-slate-900/50 border border-slate-700 rounded-lg">
                            <div className="flex items-center gap-3">
                              <div className="p-2 bg-indigo-500/20 rounded-lg">
                                <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                              </div>
                              <div>
                                <p className="text-sm text-slate-200 font-medium">{guidelinesFile.name}</p>
                                <p className="text-xs text-slate-500">
                                  {(guidelinesFile.size / 1024 / 1024).toFixed(2)} MB
                                </p>
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={handleRemoveGuidelines}
                              className="p-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
                            >
                              <X className="w-4 h-4 text-white" />
                            </button>
                          </div>
                        ) : (
                          <label className="flex items-center justify-center w-full h-24 border-2 border-dashed border-slate-700 rounded-lg cursor-pointer hover:bg-slate-800/50 transition-colors">
                            <div className="flex flex-col items-center justify-center">
                              <Upload className="w-6 h-6 text-slate-500 mb-1" />
                              <span className="text-sm text-slate-400">
                                Upload brand guidelines
                              </span>
                              <span className="text-xs text-slate-500 mt-1">
                                PDF, TXT (Max 10MB)
                              </span>
                            </div>
                            <input
                              type="file"
                              accept=".pdf,.txt,text/plain,application/pdf"
                              onChange={handleGuidelinesChange}
                              className="hidden"
                            />
                          </label>
                        )}
                        <p className="text-xs text-slate-500 mt-2">
                          💡 AI will follow your brand guidelines for tone and style
                        </p>
                      </div>
                    </div>

                    {/* Submit Buttons */}
                    <div className="flex gap-4 pt-6 border-t border-slate-700">
                      <Button
                        type="button"
                        variant="outline"
                        fullWidth
                        onClick={() => navigate('/dashboard')}
                        disabled={loading}
                      >
                        Cancel
                      </Button>
                  <Button
                    type="submit"
                    variant="gradient"
                    fullWidth
                  >
                    {loading ? 'Creating...' : 'Create Project'}
                  </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </motion.div>

            {/* Info Boxes */}
            <motion.div variants={itemVariants} className="space-y-4">
              <div className="p-4 bg-indigo-500/10 border border-indigo-500/50 rounded-lg">
                <p className="text-indigo-400 text-sm">
                  💡 <strong>Pro Tip:</strong> Be specific in your creative vision! Describe the mood, pacing, key moments, and visual style you want. The AI director will bring your vision to life with professional camera work and scene pacing.
                </p>
              </div>
              
              {(productImage || logoImage || guidelinesFile) && (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/50 rounded-lg">
                  <p className="text-emerald-400 text-sm">
                    ✅ <strong>Ready to upload:</strong> Your files will be uploaded to S3 before creating the project. The AI will use these assets when generating your video.
                  </p>
                </div>
              )}
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
          {/* Project Details Review */}
          <div className="space-y-4 bg-slate-900/50 p-4 rounded-lg">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase">
                  Project Title
                </label>
                <p className="text-slate-100 mt-1">{formData.title}</p>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase">
                  Brand Name
                </label>
                <p className="text-slate-100 mt-1">{formData.brand_name}</p>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase">
                Creative Vision
              </label>
              <p className="text-slate-100 mt-1 text-sm">{formData.creative_prompt}</p>
            </div>

            {formData.brand_description && (
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase">
                  Brand Description
                </label>
                <p className="text-slate-100 mt-1 text-sm">{formData.brand_description}</p>
              </div>
            )}

            <div className="grid grid-cols-3 gap-4">
              {formData.target_audience && (
                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase">
                    Target Audience
                  </label>
                  <p className="text-slate-100 mt-1 text-sm">{formData.target_audience}</p>
                </div>
              )}
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase">
                  Target Duration
                </label>
                <p className="text-slate-100 mt-1">{formData.target_duration}s</p>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase">
                  Aspect Ratio
                </label>
                <p className="text-slate-100 mt-1">
                  {formData.aspect_ratio === '9:16' ? '📱 Vertical (1080×1920)' : formData.aspect_ratio === '1:1' ? '⬜ Square (1080×1080)' : '🖥️ Horizontal (1920×1080)'}
                </p>
              </div>
            </div>

            {/* Assets Section */}
            {(productImage || logoImage || guidelinesFile) && (
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase mb-2 block">
                  Uploaded Assets
                </label>
                <div className="flex flex-wrap gap-2">
                  {productImage && (
                    <span className="px-3 py-1 bg-indigo-500/20 text-indigo-400 rounded-full text-xs">
                      ✓ Product Image
                    </span>
                  )}
                  {logoImage && (
                    <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-full text-xs">
                      ✓ Brand Logo
                    </span>
                  )}
                  {guidelinesFile && (
                    <span className="px-3 py-1 bg-cyan-500/20 text-cyan-400 rounded-full text-xs">
                      ✓ Brand Guidelines
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Cost Estimate */}
          <div className="bg-emerald-500/10 border border-emerald-500/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-400 uppercase">
                Estimated Cost
              </span>
            </div>
            <p className="text-2xl font-bold text-emerald-400">$0.19 - $0.43</p>
            <p className="text-xs text-emerald-300 mt-1">
              Final cost may vary based on complexity
            </p>
          </div>

          {/* Auto-Generate Option */}
          <div className="flex items-center gap-3 p-3 bg-indigo-500/10 border border-indigo-500/30 rounded-lg">
            <input
              type="checkbox"
              id="autoGenerate"
              checked={autoGenerate}
              onChange={(e) => setAutoGenerate(e.target.checked)}
              className="w-4 h-4 rounded accent-indigo-600 cursor-pointer"
            />
            <label htmlFor="autoGenerate" className="flex-1 cursor-pointer">
              <p className="text-sm font-medium text-slate-100">
                Start generation immediately
              </p>
              <p className="text-xs text-slate-400">
                {autoGenerate
                  ? 'You will be taken to the progress page'
                  : 'Project will be saved as draft'}
              </p>
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4 border-t border-slate-700">
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
              variant="gradient"
              fullWidth
              onClick={handleConfirmCreate}
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create Project'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

