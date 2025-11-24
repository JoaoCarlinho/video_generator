import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { useAuth } from '@/hooks/useAuth'
import { useCampaigns } from '@/hooks/useCampaigns'
import { useCreatives } from '@/hooks/useCreatives'
import { Plus, ArrowLeft, Sparkles, LogOut, Video, Trash2, Play } from 'lucide-react'
import { Link } from 'react-router-dom'

export const CreativesList = () => {
  const { campaignId } = useParams<{ campaignId: string }>()
  const navigate = useNavigate()
  const { logout } = useAuth()
  const { getCampaign } = useCampaigns()
  const { creatives, loading, error, fetchCreatives, deleteCreative } = useCreatives()
  const [campaign, setCampaign] = useState<any>(null)
  const [isCreatingCreative, setIsCreatingCreative] = useState(false)

  useEffect(() => {
    if (campaignId) {
      // Fetch campaign details
      getCampaign(campaignId)
        .then(setCampaign)
        .catch((err) => {
          console.error('Error fetching campaign:', err)
        })

      // Fetch creatives for this campaign
      fetchCreatives(campaignId)
    }
  }, [campaignId, getCampaign, fetchCreatives])

  const handleCreateCreative = async () => {
    if (!campaignId || !campaign) return

    setIsCreatingCreative(true)
    try {
      // Navigate to a creative creation page or form
      // For now, we'll create a simple creative and start generation
      navigate(`/campaigns/${campaignId}/creatives/create`)
    } catch (err) {
      console.error('Error creating creative:', err)
    } finally {
      setIsCreatingCreative(false)
    }
  }

  const handleCreativeClick = (creativeId: string) => {
    const creative = creatives.find((c) => c.id === creativeId)
    if (!creative) return

    // Navigate based on creative status
    if (creative.status === 'COMPLETED' || creative.status === 'completed' || creative.status === 'ready') {
      navigate(`/campaigns/${campaignId}/creatives/${creativeId}/results`)
    } else if (creative.status === 'generating' || creative.status === 'processing') {
      navigate(`/campaigns/${campaignId}/creatives/${creativeId}/progress`)
    } else if (creative.status === 'failed') {
      navigate(`/campaigns/${campaignId}/creatives/${creativeId}/results`)
    } else {
      // Draft/pending - allow starting generation
      navigate(`/campaigns/${campaignId}/creatives/${creativeId}/progress`)
    }
  }

  const handleDeleteCreative = async (creativeId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm('Are you sure you want to delete this creative? This cannot be undone.')) {
      try {
        await deleteCreative(campaignId!, creativeId)
      } catch (err) {
        console.error('Failed to delete creative:', err)
      }
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
      case 'COMPLETED':
      case 'ready':
        return 'text-green-500'
      case 'processing':
      case 'generating':
        return 'text-blue-500'
      case 'failed':
        return 'text-red-500'
      default:
        return 'text-muted-gray'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed':
      case 'COMPLETED':
      case 'ready':
        return 'Ready'
      case 'processing':
      case 'generating':
        return 'Generating...'
      case 'failed':
        return 'Failed'
      case 'pending':
      case 'draft':
        return 'Draft'
      default:
        return status
    }
  }

  return (
    <div className="min-h-screen bg-gradient-hero flex flex-col">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-32 -right-32 w-72 h-72 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-32 -left-32 w-72 h-72 bg-gold-silky/10 rounded-full blur-3xl"></div>
      </div>

      {/* Navigation Header */}
      <nav className="relative z-50 border-b border-charcoal-800/60 backdrop-blur-md bg-charcoal-900/40 sticky top-0">
        <div className="max-w-6xl mx-auto w-full px-4 py-4">
          <div className="flex items-center justify-between relative">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-charcoal-800/60 transition-all duration-200 hover:scale-105 hover:shadow-lg hover:text-gold group"
              >
                <ArrowLeft className="w-5 h-5 text-muted-gray group-hover:text-gold transition-colors duration-200" />
                <span className="text-muted-gray group-hover:text-gold transition-colors duration-200">Back</span>
              </button>
            </div>

            <div className="absolute left-1/2 transform -translate-x-1/2 hidden md:block">
              <h1 className="text-sm font-semibold text-off-white">Creatives</h1>
            </div>

            <div className="flex items-center gap-4">
              <Link to="/" className="flex items-center gap-2">
                <div className="p-2 bg-gold rounded-lg shadow-gold">
                  <Sparkles className="h-5 w-5 text-gold-foreground" />
                </div>
                <span className="text-xl font-bold text-gradient-gold">GenAds</span>
              </Link>
              <button
                onClick={() => logout()}
                className="flex items-center gap-2 px-4 py-2 text-sm text-muted-gray hover:text-gold transition-colors rounded-lg hover:bg-charcoal-800/60"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="relative z-10 flex-1 w-full max-w-6xl mx-auto px-4 py-6">
        <motion.div
          className="space-y-6"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Campaign Info */}
          {campaign && (
            <motion.div variants={itemVariants} className="bg-charcoal-900/60 backdrop-blur-sm rounded-xl p-6 border border-charcoal-800/60">
              <h2 className="text-2xl font-bold text-off-white mb-2">{campaign.name}</h2>
              <p className="text-muted-gray">{campaign.seasonal_event} {campaign.year}</p>
            </motion.div>
          )}

          {/* Creatives Section */}
          <motion.div variants={itemVariants} className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h3 className="text-2xl sm:text-3xl font-bold text-off-white mb-2">
                  Creatives
                </h3>
                <p className="text-muted-gray">
                  Create and manage video creatives for this campaign
                </p>
              </div>
              <Button
                onClick={handleCreateCreative}
                disabled={isCreatingCreative}
                className="flex items-center gap-2 bg-gold hover:bg-gold/90 text-gold-foreground px-6 py-3 rounded-lg font-semibold transition-all duration-200 hover:scale-105 shadow-gold"
              >
                <Plus className="w-5 h-5" />
                New Creative
              </Button>
            </div>

            {/* Loading State */}
            {loading && (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-gold"></div>
                <p className="mt-4 text-muted-gray">Loading creatives...</p>
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                <p className="text-red-400">{error}</p>
              </div>
            )}

            {/* Empty State */}
            {!loading && !error && creatives.length === 0 && (
              <motion.div
                variants={itemVariants}
                className="bg-charcoal-900/60 backdrop-blur-sm rounded-xl p-12 border border-charcoal-800/60 text-center"
              >
                <Video className="w-16 h-16 mx-auto mb-4 text-muted-gray" />
                <h3 className="text-xl font-semibold text-off-white mb-2">No creatives yet</h3>
                <p className="text-muted-gray mb-6">
                  Create your first creative to start generating videos
                </p>
                <Button
                  onClick={handleCreateCreative}
                  className="bg-gold hover:bg-gold/90 text-gold-foreground px-6 py-3 rounded-lg font-semibold"
                >
                  <Plus className="w-5 h-5 mr-2" />
                  Create Creative
                </Button>
              </motion.div>
            )}

            {/* Creatives Grid */}
            {!loading && creatives.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {creatives.map((creative) => (
                  <motion.div
                    key={creative.id}
                    variants={itemVariants}
                    className="relative group bg-charcoal-900/60 backdrop-blur-sm rounded-xl p-6 border border-charcoal-800/60 hover:border-gold/50 transition-all duration-200 cursor-pointer hover:shadow-gold/20 hover:shadow-lg"
                    onClick={() => handleCreativeClick(creative.id)}
                  >
                    <div className="absolute top-4 right-4 z-10">
                      <button
                        onClick={(e) => handleDeleteCreative(creative.id, e)}
                        className="p-2 bg-charcoal-800/80 hover:bg-red-500/20 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                      >
                        <Trash2 className="w-4 h-4 text-red-400" />
                      </button>
                    </div>

                    <div className="mb-4">
                      <Video className="w-12 h-12 text-gold mb-3" />
                      <h4 className="text-lg font-semibold text-off-white mb-1">{creative.title}</h4>
                      {creative.brief && (
                        <p className="text-sm text-muted-gray line-clamp-2">{creative.brief}</p>
                      )}
                    </div>

                    <div className="flex items-center justify-between">
                      <span className={`text-sm font-medium ${getStatusColor(creative.status)}`}>
                        {getStatusLabel(creative.status)}
                      </span>
                      {creative.progress !== undefined && creative.progress > 0 && (
                        <span className="text-sm text-muted-gray">{creative.progress}%</span>
                      )}
                    </div>

                    {creative.progress !== undefined && creative.progress > 0 && creative.progress < 100 && (
                      <div className="mt-3 w-full bg-charcoal-800 rounded-full h-2">
                        <div
                          className="bg-gold rounded-full h-2 transition-all duration-300"
                          style={{ width: `${creative.progress}%` }}
                        />
                      </div>
                    )}

                    <div className="mt-4 pt-4 border-t border-charcoal-800">
                      <p className="text-xs text-muted-gray">
                        Created {new Date(creative.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        </motion.div>
      </main>
    </div>
  )
}
