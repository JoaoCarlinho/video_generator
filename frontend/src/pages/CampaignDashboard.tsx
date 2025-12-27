import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { CampaignCard } from '@/components/CampaignCard'
import { useAuth } from '@/hooks/useAuth'
import { useProducts } from '@/hooks/useProducts'
import { useCampaigns, type Campaign } from '@/hooks/useCampaigns'
import { Plus, ArrowLeft, Sparkles, LogOut, Package, X, Pencil } from 'lucide-react'
import { Link } from 'react-router-dom'

export const CampaignDashboard = () => {
  const { productId } = useParams<{ productId: string }>()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { getProduct } = useProducts()
  const { campaigns, loading, error, fetchCampaigns, deleteCampaign, updateCampaign } = useCampaigns()
  const [product, setProduct] = useState<any>(null)
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null)
  const [editName, setEditName] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (productId) {
      // Fetch product details
      getProduct(productId)
        .then(setProduct)
        .catch((err) => {
          console.error('Error fetching product:', err)
        })

      // Fetch campaigns for this product
      fetchCampaigns(productId)
    }
  }, [productId, getProduct, fetchCampaigns])

  const handleCreateCampaign = () => {
    if (productId) {
      navigate(`/products/${productId}/campaigns/create`)
    }
  }

  const handleCampaignClick = (campaignId: string) => {
    // Navigate to creatives list for this campaign
    navigate(`/campaigns/${campaignId}/creatives`)
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

  const handleEditCampaign = (campaign: Campaign, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card click
    setEditingCampaign(campaign)
    setEditName(campaign.name || campaign.campaign_name || '')
  }

  const handleSaveEdit = async () => {
    if (!editingCampaign || !editName.trim()) return

    setIsSaving(true)
    try {
      await updateCampaign(editingCampaign.id, { name: editName.trim() })
      setEditingCampaign(null)
      setEditName('')
      // Refresh campaigns to show updated name
      if (productId) {
        fetchCampaigns(productId)
      }
    } catch (err) {
      console.error('Failed to update campaign:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancelEdit = () => {
    setEditingCampaign(null)
    setEditName('')
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

  const handleBackToDashboard = () => {
    navigate('/dashboard', { replace: true })
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
            {/* Left: Back Button */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleBackToDashboard}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-charcoal-800/60 transition-all duration-200 hover:scale-105 hover:shadow-lg hover:text-gold group"
              >
                <ArrowLeft className="w-5 h-5 text-muted-gray group-hover:text-gold transition-colors duration-200" />
                <span className="text-muted-gray group-hover:text-gold transition-colors duration-200">Back to Products</span>
              </button>
            </div>
            
            {/* Center: Title */}
            <div className="absolute left-1/2 transform -translate-x-1/2 hidden md:block">
              <h1 className="text-sm font-semibold text-off-white">Campaign Dashboard</h1>
            </div>
            
            {/* Right: Logo and Actions */}
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
            {/* Campaigns Section */}
            <motion.div variants={itemVariants} className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-2xl sm:text-3xl font-bold text-off-white mb-2">
                    {product ? product.product_name : 'Campaigns'}
                  </h2>
                  <p className="text-muted-gray text-sm">
                    {campaigns.length} campaign{campaigns.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <Button
                  variant="hero"
                  onClick={handleCreateCampaign}
                  className="gap-2 transition-transform duration-200 hover:scale-105"
                  disabled={!productId}
                >
                  <Plus className="w-5 h-5" />
                  Create Campaign
                </Button>
              </div>

              {/* Campaigns Grid */}
              {loading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-56 bg-charcoal-900/60 rounded-xl border border-charcoal-800/70 animate-pulse" />
                  ))}
                </div>
              ) : error ? (
                <div className="p-6 bg-red-500/10 border border-red-500/30 rounded-xl text-center backdrop-blur-sm">
                  <p className="text-red-400 font-medium mb-4">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => productId && fetchCampaigns(productId)}
                    className="gap-2"
                  >
                    Try Again
                  </Button>
                </div>
              ) : campaigns.length === 0 ? (
                <motion.div
                  className="text-center py-16 px-4"
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
                    Create your first campaign to generate ad videos for this product
                  </p>
                  <Button
                    variant="hero"
                    onClick={handleCreateCampaign}
                    className="gap-2 transition-transform duration-200 hover:scale-105"
                    disabled={!productId}
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
                    <motion.div key={campaign.id} variants={itemVariants} className="relative group">
                      <CampaignCard
                        campaign={campaign}
                        onClick={() => handleCampaignClick(campaign.id)}
                      />
                      {/* Action buttons on hover */}
                      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => handleEditCampaign(campaign, e)}
                          className="p-2 bg-blue-500/80 hover:bg-blue-500 rounded-lg text-white"
                          title="Edit campaign name"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => handleDeleteCampaign(campaign.id, e)}
                          className="p-2 bg-red-500/80 hover:bg-red-500 rounded-lg text-white"
                          title="Delete campaign"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </motion.div>
          </motion.div>
      </main>

      {/* Edit Campaign Modal */}
      {editingCampaign && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-charcoal-900 border border-charcoal-700 rounded-xl p-6 w-full max-w-md mx-4 shadow-xl"
          >
            <h3 className="text-xl font-bold text-off-white mb-4">Edit Campaign Name</h3>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              placeholder="Campaign name"
              className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent mb-4"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !isSaving) {
                  handleSaveEdit()
                } else if (e.key === 'Escape') {
                  handleCancelEdit()
                }
              }}
            />
            <div className="flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={handleCancelEdit}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button
                variant="hero"
                onClick={handleSaveEdit}
                disabled={isSaving || !editName.trim()}
              >
                {isSaving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}

