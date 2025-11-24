import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { Input } from '@/components/ui'
import { useBrand, getBrandLogoUrl } from '@/hooks/useBrand'
import { useAuth } from '@/hooks/useAuth'
import { UploadCloud, FileText, Image as ImageIcon, X, CheckCircle, Sparkles, LogOut, Building2, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export const Onboarding = () => {
  const navigate = useNavigate()
  const { onboardBrand, loading, error, brand, fetchBrand } = useBrand()
  const { logout } = useAuth()
  const isNavigatingRef = useRef(false) // Prevent navigation loops

  // State declarations
  const [brandName, setBrandName] = useState('')
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string>('')
  const [guidelinesFile, setGuidelinesFile] = useState<File | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)

  const handleSignOut = async () => {
    try {
      await logout()
      navigate('/login')
    } catch (err) {
      console.error('Error signing out:', err)
    }
  }

  // Fetch brand on mount to check if user already has one
  useEffect(() => {
    fetchBrand()
  }, [fetchBrand])

  // Handle logo upload
  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setSubmitError('Logo must be less than 5MB')
      return
    }

    // Validate file type (PNG, JPEG, WebP)
    if (!file.type.match(/^image\/(png|jpeg|jpg|webp)$/i)) {
      setSubmitError('Logo must be PNG, JPEG, or WebP format')
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const preview = e.target?.result as string
      setLogoFile(file)
      setLogoPreview(preview)
    }
    reader.readAsDataURL(file)
    setSubmitError(null)
  }

  // Handle guidelines upload
  const handleGuidelinesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setSubmitError('Guidelines file must be less than 10MB')
      return
    }

    // Validate file type (PDF or DOCX)
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
    ]
    if (!validTypes.includes(file.type)) {
      setSubmitError('Guidelines must be PDF or DOCX format')
      return
    }

    setGuidelinesFile(file)
    setSubmitError(null)
  }

  // Remove logo
  const removeLogo = () => {
    setLogoFile(null)
    setLogoPreview('')
  }

  // Remove guidelines
  const removeGuidelines = () => {
    setGuidelinesFile(null)
  }

  // Validate form
  const validateForm = (): boolean => {
    if (!brandName.trim() || brandName.length < 2 || brandName.length > 100) {
      setSubmitError('Brand name must be between 2 and 100 characters')
      return false
    }

    if (!logoFile) {
      setSubmitError('Please upload a logo')
      return false
    }

    if (!guidelinesFile) {
      setSubmitError('Please upload brand guidelines')
      return false
    }

    return true
  }

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    e.stopPropagation() // Prevent any event bubbling that might cause issues
    setSubmitError(null)

    if (!validateForm()) {
      return false
    }

    if (!logoFile || !guidelinesFile) {
      setSubmitError('Please upload both logo and guidelines')
      return false
    }

    // Prevent multiple submissions
    if (isNavigatingRef.current || isSubmitting) {
      return false
    }

    setIsSubmitting(true)
    isNavigatingRef.current = true // Set flag to prevent useEffect navigation

    try {
      // onboardBrand will update the brand state via setBrand(response.data)
      const updatedBrand = await onboardBrand(brandName, logoFile, guidelinesFile)

      // Verify the brand was created successfully
      if (!updatedBrand || !updatedBrand.id) {
        throw new Error('Onboarding was not completed successfully')
      }

      // Force a brand fetch to ensure state is synced
      await fetchBrand()

      // Use window.location.href to force a full page reload
      // This ensures all components (including ProtectedRoute) see the fresh brand state
      // This prevents navigation loops caused by stale state
      window.location.href = '/dashboard'
    } catch (err: any) {
      // Reset navigation flag on error
      isNavigatingRef.current = false

      // Handle 409 Conflict - brand already exists
      if (err?.response?.status === 409) {
        // Brand was already created, fetchBrand will be called by onboardBrand
        // Fetch brand again to ensure state is updated
        await fetchBrand()
        // Use window.location.href to force a full page reload
        // This ensures all components see the fresh brand state
        window.location.href = '/dashboard'
      } else {
        setSubmitError(err.message || 'Failed to complete onboarding. Please try again.')
        setIsSubmitting(false)
      }
    }

    return false // Prevent any default form submission
  }

  // Handle continuing with existing brand
  const handleContinueWithBrand = () => {
    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen bg-gradient-light">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-100/40 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-50/30 rounded-full blur-3xl"></div>
      </div>

      {/* Navigation Header */}
      <nav className="relative z-50 border-b border-gray-200 backdrop-blur-md bg-white/80 sticky top-0">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2">
              <div className="p-2 bg-primary-500 rounded-lg shadow-md">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">GenAds</span>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSignOut}
              className="text-gray-600 hover:text-gray-900 hover:bg-gray-100"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Sign Out
            </Button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-2xl mx-auto"
          >
            {/* Header */}
            <div className="text-center mb-8">
              <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3">
                Welcome to <span className="text-primary-500">GenAds</span>
              </h1>
              <p className="text-lg text-gray-600">
                {brand ? 'Continue with your existing brand or create a new one' : "Let's set up your brand to get started"}
              </p>
            </div>

            {/* Existing Brand Card (if brand exists) */}
            {brand && !showCreateForm && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
                className="bg-white border-2 border-primary-500 rounded-xl p-6 sm:p-8 mb-6 shadow-lg"
              >
                <div className="flex items-start gap-4 mb-6">
                  <div className="flex-shrink-0">
                    {getBrandLogoUrl(brand) ? (
                      <img
                        src={getBrandLogoUrl(brand)!}
                        alt={brand.brand_name || brand.company_name}
                        className="w-16 h-16 rounded-lg object-contain border-2 border-gray-200"
                      />
                    ) : (
                      <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center">
                        <Building2 className="w-8 h-8 text-gray-400" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-gray-900 mb-1">{brand.brand_name || brand.company_name}</h3>
                    <p className="text-sm text-gray-600">Existing Brand</p>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-3">
                  <Button
                    variant="hero"
                    onClick={handleContinueWithBrand}
                    fullWidth
                    className="gap-2"
                  >
                    Continue with {brand.brand_name || brand.company_name}
                    <ArrowRight className="w-5 h-5" />
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setShowCreateForm(true)}
                    className="sm:w-auto border-gray-300 text-gray-700 hover:bg-gray-50"
                  >
                    Create New Brand
                  </Button>
                </div>
              </motion.div>
            )}

            {/* Onboarding Form (shown if no brand or user wants to create new) */}
            {(!brand || showCreateForm) && (
              <motion.form
                onSubmit={handleSubmit}
                className="bg-white border border-gray-200 rounded-xl p-6 sm:p-8 space-y-6 shadow-lg"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, delay: brand ? 0.2 : 0.1 }}
              >
                {showCreateForm && (
                  <div className="flex items-center justify-between pb-4 border-b border-gray-200">
                    <h3 className="text-lg font-semibold text-gray-900">Create New Brand</h3>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowCreateForm(false)}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      <X className="w-5 h-5" />
                    </Button>
                  </div>
                )}

                {/* Brand Name */}
                <div>
                  <Input
                    label="Brand Name"
                    type="text"
                    value={brandName}
                    onChange={(e) => setBrandName(e.target.value)}
                    placeholder="e.g., Chanel, Dior, Tom Ford"
                    required
                    className="bg-gray-50 border-gray-300 text-gray-900"
                  />
                </div>

                {/* Logo Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Brand Logo <span className="text-red-500">*</span>
                  </label>
                  {logoPreview ? (
                    <div className="relative inline-block">
                      <div className="w-32 h-32 rounded-lg border-2 border-primary-500 overflow-hidden bg-gray-50">
                        <img
                          src={logoPreview}
                          alt="Logo preview"
                          className="w-full h-full object-contain"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={removeLogo}
                        className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full text-white hover:bg-red-600 transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary-500 transition-colors bg-gray-50">
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <ImageIcon className="w-8 h-8 mb-2 text-gray-400 group-hover:text-primary-500 transition-colors" />
                        <p className="mb-2 text-sm text-gray-600">
                          <span className="font-semibold">Click to upload</span> or drag and drop
                        </p>
                        <p className="text-xs text-gray-500">PNG, JPEG, or WebP (MAX. 5MB)</p>
                      </div>
                      <input
                        type="file"
                        className="hidden"
                        accept="image/png,image/jpeg,image/jpg,image/webp"
                        onChange={handleLogoChange}
                      />
                    </label>
                  )}
                </div>

                {/* Guidelines Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Brand Guidelines <span className="text-red-500">*</span>
                  </label>
                  {guidelinesFile ? (
                    <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg border border-primary-500">
                      <FileText className="w-5 h-5 text-primary-500 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {guidelinesFile.name}
                        </p>
                        <p className="text-xs text-gray-600">
                          {(guidelinesFile.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={removeGuidelines}
                        className="p-1 text-gray-500 hover:text-red-500 transition-colors"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                  ) : (
                    <label className="flex items-center justify-center w-full p-4 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary-500 transition-colors bg-gray-50">
                      <div className="flex items-center gap-3">
                        <UploadCloud className="w-5 h-5 text-gray-400 group-hover:text-primary-500 transition-colors flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-600">
                            <span className="font-semibold">Click to upload</span> or drag and drop
                          </p>
                          <p className="text-xs text-gray-500">PDF or DOCX (MAX. 10MB)</p>
                        </div>
                      </div>
                      <input
                        type="file"
                        className="hidden"
                        accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        onChange={handleGuidelinesChange}
                      />
                    </label>
                  )}
                  <p className="text-xs text-gray-500 mt-2">
                    Upload your brand guidelines document (PDF or DOCX) containing colors, fonts, tone, and style guidelines
                  </p>
                </div>

                {/* Error Message */}
                {(error || submitError) && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-600">{error || submitError}</p>
                  </div>
                )}

                {/* Submit Button */}
                <Button
                  type="submit"
                  variant="hero"
                  size="lg"
                  fullWidth
                  disabled={loading || isSubmitting}
                  className="gap-2"
                >
                  {loading || isSubmitting ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Completing Onboarding...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-5 h-5" />
                      Complete Onboarding
                    </>
                  )}
                </Button>
              </motion.form>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
