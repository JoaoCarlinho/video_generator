import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { Input } from '@/components/ui'
import { usePerfumes, type PerfumeGender } from '@/hooks/usePerfumes'
import { useAuth } from '@/hooks/useAuth'
import { Image as ImageIcon, X, CheckCircle, Sparkles, LogOut, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

export const AddPerfume = () => {
  const navigate = useNavigate()
  const { createPerfume, loading, error } = usePerfumes()
  const { logout } = useAuth()

  const [perfumeName, setPerfumeName] = useState('')
  const [perfumeGender, setPerfumeGender] = useState<PerfumeGender>('unisex')
  const [frontImage, setFrontImage] = useState<File | null>(null)
  const [frontPreview, setFrontPreview] = useState<string>('')
  const [backImage, setBackImage] = useState<File | null>(null)
  const [backPreview, setBackPreview] = useState<string>('')
  const [topImage, setTopImage] = useState<File | null>(null)
  const [topPreview, setTopPreview] = useState<string>('')
  const [leftImage, setLeftImage] = useState<File | null>(null)
  const [leftPreview, setLeftPreview] = useState<string>('')
  const [rightImage, setRightImage] = useState<File | null>(null)
  const [rightPreview, setRightPreview] = useState<string>('')
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSignOut = async () => {
    try {
      await logout()
      navigate('/login')
    } catch (err) {
      console.error('Error signing out:', err)
    }
  }

  // Handle image uploads
  const handleImageChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    setImage: (file: File | null) => void,
    setPreview: (preview: string) => void,
    angle: string
  ) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setSubmitError(`${angle} image must be less than 5MB`)
      return
    }

    // Validate file type (PNG, JPEG, WebP)
    if (!file.type.match(/^image\/(png|jpeg|jpg|webp)$/i)) {
      setSubmitError(`${angle} image must be PNG, JPEG, or WebP format`)
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const preview = e.target?.result as string
      setImage(file)
      setPreview(preview)
    }
    reader.readAsDataURL(file)
    setSubmitError(null)
  }

  const removeImage = (
    setImage: (file: File | null) => void,
    setPreview: (preview: string) => void
  ) => {
    setImage(null)
    setPreview('')
  }

  // Validate form
  const validateForm = (): boolean => {
    if (!perfumeName.trim() || perfumeName.length < 2 || perfumeName.length > 200) {
      setSubmitError('Perfume name must be between 2 and 200 characters')
      return false
    }

    if (!frontImage) {
      setSubmitError('Please upload a front image (required)')
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

    if (!frontImage) {
      setSubmitError('Please upload a front image')
      return
    }

    setIsSubmitting(true)

    try {
      await createPerfume({
        perfume_name: perfumeName,
        perfume_gender: perfumeGender,
        front_image: frontImage,
        back_image: backImage || undefined,
        top_image: topImage || undefined,
        left_image: leftImage || undefined,
        right_image: rightImage || undefined,
      })
      // Redirect to dashboard on success
      navigate('/dashboard')
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to create perfume. Please try again.')
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
            <Link to="/dashboard" className="flex items-center gap-2">
              <ArrowLeft className="w-5 h-5 text-muted-gray hover:text-gold transition-colors" />
              <span className="text-muted-gray hover:text-gold transition-colors">Back to Dashboard</span>
            </Link>
            <div className="flex items-center gap-4">
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
                Add New <span className="text-gradient-gold">Perfume</span>
              </h1>
              <p className="text-lg text-muted-gray">
                Add a new perfume to your brand collection
              </p>
            </div>

            {/* Add Perfume Form */}
            <motion.form
              onSubmit={handleSubmit}
              className="bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-xl p-6 sm:p-8 space-y-6"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              {/* Perfume Name */}
              <div>
                <Input
                  label="Perfume Name"
                  type="text"
                  value={perfumeName}
                  onChange={(e) => setPerfumeName(e.target.value)}
                  placeholder="e.g., Sauvage, Bleu de Chanel, Black Opium"
                  required
                  helpText="This will be used to identify your perfume"
                  className="bg-slate-800 border-slate-700 text-off-white"
                />
              </div>

              {/* Perfume Gender */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Perfume Gender <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-3">
                  {(['masculine', 'feminine', 'unisex'] as PerfumeGender[]).map((gender) => (
                    <button
                      key={gender}
                      type="button"
                      onClick={() => setPerfumeGender(gender)}
                      className={`flex-1 px-4 py-3 rounded-lg border-2 transition-all ${
                        perfumeGender === gender
                          ? 'border-gold bg-gold/10 text-gold'
                          : 'border-olive-600 bg-slate-800/50 text-muted-gray hover:border-olive-500 hover:text-off-white'
                      }`}
                    >
                      <span className="capitalize font-medium">{gender}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Front Image (Required) */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Front Image <span className="text-red-500">*</span>
                </label>
                {frontPreview ? (
                  <div className="relative inline-block">
                    <div className="w-32 h-32 rounded-lg border-2 border-gold overflow-hidden bg-slate-800">
                      <img
                        src={frontPreview}
                        alt="Front preview"
                        className="w-full h-full object-contain"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => removeImage(setFrontImage, setFrontPreview)}
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
                        <span className="font-semibold">Click to upload</span> front image
                      </p>
                      <p className="text-xs text-muted-gray">PNG, JPEG, or WebP (MAX. 5MB)</p>
                    </div>
                    <input
                      type="file"
                      className="hidden"
                      accept="image/png,image/jpeg,image/jpg,image/webp"
                      onChange={(e) => handleImageChange(e, setFrontImage, setFrontPreview, 'Front')}
                      required
                    />
                  </label>
                )}
              </div>

              {/* Optional Images */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Additional Images <span className="text-xs text-muted-gray">(Optional)</span>
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {/* Back Image */}
                  <div>
                    <label className="block text-xs text-muted-gray mb-2">Back</label>
                    {backPreview ? (
                      <div className="relative">
                        <div className="w-full aspect-square rounded-lg border-2 border-olive-600 overflow-hidden bg-slate-800">
                          <img
                            src={backPreview}
                            alt="Back preview"
                            className="w-full h-full object-contain"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => removeImage(setBackImage, setBackPreview)}
                          className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full text-white hover:bg-red-600 transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center w-full aspect-square border-2 border-dashed border-olive-600 rounded-lg cursor-pointer hover:border-gold transition-colors bg-slate-800/50">
                        <ImageIcon className="w-6 h-6 mb-1 text-muted-gray" />
                        <input
                          type="file"
                          className="hidden"
                          accept="image/png,image/jpeg,image/jpg,image/webp"
                          onChange={(e) => handleImageChange(e, setBackImage, setBackPreview, 'Back')}
                        />
                      </label>
                    )}
                  </div>

                  {/* Top Image */}
                  <div>
                    <label className="block text-xs text-muted-gray mb-2">Top</label>
                    {topPreview ? (
                      <div className="relative">
                        <div className="w-full aspect-square rounded-lg border-2 border-olive-600 overflow-hidden bg-slate-800">
                          <img
                            src={topPreview}
                            alt="Top preview"
                            className="w-full h-full object-contain"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => removeImage(setTopImage, setTopPreview)}
                          className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full text-white hover:bg-red-600 transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center w-full aspect-square border-2 border-dashed border-olive-600 rounded-lg cursor-pointer hover:border-gold transition-colors bg-slate-800/50">
                        <ImageIcon className="w-6 h-6 mb-1 text-muted-gray" />
                        <input
                          type="file"
                          className="hidden"
                          accept="image/png,image/jpeg,image/jpg,image/webp"
                          onChange={(e) => handleImageChange(e, setTopImage, setTopPreview, 'Top')}
                        />
                      </label>
                    )}
                  </div>

                  {/* Left Image */}
                  <div>
                    <label className="block text-xs text-muted-gray mb-2">Left</label>
                    {leftPreview ? (
                      <div className="relative">
                        <div className="w-full aspect-square rounded-lg border-2 border-olive-600 overflow-hidden bg-slate-800">
                          <img
                            src={leftPreview}
                            alt="Left preview"
                            className="w-full h-full object-contain"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => removeImage(setLeftImage, setLeftPreview)}
                          className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full text-white hover:bg-red-600 transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center w-full aspect-square border-2 border-dashed border-olive-600 rounded-lg cursor-pointer hover:border-gold transition-colors bg-slate-800/50">
                        <ImageIcon className="w-6 h-6 mb-1 text-muted-gray" />
                        <input
                          type="file"
                          className="hidden"
                          accept="image/png,image/jpeg,image/jpg,image/webp"
                          onChange={(e) => handleImageChange(e, setLeftImage, setLeftPreview, 'Left')}
                        />
                      </label>
                    )}
                  </div>

                  {/* Right Image */}
                  <div>
                    <label className="block text-xs text-muted-gray mb-2">Right</label>
                    {rightPreview ? (
                      <div className="relative">
                        <div className="w-full aspect-square rounded-lg border-2 border-olive-600 overflow-hidden bg-slate-800">
                          <img
                            src={rightPreview}
                            alt="Right preview"
                            className="w-full h-full object-contain"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => removeImage(setRightImage, setRightPreview)}
                          className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full text-white hover:bg-red-600 transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center w-full aspect-square border-2 border-dashed border-olive-600 rounded-lg cursor-pointer hover:border-gold transition-colors bg-slate-800/50">
                        <ImageIcon className="w-6 h-6 mb-1 text-muted-gray" />
                        <input
                          type="file"
                          className="hidden"
                          accept="image/png,image/jpeg,image/jpg,image/webp"
                          onChange={(e) => handleImageChange(e, setRightImage, setRightPreview, 'Right')}
                        />
                      </label>
                    )}
                  </div>
                </div>
                <p className="text-xs text-muted-gray mt-2">
                  Upload additional angles to improve video generation quality (optional)
                </p>
              </div>

              {/* Error Message */}
              {(error || submitError) && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <p className="text-sm text-red-400">{error || submitError}</p>
                </div>
              )}

              {/* Submit Button */}
              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => navigate('/dashboard')}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="hero"
                  size="lg"
                  className="flex-1 gap-2"
                  disabled={loading || isSubmitting}
                >
                  {loading || isSubmitting ? (
                    <>
                      <div className="w-5 h-5 border-2 border-gold-foreground border-t-transparent rounded-full animate-spin" />
                      Creating Perfume...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-5 h-5" />
                      Create Perfume
                    </>
                  )}
                </Button>
              </div>
            </motion.form>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

