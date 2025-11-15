import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle, Badge, Button } from '@/components/ui'
import { Play, Trash2, Edit3, Clock } from 'lucide-react'

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

const statusColors: Record<string, string> = {
  draft: 'slate',
  generating: 'indigo',
  ready: 'emerald',
  failed: 'red',
  COMPLETED: 'emerald',
}

const statusLabels: Record<string, string> = {
  draft: 'Draft',
  generating: 'Generating...',
  ready: 'Ready',
  failed: 'Failed',
  COMPLETED: 'Completed',
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
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    })
  }

  const variants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
    hover: { y: -8, transition: { duration: 0.2 } },
  }

  const isClickable = status !== 'failed' && onView
  
  const handleCardClick = () => {
    if (isClickable) {
      console.log('Card clicked - navigating to project:', title, status)
      onView?.()
    }
  }
  
  return (
    <motion.div 
      variants={variants} 
      whileHover="hover"
      onClick={handleCardClick}
      className={isClickable ? 'cursor-pointer' : ''}
    >
      <Card
        variant="glass"
        className={`h-full overflow-hidden border transition-all ${
          isClickable 
            ? 'border-slate-700/50 hover:border-indigo-500/50 cursor-pointer' 
            : 'border-slate-700/50'
        }`}
      >
        <CardHeader className="pb-3">
          <div className="flex justify-between items-start gap-2">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-lg truncate">{title}</CardTitle>
              {createdAt && (
                <p className="text-xs text-slate-500 mt-1">{formatDate(createdAt)}</p>
              )}
            </div>
            <Badge
              variant={statusColors[status] as any}
              className="whitespace-nowrap flex-shrink-0"
            >
              {statusLabels[status]}
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Brief Preview */}
          {brief && (
            <p className="text-sm text-slate-400 line-clamp-2">{brief}</p>
          )}

          {/* Progress Bar */}
          {status === 'generating' && (
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">Progress</span>
                <span className="text-indigo-400 font-medium">{progress}%</span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          )}

          {/* Cost Info */}
          {costEstimate && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Clock className="w-3 h-3" />
              <span>Cost: ${costEstimate.toFixed(2)}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            {status === 'draft' && onEdit && (
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation()
                  onEdit()
                }}
                className="flex-1 gap-2"
              >
                <Edit3 className="w-4 h-4" />
                Edit
              </Button>
            )}
            {onDelete && (
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete()
                }}
                className="gap-2 text-red-400 hover:text-red-300 hover:bg-red-500/10"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

