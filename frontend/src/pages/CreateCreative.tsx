import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { Input } from '@/components/ui'
import { useCampaigns, type VideoStyle } from '@/hooks/useCampaigns'
import { useCreatives } from '@/hooks/useCreatives'
import { useAuth } from '@/hooks/useAuth'
import { ArrowLeft, Sparkles, LogOut } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Slider } from '@/components/ui/slider'

export const CreateCreative = () => {
  const { campaignId } = useParams<{ campaignId: string }>()
  const navigate = useNavigate()
  const { createCreative, loading, error } = useCreatives()
  const { getCampaign } = useCampaigns()
  const { logout } = useAuth()

  const [campaign, setCampaign] = useState<any>(null)
  const [creativeTitle, setCreativeTitle] = useState('')
  const [creativePrompt, setCreativePrompt] = useState('')
  const [selectedStyle, setSelectedStyle] = useState<VideoStyle>('gold_luxe')
  const [targetDuration, setTargetDuration] = useState(30)
  const [numVariations, setNumVariations] = useState<1 | 2 | 3>(1)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (campaignId) {
      getCampaign(campaignId)
        .then(setCampaign)
        .catch((err) => {
          console.error('Error fetching campaign:', err)
        })
    }
  }, [campaignId, getCampaign])

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
    if (!creativeTitle.trim() || creativeTitle.length < 2 || creativeTitle.length > 200) {
      setSubmitError('Creative title must be between 2 and 200 characters')
      return false
    }

    if (!creativePrompt.trim() || creativePrompt.length < 10) {
      setSubmitError('Creative prompt must be at least 10 characters')
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

    if (!campaignId || !campaign) {
      setSubmitError('Campaign not found')
      return
    }

    setIsSubmitting(true)

    try {
      // Create the creative with all necessary data
      const creative = await createCreative(campaignId, {
        title: creativeTitle,
        brief: creativePrompt,
        brand_name: campaign.name,
        product_name: campaign.name,
        mood: 'uplifting',
        duration: targetDuration,
        aspect_ratio: '9:16',
        creative_prompt: creativePrompt,
        selected_style: selectedStyle,
        num_variations: numVariations,
        video_provider: 'ecs', // REPLICATE DISABLED - Use ECS only
      })

      // Navigate to the creative's progress page to start generation
      navigate(`/campaigns/${campaignId}/creatives/${creative.id}/progress`)
    } catch (err: any) {
      console.error('Error creating creative:', err)
      setSubmitError(err.message || 'Failed to create creative. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const videoStyles: { value: VideoStyle; label: string; description: string }[] = [
    {
      value: 'gold_luxe',
      label: 'Gold Luxe',
      description: 'Elegant and sophisticated with warm golden tones',
    },
    {
      value: 'silver_modern',
      label: 'Silver Modern',
      description: 'Sleek and contemporary with cool metallic tones',
    },
    {
      value: 'noir_dramatic',
      label: 'Noir Dramatic',
      description: 'Bold and cinematic with high contrast',
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-hero flex flex-col">
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-32 -right-32 w-72 h-72 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-32 -left-32 w-72 h-72 bg-gold-silky/10 rounded-full blur-3xl"></div>
      </div>

      <nav className="relative z-50 border-b border-charcoal-800/60 backdrop-blur-md bg-charcoal-900/40 sticky top-0">
        <div className="max-w-6xl mx-auto w-full px-4 py-4">
          <div className="flex items-center justify-between relative">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => navigate(`/campaigns/${campaignId}/creatives`)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-charcoal-800/60 transition-all duration-200"
              >
                <ArrowLeft className="w-5 h-5 text-off-white" />
                <span className="text-off-white">Back to Creatives</span>
              </button>
            </div>

            <div className="flex items-center gap-4">
              <Link to="/" className="flex items-center gap-2">
                <div className="p-2 bg-gold rounded-lg shadow-gold">
                  <Sparkles className="h-5 w-5 text-gold-foreground" />
                </div>
                <span className="text-xl font-bold text-gradient-gold">GenAds</span>
              </Link>
              <button
                onClick={handleSignOut}
                className="flex items-center gap-2 px-4 py-2 text-sm text-muted-gray hover:text-gold transition-colors rounded-lg hover:bg-charcoal-800/60"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="relative z-10 flex-1 w-full max-w-3xl mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="bg-charcoal-900/60 backdrop-blur-sm rounded-xl p-8 border border-charcoal-800/60">
            <h1 className="text-3xl font-bold text-off-white mb-2">Create New Creative</h1>
            {campaign && (
              <p className="text-muted-gray mb-8">
                For campaign: {campaign.name} - {campaign.seasonal_event} {campaign.year}
              </p>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="creativeTitle" className="block text-sm font-medium text-off-white mb-2">
                  Creative Title *
                </label>
                <Input
                  id="creativeTitle"
                  type="text"
                  value={creativeTitle}
                  onChange={(e) => setCreativeTitle(e.target.value)}
                  placeholder="e.g., Summer Launch Video"
                  className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder:text-gray-400"
                  required
                />
              </div>

              <div>
                <label htmlFor="creativePrompt" className="block text-sm font-medium text-off-white mb-2">
                  Creative Prompt *
                </label>
                <textarea
                  id="creativePrompt"
                  value={creativePrompt}
                  onChange={(e) => setCreativePrompt(e.target.value)}
                  placeholder="Describe your creative vision..."
                  rows={4}
                  className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent resize-none"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-off-white mb-3">
                  Video Style
                </label>
                <div className="grid gap-3">
                  {videoStyles.map((style) => (
                    <button
                      key={style.value}
                      type="button"
                      onClick={() => setSelectedStyle(style.value)}
                      className={`p-4 rounded-lg border-2 transition-all text-left ${
                        selectedStyle === style.value
                          ? 'border-gold bg-gold/10'
                          : 'border-charcoal-700 bg-charcoal-800/40 hover:border-charcoal-600'
                      }`}
                    >
                      <div className="font-semibold text-off-white mb-1">{style.label}</div>
                      <div className="text-sm text-muted-gray">{style.description}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label htmlFor="targetDuration" className="block text-sm font-medium text-off-white mb-3">
                  Target Duration: {targetDuration} seconds
                </label>
                <Slider
                  id="targetDuration"
                  min={15}
                  max={60}
                  step={15}
                  value={[targetDuration]}
                  onValueChange={(value) => setTargetDuration(value[0])}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-gray mt-2">
                  <span>15s</span>
                  <span>30s</span>
                  <span>45s</span>
                  <span>60s</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-off-white mb-3">
                  Number of Variations
                </label>
                <div className="flex gap-3">
                  {[1, 2, 3].map((num) => (
                    <button
                      key={num}
                      type="button"
                      onClick={() => {
                        console.log('🔘 Creative variation button clicked:', num)
                        setNumVariations(num as 1 | 2 | 3)
                      }}
                      className={`flex-1 py-3 rounded-lg border-2 font-semibold transition-all ${
                        numVariations === num
                          ? 'border-gold bg-gold/10 text-gold'
                          : 'border-charcoal-700 bg-charcoal-800/40 text-muted-gray hover:border-charcoal-600'
                      }`}
                    >
                      {num}
                    </button>
                  ))}
                </div>
              </div>

              {submitError && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <p className="text-red-400 text-sm">{submitError}</p>
                </div>
              )}

              <div className="pt-4">
                <Button
                  type="submit"
                  disabled={isSubmitting || loading}
                  className="w-full bg-gold hover:bg-gold/90 text-gold-foreground px-6 py-4 rounded-lg font-semibold text-lg transition-all duration-200 hover:scale-105 shadow-gold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Creating...' : 'Create & Start Generation'}
                </Button>
              </div>
            </form>
          </div>
        </motion.div>
      </main>
    </div>
  )
}
