import { motion } from 'framer-motion'
import { ImageIcon, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui'

export interface PerfumeCardProps {
  perfume: {
    perfume_id: string
    perfume_name: string
    perfume_gender: 'masculine' | 'feminine' | 'unisex'
    front_image_url: string
    campaigns_count?: number
  }
  onClick: () => void
}

const genderColors = {
  masculine: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  feminine: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  unisex: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
}

const genderLabels = {
  masculine: 'Masculine',
  feminine: 'Feminine',
  unisex: 'Unisex',
}

export const PerfumeCard = ({ perfume, onClick }: PerfumeCardProps) => {
  return (
    <motion.div
      className="group relative aspect-square bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-xl overflow-hidden cursor-pointer hover:border-gold transition-all duration-300 hover:shadow-gold"
      onClick={onClick}
      whileHover={{ y: -4, scale: 1.02 }}
      transition={{ duration: 0.2 }}
    >
      {/* Image */}
      <div className="relative w-full h-3/4 bg-slate-800 overflow-hidden">
        {perfume.front_image_url ? (
          <img
            src={perfume.front_image_url}
            alt={perfume.perfume_name}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <ImageIcon className="w-16 h-16 text-muted-gray" />
          </div>
        )}
        {/* Gold ring on hover */}
        <div className="absolute inset-0 border-2 border-gold opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
      </div>

      {/* Info Section */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-olive-950 via-olive-900 to-transparent p-4">
        <h3 className="text-lg font-bold text-off-white mb-2 truncate">
          {perfume.perfume_name}
        </h3>
        <div className="flex items-center justify-between gap-2">
          <Badge
            variant="outline"
            className={genderColors[perfume.perfume_gender]}
          >
            {genderLabels[perfume.perfume_gender]}
          </Badge>
          {perfume.campaigns_count !== undefined && (
            <div className="flex items-center gap-1 text-xs text-muted-gray">
              <Sparkles className="w-3 h-3" />
              <span>{perfume.campaigns_count} campaign{perfume.campaigns_count !== 1 ? 's' : ''}</span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

