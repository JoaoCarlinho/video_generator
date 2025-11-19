import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { CampaignCard } from '@/components/CampaignCard'
import { useAuth } from '@/hooks/useAuth'
import { usePerfumes } from '@/hooks/usePerfumes'
import { useCampaigns } from '@/hooks/useCampaigns'
import { Plus, ArrowLeft, Sparkles, LogOut, Package, ImageIcon, X } from 'lucide-react'
import { Link } from 'react-router-dom'

export const CampaignDashboard = () => {
  const { perfumeId } = useParams<{ perfumeId: string }>()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { getPerfume } = usePerfumes()
  const { campaigns, loading, error, fetchCampaigns, deleteCampaign } = useCampaigns()
  const [perfume, setPerfume] = useState<any>(null)
  const [perfumeLoading, setPerfumeLoading] = useState(true)

  useEffect(() => {
    if (perfumeId) {
      // Fetch perfume details
      getPerfume(perfumeId)
        .then(setPerfume)
        .catch((err) => {
          console.error('Error fetching perfume:', err)
        })
        .finally(() => setPerfumeLoading(false))

      // Fetch campaigns for this perfume
      fetchCampaigns(perfumeId)
    }
  }, [perfumeId, getPerfume, fetchCampaigns])

  const handleCreateCampaign = () => {
    if (perfumeId) {
      navigate(`/perfumes/${perfumeId}/campaigns/create`)
    }
  }

  const handleCampaignClick = (campaignId: string) => {
    const campaign = campaigns.find((c) => c.campaign_id === campaignId)
    if (!campaign) return

    // Navigate based on campaign status
    if (campaign.status === 'completed') {
      navigate(`/campaigns/${campaignId}/results`)
    } else if (campaign.status === 'processing') {
      navigate(`/campaigns/${campaignId}/progress`)
    } else if (campaign.status === 'failed') {
      // Show error or allow retry
      navigate(`/campaigns/${campaignId}/results`)
    } else {
      // Pending - show progress or results
      navigate(`/campaigns/${campaignId}/progress`)
    }
  }

  const handleDeleteCampaign = async (campaignId: string, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card click
    if (confirm('Are you sure you want to delete this campaign? This cannot be undone.')) {
      try {
        await deleteCampaign(campaignId)
      } catch (err) {
        console.error('Failed to delete campaign:', err)
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
              <Link to="/dashboard" className="flex items-center gap-2">
                <ArrowLeft className="w-5 h-5 text-muted-gray hover:text-gold transition-colors" />
                <span className="text-muted-gray hover:text-gold transition-colors">Back to Dashboard</span>
              </Link>
              <div className="hidden md:block ml-6 pl-6 border-l border-olive-600/50">
                <h1 className="text-sm font-semibold text-off-white">Campaign Dashboard</h1>
              </div>
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
                className="flex items-center gap-2 px-4 py-2 text-sm text-muted-gray hover:text-gold transition-colors rounded-lg hover:bg-olive-800/50"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
          <motion.div
            className="space-y-8 sm:space-y-12"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {/* Perfume Header */}
            {perfumeLoading ? (
              <div className="h-48 bg-olive-800/30 rounded-xl border border-olive-600 animate-pulse" />
            ) : perfume ? (
              <motion.div
                variants={itemVariants}
                className="bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-xl p-6 sm:p-8"
              >
                <div className="flex flex-col sm:flex-row gap-6 items-start sm:items-center">
                  {/* Perfume Image */}
                  <div className="w-32 h-32 sm:w-40 sm:h-40 rounded-lg border-2 border-gold overflow-hidden bg-slate-800 flex-shrink-0">
                    {perfume.front_image_url ? (
                      <img
                        src={perfume.front_image_url}
                        alt={perfume.perfume_name}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <ImageIcon className="w-12 h-12 text-muted-gray" />
                      </div>
                    )}
                  </div>

                  {/* Perfume Info */}
                  <div className="flex-1">
                    <h1 className="text-3xl sm:text-4xl font-bold text-off-white mb-2">
                      {perfume.perfume_name}
                    </h1>
                    <div className="flex flex-wrap items-center gap-4 text-muted-gray">
                      <span className="capitalize">{perfume.perfume_gender}</span>
                      <span>•</span>
                      <span>{campaigns.length} campaign{campaigns.length !== 1 ? 's' : ''}</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div variants={itemVariants} className="text-center py-12">
                <p className="text-red-400">Failed to load perfume details</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate('/dashboard')}
                  className="mt-4"
                >
                  Back to Dashboard
                </Button>
              </motion.div>
            )}

            {/* Campaigns Section */}
            <motion.div variants={itemVariants} className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-2xl sm:text-3xl font-bold text-off-white mb-2">Campaigns</h2>
                  <p className="text-muted-gray text-sm">
                    {campaigns.length} campaign{campaigns.length !== 1 ? 's' : ''} for this perfume
                  </p>
                </div>
                <Button
                  variant="hero"
                  onClick={handleCreateCampaign}
                  className="gap-2 transition-transform duration-200 hover:scale-105"
                  disabled={!perfumeId}
                >
                  <Plus className="w-5 h-5" />
                  Create Campaign
                </Button>
              </div>

              {/* Campaigns Grid */}
              {loading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-64 bg-olive-800/30 rounded-xl border border-olive-600 animate-pulse" />
                  ))}
                </div>
              ) : error ? (
                <div className="p-8 bg-red-500/10 border border-red-500/30 rounded-xl text-center backdrop-blur-sm">
                  <p className="text-red-400 font-medium mb-4">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => perfumeId && fetchCampaigns(perfumeId)}
                    className="gap-2"
                  >
                    Try Again
                  </Button>
                </div>
              ) : campaigns.length === 0 ? (
                <motion.div
                  className="text-center py-20 px-4"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                >
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-gold/10 rounded-full mb-6">
                    <Sparkles className="w-10 h-10 text-gold" />
                  </div>
                  <h3 className="text-2xl font-bold text-off-white mb-3">
                    No campaigns yet
                  </h3>
                  <p className="text-muted-gray mb-8 max-w-md mx-auto">
                    Create your first campaign to generate ad videos for this perfume
                  </p>
                  <Button
                    variant="hero"
                    onClick={handleCreateCampaign}
                    className="gap-2 transition-transform duration-200 hover:scale-105"
                    disabled={!perfumeId}
                  >
                    <Plus className="w-5 h-5" />
                    Create Your First Campaign
                  </Button>
                </motion.div>
              ) : (
                <motion.div
                  className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                >
                  {campaigns.map((campaign) => (
                    <motion.div key={campaign.campaign_id} variants={itemVariants} className="relative group">
                      <CampaignCard
                        campaign={campaign}
                        onClick={() => handleCampaignClick(campaign.campaign_id)}
                      />
                      {/* Delete button on hover */}
                      <button
                        onClick={(e) => handleDeleteCampaign(campaign.campaign_id, e)}
                        className="absolute top-2 right-2 p-2 bg-red-500/80 hover:bg-red-500 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity text-white"
                        title="Delete campaign"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </motion.div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

