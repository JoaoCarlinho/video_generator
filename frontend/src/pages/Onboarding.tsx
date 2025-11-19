import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { Input } from '@/components/ui'
import { useBrand } from '@/hooks/useBrand'
import { useAuth } from '@/hooks/useAuth'
import { UploadCloud, FileText, Image as ImageIcon, X, CheckCircle, Sparkles, LogOut } from 'lucide-react'
import { Link } from 'react-router-dom'

export const Onboarding = () => {
  const navigate = useNavigate()
  const { onboardBrand, loading, error, brand } = useBrand()
  const { logout } = useAuth()

  const handleSignOut = async () => {
    try {
      await logout()
      navigate('/login')
    } catch (err) {
      console.error('Error signing out:', err)
    }
  }

  // Check if user already has a brand and redirect
  useEffect(() => {
    if (brand && brand.onboarding_completed) {
      // User already completed onboarding, redirect to dashboard
      navigate('/dashboard', { replace: true })
    }
  }, [brand, navigate])

  const [brandName, setBrandName] = useState('')
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string>('')
  const [guidelinesFile, setGuidelinesFile] = useState<File | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

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
    setSubmitError(null)

    if (!validateForm()) {
      return
    }

    if (!logoFile || !guidelinesFile) {
      setSubmitError('Please upload both logo and guidelines')
      return
    }

    setIsSubmitting(true)

    try {
      await onboardBrand(brandName, logoFile, guidelinesFile)
      // Refresh brand data and redirect to dashboard on success
      // Small delay to ensure brand data is synced
      setTimeout(() => {
        navigate('/dashboard')
      }, 500)
    } catch (err: any) {
      // Handle 409 Conflict - brand already exists
      if (err?.response?.status === 409) {
        // Brand was already created, just redirect to dashboard
        setSubmitError('Brand already exists. Redirecting to dashboard...')
        setTimeout(() => {
          navigate('/dashboard')
        }, 1500)
      } else {
        setSubmitError(err.message || 'Failed to complete onboarding. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
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
            <Link to="/" className="flex items-center gap-2">
              <div className="p-2 bg-gold rounded-lg shadow-gold">
                <Sparkles className="h-5 w-5 text-gold-foreground" />
              </div>
              <span className="text-xl font-bold text-gradient-gold">GenAds</span>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSignOut}
              className="text-muted-gray hover:text-off-white hover:bg-olive-800/50"
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
              <h1 className="text-3xl sm:text-4xl font-bold text-off-white mb-3">
                Welcome to <span className="text-gradient-gold">GenAds</span>
              </h1>
              <p className="text-lg text-muted-gray">
                Let's set up your brand to get started
              </p>
            </div>

            {/* Onboarding Form */}
            <motion.form
              onSubmit={handleSubmit}
              className="bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-xl p-6 sm:p-8 space-y-6"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              {/* Brand Name */}
              <div>
                <Input
                  label="Brand Name"
                  type="text"
                  value={brandName}
                  onChange={(e) => setBrandName(e.target.value)}
                  placeholder="e.g., Chanel, Dior, Tom Ford"
                  required
                  helpText="This will be used across all your campaigns"
                  className="bg-slate-800 border-slate-700 text-off-white"
                />
              </div>

              {/* Logo Upload */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Brand Logo <span className="text-red-500">*</span>
                </label>
                {logoPreview ? (
                  <div className="relative inline-block">
                    <div className="w-32 h-32 rounded-lg border-2 border-gold overflow-hidden bg-slate-800">
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
                  <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-olive-600 rounded-lg cursor-pointer hover:border-gold transition-colors bg-slate-800/50">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <ImageIcon className="w-8 h-8 mb-2 text-muted-gray group-hover:text-gold transition-colors" />
                      <p className="mb-2 text-sm text-muted-gray">
                        <span className="font-semibold">Click to upload</span> or drag and drop
                      </p>
                      <p className="text-xs text-muted-gray">PNG, JPEG, or WebP (MAX. 5MB)</p>
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
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Brand Guidelines <span className="text-red-500">*</span>
                </label>
                {guidelinesFile ? (
                  <div className="flex items-center gap-3 p-4 bg-slate-800 rounded-lg border border-gold">
                    <FileText className="w-5 h-5 text-gold flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-off-white truncate">
                        {guidelinesFile.name}
                      </p>
                      <p className="text-xs text-muted-gray">
                        {(guidelinesFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={removeGuidelines}
                      className="p-1 text-muted-gray hover:text-red-400 transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-olive-600 rounded-lg cursor-pointer hover:border-gold transition-colors bg-slate-800/50">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <UploadCloud className="w-8 h-8 mb-2 text-muted-gray group-hover:text-gold transition-colors" />
                      <p className="mb-2 text-sm text-muted-gray">
                        <span className="font-semibold">Click to upload</span> or drag and drop
                      </p>
                      <p className="text-xs text-muted-gray">PDF or DOCX (MAX. 10MB)</p>
                    </div>
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                      onChange={handleGuidelinesChange}
                    />
                  </label>
                )}
                <p className="text-xs text-muted-gray mt-2">
                  Upload your brand guidelines document (PDF or DOCX) containing colors, fonts, tone, and style guidelines
                </p>
              </div>

              {/* Error Message */}
              {(error || submitError) && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <p className="text-sm text-red-400">{error || submitError}</p>
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
                    <div className="w-5 h-5 border-2 border-gold-foreground border-t-transparent rounded-full animate-spin" />
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
          </motion.div>
        </div>
      </div>
    </div>
  )
}

