import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { Input } from '@/components/ui'
import { useProducts, type ProductGender } from '@/hooks/useProducts'
import { useAuth } from '@/hooks/useAuth'
import { Image as ImageIcon, X, CheckCircle, Sparkles, LogOut, ArrowLeft, Check } from 'lucide-react'
import { Link } from 'react-router-dom'

export const AddProduct = () => {
  const navigate = useNavigate()
  const { createProduct, loading, error } = useProducts()
  const { logout } = useAuth()

  const [productName, setProductName] = useState('')
  const [productGender, setProductGender] = useState<ProductGender>('unisex')
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
    if (!productName.trim() || productName.length < 2 || productName.length > 200) {
      setSubmitError('Product name must be between 2 and 200 characters')
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
      await createProduct({
        product_name: productName,
        product_gender: productGender,
        front_image: frontImage,
        back_image: backImage || undefined,
        top_image: topImage || undefined,
        left_image: leftImage || undefined,
        right_image: rightImage || undefined,
      })
      // Redirect to dashboard on success
      navigate('/dashboard')
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to create product. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
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
            <Link to="/dashboard" className="flex items-center gap-2">
              <ArrowLeft className="w-5 h-5 text-gray-600 hover:text-primary-600 transition-colors" />
              <span className="text-gray-600 hover:text-primary-600 transition-colors">Back to Dashboard</span>
            </Link>
            <div className="flex items-center gap-4">
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
                Add New <span className="text-primary-600">Product</span>
              </h1>
              <p className="text-lg text-gray-600">
                Add a new product to your brand collection
              </p>
            </div>

            {/* Add Product Form */}
            <motion.form
              onSubmit={handleSubmit}
              className="bg-white backdrop-blur-sm border border-gray-200 rounded-xl p-6 sm:p-8 space-y-6 shadow-lg"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              {/* Product Name */}
              <div>
                <Input
                  label="Product Name"
                  type="text"
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  placeholder="e.g., Sauvage, Bleu de Chanel, Black Opium"
                  required
                  helpText="This will be used to identify your product"
                  className="bg-white border-gray-300 text-gray-900"
                />
              </div>

              {/* Product Gender */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Product Gender <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-3">
                  {(['masculine', 'feminine', 'unisex'] as ProductGender[]).map((gender) => {
                    const isSelected = productGender === gender
                    return (
                    <button
                      key={gender}
                      type="button"
                      onClick={() => setProductGender(gender)}
                        className={`flex-1 px-4 py-3 rounded-lg border-2 transition-all duration-200 flex items-center justify-center gap-2 ${
                          isSelected
                            ? 'border-primary-500 bg-primary-50 text-primary-700 font-semibold shadow-md ring-2 ring-primary-200 scale-105'
                            : 'border-gray-300 bg-white text-gray-600 hover:border-primary-300 hover:text-gray-900 hover:bg-gray-50'
                      }`}
                    >
                        {isSelected && <Check className="w-4 h-4" />}
                        <span className="capitalize">{gender}</span>
                    </button>
                    )
                  })}
                </div>
              </div>

              {/* Front Image (Required) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Front Image <span className="text-red-500">*</span>
                </label>
                {frontPreview ? (
                  <div className="relative inline-block">
                    <div className="w-32 h-32 rounded-lg border-2 border-primary-500 overflow-hidden bg-white">
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
                  <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary-400 transition-colors bg-gray-50 group">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <ImageIcon className="w-8 h-8 mb-2 text-gray-400 group-hover:text-primary-600 transition-colors" />
                      <p className="mb-2 text-sm text-gray-600">
                        <span className="font-semibold">Click to upload</span> front image
                      </p>
                      <p className="text-xs text-gray-500">PNG, JPEG, or WebP (MAX. 5MB)</p>
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

              {/* Optional Images 
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Additional Images <span className="text-xs text-muted-gray">(Optional)</span>
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {/* Back Image 
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

                  {/* Top Image 
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

                  {/* Left Image 
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

                  {/* Right Image 
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
              </div>*/}

              {/* Error Message */}
              {(error || submitError) && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{error || submitError}</p>
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
                  variant="default"
                  size="lg"
                  className="flex-1 gap-2"
                  disabled={loading || isSubmitting}
                >
                  {loading || isSubmitting ? (
                    <>
                      <div className="w-5 h-5 border-2 border-gold-foreground border-t-transparent rounded-full animate-spin" />
                      Creating Product...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-5 h-5" />
                      Create Product
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

