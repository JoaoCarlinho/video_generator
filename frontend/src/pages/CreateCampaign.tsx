import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { Input } from '@/components/ui'
import { useCampaigns } from '@/hooks/useCampaigns'
import { useProducts } from '@/hooks/useProducts'
import { useAuth } from '@/hooks/useAuth'
import { ArrowLeft, Sparkles, LogOut, CheckCircle } from 'lucide-react'
import { Link } from 'react-router-dom'

export const CreateCampaign = () => {
  const { productId } = useParams<{ productId: string }>()
  const navigate = useNavigate()
  const { createCampaign, loading, error } = useCampaigns()
  const { getProduct } = useProducts()
  const { logout } = useAuth()

  const [product, setProduct] = useState<any>(null)
  const [campaignName, setCampaignName] = useState('')
  const [seasonalEvent, setSeasonalEvent] = useState('')
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Predefined seasonal events
  const seasonalEventOptions = [
    'New Year Sale',
    'Valentine\'s Day',
    'Spring Collection',
    'Easter Sale',
    'Mother\'s Day',
    'Memorial Day Sale',
    'Summer Launch',
    'Father\'s Day',
    'Independence Day Sale',
    'Back to School',
    'Labor Day Sale',
    'Fall Collection',
    'Halloween Special',
    'Black Friday',
    'Cyber Monday',
    'Holiday Season',
    'Christmas Sale',
    'Year End Clearance',
    'Product Launch',
    'Brand Anniversary',
    'Flash Sale',
    'Exclusive Drop',
    'General Campaign'
  ]

  useEffect(() => {
    if (productId) {
      getProduct(productId)
        .then(setProduct)
        .catch((err) => {
          console.error('Error fetching product:', err)
        })
    }
  }, [productId, getProduct])

  const handleSignOut = async () => {
    try {
      await logout()
      navigate('/login')
    } catch (err) {
      console.error('Error signing out:', err)
    }
  }

  // Validate form
  const validateForm = (): boolean => {
    if (!campaignName.trim() || campaignName.length < 2 || campaignName.length > 100) {
      setSubmitError('Campaign name must be between 2 and 100 characters')
      return false
    }

    if (!seasonalEvent.trim()) {
      setSubmitError('Please select a season or event')
      return false
    }

    if (!productId) {
      setSubmitError('Product ID is missing')
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

    if (!productId) {
      setSubmitError('Product ID is missing')
      return
    }

    setIsSubmitting(true)

    try {
      const currentYear = new Date().getFullYear()

      // Create campaign - video-specific details defined per-creative
      const campaign = await createCampaign({
        product_id: productId,
        campaign_name: campaignName,
        seasonal_event: seasonalEvent,
        year: currentYear
      })

      // Redirect to campaign's creatives page to add creatives
      navigate(`/campaigns/${campaign.id}/creatives`)
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to create campaign. Please try again.')
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
      <nav className="relative z-50 border-b border-olive-600/50 backdrop-blur-md bg-olive-950/30 sticky top-0">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link
              to={productId ? `/products/${productId}` : '/dashboard'}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-5 h-5 text-muted-gray hover:text-gold transition-colors" />
              <span className="text-muted-gray hover:text-gold transition-colors">
                {product ? `Back to ${product.product_name}` : 'Back'}
              </span>
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
            className="max-w-3xl mx-auto"
          >
            {/* Header */}
            <div className="text-center mb-8">
              <h1 className="text-3xl sm:text-4xl font-bold text-off-white mb-3">
                Create New <span className="text-gradient-gold">Campaign</span>
              </h1>
              <p className="text-muted-gray">
                Campaigns organize your video creatives under a marketing initiative
              </p>
            </div>

            {/* Create Campaign Form */}
            <motion.form
              onSubmit={handleSubmit}
              className="bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-xl p-6 sm:p-8 space-y-6"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              {/* Campaign Name */}
              <div>
                <Input
                  label="Campaign Name"
                  type="text"
                  value={campaignName}
                  onChange={(e) => setCampaignName(e.target.value)}
                  placeholder="e.g., Summer Collection 2024, Holiday Launch"
                  required
                  className="bg-olive-800/30 border-olive-600 text-off-white"
                />
              </div>

              {/* Seasonal Event */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Season / Event <span className="text-red-500">*</span>
                </label>
                <select
                  value={seasonalEvent}
                  onChange={(e) => setSeasonalEvent(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-olive-800/30 border border-olive-600 rounded-lg text-off-white focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent appearance-none cursor-pointer"
                >
                  <option value="" disabled className="bg-olive-900 text-muted-gray">
                    Select a season or event...
                  </option>
                  {seasonalEventOptions.map((event) => (
                    <option key={event} value={event} className="bg-olive-900">
                      {event}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-gray mt-1">
                  Choose the marketing season or event this campaign targets
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
                  onClick={() => navigate(productId ? `/products/${productId}` : '/dashboard')}
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
                      Creating Campaign...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-5 h-5" />
                      Create Campaign
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

