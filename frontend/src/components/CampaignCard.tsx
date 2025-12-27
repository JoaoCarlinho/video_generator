import { motion } from 'framer-motion'
import { Video, Clock, Sparkles, DollarSign, Calendar } from 'lucide-react'
import { Badge } from '@/components/ui'
import type { Campaign, CampaignStatus } from '@/hooks/useCampaigns'

export interface CampaignCardProps {
  campaign: Campaign
  onClick: () => void
}

const statusColors: Record<CampaignStatus, string> = {
  pending: 'bg-slate-600/20 text-slate-400 border-slate-600/30',
  processing: 'bg-blue-600/20 text-blue-400 border-blue-600/30',
  completed: 'bg-emerald-600/20 text-emerald-400 border-emerald-600/30',
  failed: 'bg-red-600/20 text-red-400 border-red-600/30',
}

const statusLabels: Record<CampaignStatus, string> = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const formatCost = (cost: number | string | null | undefined): string => {
  if (cost === null || cost === undefined) {
    return '$0.00'
  }
  const numCost = typeof cost === 'string' ? parseFloat(cost) : cost
  if (isNaN(numCost)) {
    return '$0.00'
  }
  return `$${numCost.toFixed(2)}`
}

export const CampaignCard = ({ campaign, onClick }: CampaignCardProps) => {
  // Get video thumbnail from campaign_json if available
  // Backend stores as object: {"variation_0": {"aspectExports": {"9:16": "url"}}, ...}
  // Handle case where campaign_json might be a string (JSONB serialization)
  let campaignJson = campaign.campaign_json || {}
  if (typeof campaignJson === 'string') {
    try {
      campaignJson = JSON.parse(campaignJson)
    } catch (e) {
      console.error('❌ Failed to parse campaign_json:', e)
      campaignJson = {}
    }
  }
  const variationPaths = campaignJson?.variationPaths || {}
  let thumbnailUrl: string | null = null
  
  // Handle both object format (from backend) and array format (legacy)
  if (Array.isArray(variationPaths) && variationPaths.length > 0) {
    // Legacy array format
    thumbnailUrl = variationPaths[0]?.final_video_url || variationPaths[0]?.video_url || null
  } else if (typeof variationPaths === 'object' && Object.keys(variationPaths).length > 0) {
    // Current object format
    const firstVariationKey = Object.keys(variationPaths).sort()[0]
    const firstVariation = variationPaths[firstVariationKey]
    thumbnailUrl = firstVariation?.aspectExports?.['9:16'] 
      || firstVariation?.final_video_url 
      || firstVariation?.video_url 
      || null
  }

  return (
    <motion.div
      className="group relative bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl overflow-hidden cursor-pointer hover:border-gold transition-all duration-300 hover:shadow-lg hover:shadow-gold/10"
      onClick={onClick}
      whileHover={{ y: -4, scale: 1.02 }}
      transition={{ duration: 0.2 }}
    >
      {/* Video Thumbnail */}
      <div className="relative w-full h-40 bg-slate-900 overflow-hidden">
        {thumbnailUrl ? (
          <video
            src={thumbnailUrl}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
            muted
            playsInline
            preload="metadata"
            onMouseEnter={(e) => {
              const video = e.currentTarget
              video.currentTime = 0.5 // Show frame at 0.5s
              video.play().catch(() => {}) // Muted autoplay
            }}
            onMouseLeave={(e) => {
              e.currentTarget.pause()
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
            <div className="flex flex-col items-center gap-2">
              <Video className="w-10 h-10 text-muted-gray" />
              <span className="text-xs text-muted-gray">No preview</span>
            </div>
          </div>
        )}
        {/* Gold ring on hover */}
        <div className="absolute inset-0 border-2 border-gold opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
      </div>

      {/* Content Section */}
      <div className="p-3 space-y-2">
        {/* Campaign Name */}
        <h3 className="text-base font-bold text-off-white truncate group-hover:text-gold transition-colors">
          {campaign.name || campaign.campaign_name}
        </h3>

        {/* Status Badge */}
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={statusColors[campaign.status]}
            animated={campaign.status === 'processing'}
          >
            {statusLabels[campaign.status]}
          </Badge>
          {campaign.status === 'processing' && (
            <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gold transition-all duration-300"
                style={{ width: `${campaign.progress}%` }}
              />
            </div>
          )}
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          {/* Duration */}
          <div className="flex items-center gap-1.5 text-muted-gray">
            <Clock className="w-3.5 h-3.5" />
            <span>{campaign.target_duration}s</span>
          </div>

          {/* Variations */}
          <div className="flex items-center gap-1.5 text-muted-gray">
            <Sparkles className="w-3.5 h-3.5" />
            <span>
              {campaign.num_variations} variation{campaign.num_variations !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Created Date */}
          <div className="flex items-center gap-1.5 text-muted-gray">
            <Calendar className="w-3.5 h-3.5" />
            <span>{formatDate(campaign.created_at)}</span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

