import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { Input } from '@/components/ui'
import { useCampaigns, type VideoStyle } from '@/hooks/useCampaigns'
import { usePerfumes } from '@/hooks/usePerfumes'
import { useAuth } from '@/hooks/useAuth'
import { ArrowLeft, Sparkles, LogOut, CheckCircle, Clock, Sparkles as SparklesIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Slider } from '@/components/ui/slider'

export const CreateCampaign = () => {
  const { perfumeId } = useParams<{ perfumeId: string }>()
  const navigate = useNavigate()
  const { createCampaign, loading, error } = useCampaigns()
  const { getPerfume } = usePerfumes()
  const { logout } = useAuth()

  const [perfume, setPerfume] = useState<any>(null)
  const [campaignName, setCampaignName] = useState('')
  const [creativePrompt, setCreativePrompt] = useState('')
  const [selectedStyle, setSelectedStyle] = useState<VideoStyle>('gold_luxe')
  const [targetDuration, setTargetDuration] = useState(30)
  const [numVariations, setNumVariations] = useState<1 | 2 | 3>(1)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (perfumeId) {
      getPerfume(perfumeId)
        .then(setPerfume)
        .catch((err) => {
          console.error('Error fetching perfume:', err)
        })
    }
  }, [perfumeId, getPerfume])

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
    if (!campaignName.trim() || campaignName.length < 2 || campaignName.length > 200) {
      setSubmitError('Campaign name must be between 2 and 200 characters')
      return false
    }

    if (!creativePrompt.trim() || creativePrompt.length < 10 || creativePrompt.length > 2000) {
      setSubmitError('Creative prompt must be between 10 and 2000 characters')
      return false
    }

    if (!perfumeId) {
      setSubmitError('Perfume ID is missing')
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

    if (!perfumeId) {
      setSubmitError('Perfume ID is missing')
      return
    }

    setIsSubmitting(true)

    try {
      const campaign = await createCampaign({
        perfume_id: perfumeId,
        campaign_name: campaignName,
        creative_prompt: creativePrompt,
        selected_style: selectedStyle,
        target_duration: targetDuration,
        num_variations: numVariations,
      })
      
      // Redirect to campaign progress page
      navigate(`/campaigns/${campaign.campaign_id}/progress`)
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to create campaign. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const styleOptions: { value: VideoStyle; label: string; description: string }[] = [
    {
      value: 'gold_luxe',
      label: 'Gold Luxe',
      description: 'Luxurious golden tones, elegant and sophisticated',
    },
    {
      value: 'dark_elegance',
      label: 'Dark Elegance',
      description: 'Mysterious dark aesthetic with dramatic lighting',
    },
    {
      value: 'romantic_floral',
      label: 'Romantic Floral',
      description: 'Soft, romantic tones with floral elegance',
    },
  ]

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
            <Link
              to={perfumeId ? `/perfumes/${perfumeId}` : '/dashboard'}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-5 h-5 text-muted-gray hover:text-gold transition-colors" />
              <span className="text-muted-gray hover:text-gold transition-colors">
                {perfume ? `Back to ${perfume.perfume_name}` : 'Back'}
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
              {perfume && (
                <p className="text-lg text-muted-gray">
                  For <span className="text-gold font-semibold">{perfume.perfume_name}</span>
                </p>
              )}
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
                  helpText="Give your campaign a memorable name"
                  className="bg-slate-800 border-slate-700 text-off-white"
                />
              </div>

              {/* Creative Prompt */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Creative Prompt <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={creativePrompt}
                  onChange={(e) => setCreativePrompt(e.target.value)}
                  placeholder="Describe the vision for your ad campaign. What mood, atmosphere, or story should the video convey? (10-2000 characters)"
                  required
                  rows={6}
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-off-white placeholder-muted-gray focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent resize-none"
                />
                <p className="text-xs text-muted-gray mt-1">
                  {creativePrompt.length} / 2000 characters
                </p>
              </div>

              {/* Video Style */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Video Style <span className="text-red-500">*</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {styleOptions.map((style) => (
                    <button
                      key={style.value}
                      type="button"
                      onClick={() => setSelectedStyle(style.value)}
                      className={`p-4 rounded-lg border-2 transition-all text-left ${
                        selectedStyle === style.value
                          ? 'border-gold bg-gold/10 text-gold'
                          : 'border-olive-600 bg-slate-800/50 text-muted-gray hover:border-olive-500 hover:text-off-white'
                      }`}
                    >
                      <h3 className="font-semibold mb-1 capitalize">{style.label}</h3>
                      <p className="text-xs opacity-80">{style.description}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Target Duration */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Target Duration: <span className="text-gold font-semibold">{targetDuration}s</span>
                </label>
                <div className="px-2">
                  <Slider
                    value={[targetDuration]}
                    onValueChange={(value) => setTargetDuration(value[0])}
                    min={15}
                    max={60}
                    step={5}
                    className="w-full"
                  />
                </div>
                <div className="flex justify-between text-xs text-muted-gray mt-2">
                  <span>15s</span>
                  <span>30s</span>
                  <span>45s</span>
                  <span>60s</span>
                </div>
                <p className="text-xs text-muted-gray mt-2">
                  TikTok videos work best between 15-60 seconds
                </p>
              </div>

              {/* Number of Variations */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Number of Variations <span className="text-xs text-muted-gray">(Optional)</span>
                </label>
                <div className="flex gap-3">
                  {([1, 2, 3] as const).map((num) => (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setNumVariations(num)}
                      className={`flex-1 px-4 py-3 rounded-lg border-2 transition-all ${
                        numVariations === num
                          ? 'border-gold bg-gold/10 text-gold'
                          : 'border-olive-600 bg-slate-800/50 text-muted-gray hover:border-olive-500 hover:text-off-white'
                      }`}
                    >
                      <div className="flex items-center justify-center gap-2">
                        <SparklesIcon className="w-4 h-4" />
                        <span className="font-medium">{num}</span>
                      </div>
                      <p className="text-xs mt-1 opacity-80">
                        {num === 1 ? 'Single video' : `${num} variations`}
                      </p>
                    </button>
                  ))}
                </div>
                <p className="text-xs text-muted-gray mt-2">
                  Generate multiple variations to choose your favorite (all variations process in parallel)
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
                  onClick={() => navigate(perfumeId ? `/perfumes/${perfumeId}` : '/dashboard')}
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

