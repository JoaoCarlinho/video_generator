import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { Trash2, Edit3, Clock, Sparkles, CheckCircle2, Loader2, AlertCircle, FileText } from 'lucide-react'

interface ProjectCardProps {
  id?: string
  title: string
  brief?: string
  status: 'draft' | 'generating' | 'ready' | 'failed' | 'COMPLETED'
  progress?: number
  createdAt?: string
  updatedAt?: string
  costEstimate?: number
  onView?: () => void
  onEdit?: () => void
  onDelete?: () => void
}

const statusConfig: Record<string, { 
  label: string
  icon: typeof CheckCircle2
  color: string
  bg: string
  border: string
  glow: string
}> = {
  draft: {
    label: 'Draft',
    icon: FileText,
    color: 'text-muted-gray',
    bg: 'bg-olive-700/20',
    border: 'border-olive-600/30',
    glow: 'shadow-olive-600/20',
  },
  generating: {
    label: 'Generating',
    icon: Loader2,
    color: 'text-gold',
    bg: 'bg-gold/10',
    border: 'border-gold/30',
    glow: 'shadow-gold/30',
  },
  ready: {
    label: 'Ready',
    icon: CheckCircle2,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    glow: 'shadow-emerald-500/20',
  },
  COMPLETED: {
    label: 'Completed',
    icon: CheckCircle2,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    glow: 'shadow-emerald-500/20',
  },
  failed: {
    label: 'Failed',
    icon: AlertCircle,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    glow: 'shadow-red-500/20',
  },
}

export const ProjectCard = ({
  title,
  brief,
  status,
  progress = 0,
  createdAt,
  costEstimate,
  onView,
  onEdit,
  onDelete,
}: ProjectCardProps) => {
  const formatDate = (date: string | undefined) => {
    if (!date) return ''
    const dateObj = new Date(date)
    const now = new Date()
    const diffTime = Math.abs(now.getTime() - dateObj.getTime())
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    
    if (diffDays === 1) return 'Today'
    if (diffDays === 2) return 'Yesterday'
    if (diffDays <= 7) return `${diffDays - 1} days ago`
    
    return dateObj.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    })
  }

  const variants: any = {
    hidden: { opacity: 0, y: 20, scale: 0.95 },
    visible: { 
      opacity: 1, 
      y: 0, 
      scale: 1,
      transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] }
    },
    hover: { 
      y: -12, 
      scale: 1.02,
      transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] }
    },
  }

  const isClickable = status !== 'failed' && onView
  const statusStyle = statusConfig[status] || statusConfig.draft
  const StatusIcon = statusStyle.icon
  
  const handleCardClick = () => {
    if (isClickable) {
      onView?.()
    }
  }
  
  return (
    <motion.div 
      variants={variants} 
      whileHover="hover"
      onClick={handleCardClick}
      className={`group relative ${isClickable ? 'cursor-pointer' : ''}`}
    >
      <div
        className={`relative h-full overflow-hidden bg-olive-800/40 backdrop-blur-md border rounded-2xl transition-all duration-500 ${
          isClickable 
            ? `border-olive-600/50 group-hover:border-gold/60 group-hover:shadow-[0_0_30px_rgba(243,217,164,0.4),0_0_60px_rgba(243,217,164,0.2),0_0_90px_rgba(243,217,164,0.1)]` 
            : 'border-olive-600/50'
        }`}
      >
        {/* Animated gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-gold/0 via-transparent to-gold-silky/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
        
        {/* Subtle shine effect */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/0 to-transparent opacity-0 group-hover:opacity-5 group-hover:animate-shimmer pointer-events-none" />
        
        {/* Status indicator bar */}
        <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${statusStyle.bg} ${statusStyle.border} border-b`} />
        
        <div className="relative p-6 space-y-5">
          {/* Header Section */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0 space-y-3">
              {/* Title with icon */}
              <div className="flex items-start gap-3">
                <div className={`p-2.5 rounded-xl ${statusStyle.bg} ${statusStyle.border} border group-hover:scale-110 transition-transform duration-300 flex-shrink-0`}>
                  <Sparkles className="w-4 h-4 text-gold" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-bold text-off-white leading-tight mb-1.5 group-hover:text-gold transition-colors duration-300 line-clamp-2">
                    {title}
                  </h3>
                  {createdAt && (
                    <div className="flex items-center gap-1.5 text-xs text-muted-gray">
                      <Clock className="w-3 h-3" />
                      <span>{formatDate(createdAt)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            {/* Status Badge */}
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${statusStyle.bg} ${statusStyle.border} border flex-shrink-0 group-hover:scale-105 transition-transform duration-300`}>
              <StatusIcon className={`w-3.5 h-3.5 ${statusStyle.color} ${status === 'generating' ? 'animate-spin' : ''}`} />
              <span className={`text-xs font-semibold ${statusStyle.color}`}>
                {statusStyle.label}
              </span>
            </div>
          </div>

          {/* Brief Preview */}
          {brief && (
            <p className="text-sm text-muted-gray line-clamp-3 leading-relaxed min-h-[3.75rem]">
              {brief}
            </p>
          )}

          {/* Progress Section */}
          {status === 'generating' && (
            <div className="space-y-3 pt-2 border-t border-olive-600/30">
              <div className="flex justify-between items-center">
                <span className="text-xs font-medium text-muted-gray uppercase tracking-wider">Progress</span>
                <span className="text-sm font-bold text-gold">{progress}%</span>
              </div>
              <div className="relative h-2 bg-olive-700/30 rounded-full overflow-hidden border border-olive-600/20">
                <motion.div
                  className="h-full bg-gradient-to-r from-gold via-gold-dark to-gold rounded-full relative overflow-hidden"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
                >
                  {/* Shimmer effect on progress bar */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
                </motion.div>
              </div>
            </div>
          )}

          {/* Footer Section */}
          <div className="flex items-center justify-between pt-4 border-t border-olive-600/30">
            {/* Cost Info */}
            {costEstimate && (
              <div className="flex items-center gap-2 text-xs text-muted-gray">
                <div className="p-1 bg-olive-700/30 rounded">
                  <Clock className="w-3 h-3" />
                </div>
                <span className="font-medium">${costEstimate.toFixed(2)}</span>
              </div>
            )}
            
            {/* Actions */}
            <div className="flex items-center gap-2 ml-auto">
              {status === 'draft' && onEdit && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={(e) => {
                    e.stopPropagation()
                    onEdit()
                  }}
                  className="h-8 px-3 text-xs text-muted-gray hover:text-gold hover:bg-gold/10 border border-transparent hover:border-gold/30 transition-all duration-200"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                </Button>
              )}
            </div>
          </div>
          
          {/* Delete Button - Bottom Right */}
          {onDelete && (
            <div className="absolute bottom-4 right-4">
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete()
                }}
                className="h-8 w-8 p-0 text-muted-gray hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/30 transition-all duration-200 rounded-lg"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
