import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { ProjectCard } from '@/components/PageComponents/CampaignCard'
import { useAuth } from '@/hooks/useAuth'
import { useCampaigns } from '@/hooks/useCampaigns'
import { useCreatives } from '@/hooks/useCreatives'
import { Plus, ArrowLeft, Sparkles, LogOut, X } from 'lucide-react'
import { Link } from 'react-router-dom'

export const CreativeDashboard = () => {
  const { campaignId } = useParams<{ campaignId: string }>()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { getCampaign } = useCampaigns()
  const { creatives, loading, error, fetchCreatives, deleteCreative } = useCreatives()
  const [campaign, setCampaign] = useState<any>(null)

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

  const handleCreateCreative = () => {
    if (campaignId) {
      navigate(`/campaigns/${campaignId}/creatives/new`)
    }
  }

  const handleCreativeClick = (creativeId: string) => {
    const creative = creatives.find((c) => c.id === creativeId)
    if (!creative) return

    // Navigate based on creative status
    if (creative.status === 'COMPLETED' || creative.status === 'ready') {
      navigate(`/campaigns/${campaignId}/creatives/${creativeId}/results`)
    } else if (creative.status === 'generating' || creative.status === 'draft') {
      navigate(`/campaigns/${campaignId}/creatives/${creativeId}/progress`)
    } else if (creative.status === 'failed') {
      // Show error or allow retry
      navigate(`/campaigns/${campaignId}/creatives/${creativeId}/results`)
    } else {
      // Default to progress
      navigate(`/campaigns/${campaignId}/creatives/${creativeId}/progress`)
    }
  }

  const handleDeleteCreative = async (creativeId: string, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card click
    if (!campaignId) return

    if (confirm('Are you sure you want to delete this creative? This cannot be undone.')) {
      try {
        await deleteCreative(campaignId, creativeId)
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

  const handleBackToCampaigns = () => {
    navigate('/dashboard', { replace: true })
  }

  return (
    <div className="min-h-screen bg-gradient-light flex flex-col">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-32 -right-32 w-72 h-72 bg-blue-100/50 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-32 -left-32 w-72 h-72 bg-blue-50/50 rounded-full blur-3xl"></div>
      </div>

      {/* Navigation Header */}
      <nav className="relative z-50 border-b border-gray-200 backdrop-blur-md bg-white/80 sticky top-0">
        <div className="max-w-6xl mx-auto w-full px-4 py-4">
          <div className="flex items-center justify-between relative">
            {/* Left: Back Button */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleBackToCampaigns}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-all duration-200 hover:scale-105 hover:shadow-lg hover:text-primary-600 group"
              >
                <ArrowLeft className="w-5 h-5 text-gray-600 group-hover:text-primary-600 transition-colors duration-200" />
                <span className="text-gray-600 group-hover:text-primary-600 transition-colors duration-200">Back to Dashboard</span>
              </button>
            </div>

            {/* Center: Title */}
            <div className="absolute left-1/2 transform -translate-x-1/2 hidden md:block">
              <h1 className="text-sm font-semibold text-gray-900">Creative Dashboard</h1>
            </div>

            {/* Right: Logo and Actions */}
            <div className="flex items-center gap-4">
              <Link to="/" className="flex items-center gap-2">
                <div className="p-2 bg-primary-500 rounded-lg shadow-md">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <span className="text-xl font-bold text-primary-600">GenAds</span>
              </Link>
              <button
                onClick={() => logout()}
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-primary-600 transition-colors rounded-lg hover:bg-gray-100"
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
            {/* Creatives Section */}
            <motion.div variants={itemVariants} className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
                    {campaign ? campaign.campaign_name : 'Creatives'}
                  </h2>
                  <p className="text-gray-600 text-sm">
                    {creatives.length} creative{creatives.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <Button
                  onClick={handleCreateCreative}
                  className="gap-2 bg-primary-500 text-white hover:bg-primary-600 transition-transform duration-200 hover:scale-105"
                  disabled={!campaignId}
                >
                  <Plus className="w-5 h-5" />
                  Create Creative
                </Button>
              </div>

              {/* Creatives Grid */}
              {loading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-56 bg-gray-100 rounded-xl border border-gray-200 animate-pulse" />
                  ))}
                </div>
              ) : error ? (
                <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-center backdrop-blur-sm">
                  <p className="text-red-600 font-medium mb-4">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => campaignId && fetchCreatives(campaignId)}
                    className="gap-2"
                  >
                    Try Again
                  </Button>
                </div>
              ) : creatives.length === 0 ? (
                <motion.div
                  className="text-center py-16 px-4"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                >
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-primary-50 rounded-full mb-6">
                    <Sparkles className="w-10 h-10 text-primary-600" />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 mb-3">
                    No creatives yet
                  </h3>
                  <p className="text-gray-600 mb-8 max-w-md mx-auto">
                    Create your first creative to generate videos for this campaign
                  </p>
                  <Button
                    onClick={handleCreateCreative}
                    className="gap-2 bg-primary-500 text-white hover:bg-primary-600 transition-transform duration-200 hover:scale-105"
                    disabled={!campaignId}
                  >
                    <Plus className="w-5 h-5" />
                    Create Your First Creative
                  </Button>
                </motion.div>
              ) : (
                <motion.div
                  className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                >
                  {creatives.map((creative) => (
                    <motion.div key={creative.id} variants={itemVariants} className="relative group">
                      <ProjectCard
                        id={creative.id}
                        title={creative.title}
                        brief={creative.brief}
                        status={creative.status}
                        progress={creative.progress}
                        createdAt={creative.created_at}
//                         costEstimate={creative.cost}
                        onView={() => handleCreativeClick(creative.id)}
                      />
                      {/* Delete button on hover */}
                      <button
                        onClick={(e) => handleDeleteCreative(creative.id, e)}
                        className="absolute top-2 right-2 p-2 bg-red-500/80 hover:bg-red-500 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity text-white z-10"
                        title="Delete creative"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </motion.div>
          </motion.div>
      </main>
    </div>
  )
}
