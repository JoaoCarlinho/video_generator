import { motion } from 'framer-motion'
import { Check, Clock, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'

interface ProgressStep {
  id: string
  label: string
  percentage: number
}

const defaultSteps: ProgressStep[] = [
  { id: 'EXTRACTING', label: 'Extracting Product', percentage: 10 },
  { id: 'PLANNING', label: 'Planning Scenes', percentage: 15 },
  { id: 'GENERATING', label: 'Generating Videos', percentage: 45 },
  { id: 'COMPOSITING', label: 'Compositing Product', percentage: 60 },
  { id: 'TEXT_OVERLAY', label: 'Adding Text', percentage: 75 },
  { id: 'AUDIO', label: 'Generating Audio', percentage: 85 },
  { id: 'RENDERING', label: 'Rendering Output', percentage: 100 },
]

interface ProgressTrackerProps {
  status: 'QUEUED' | 'EXTRACTING' | 'PLANNING' | 'GENERATING' | 'COMPOSITING' | 'TEXT_OVERLAY' | 'AUDIO' | 'RENDERING' | 'COMPLETED' | 'FAILED'
  progress: number
  steps?: ProgressStep[]
  onCancel?: () => void
  error?: string
}

export const ProgressTracker = ({
  status,
  progress,
  steps = defaultSteps,
  onCancel,
  error,
}: ProgressTrackerProps) => {
  const isComplete = status === 'COMPLETED'
  const isFailed = status === 'FAILED'
  const isQueued = status === 'QUEUED'

  const getStepStatus = (stepPercentage: number) => {
    if (stepPercentage <= progress) {
      return 'completed'
    } else if (stepPercentage - 10 < progress && progress < stepPercentage) {
      return 'current'
    }
    return 'pending'
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
    hidden: { opacity: 0, x: -20 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.4 } },
  }

  return (
    <motion.div
      className="space-y-8"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Overall Progress */}
      <motion.div variants={itemVariants} className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-100">Generation Progress</h3>
          <Badge
            variant={isComplete ? 'success' : isFailed ? 'danger' : isQueued ? 'outline' : 'secondary'}
            className="capitalize"
          >
            {isQueued
              ? 'Queued'
              : isFailed
                ? 'Failed'
                : isComplete
                  ? 'Complete'
                  : 'In Progress'}
          </Badge>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Overall Progress</span>
            <span className="text-indigo-400 font-medium">{Math.round(progress)}%</span>
          </div>
          <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              className={`h-full rounded-full transition-all ${
                isFailed
                  ? 'bg-gradient-to-r from-red-500 to-red-600'
                  : isComplete
                    ? 'bg-gradient-to-r from-emerald-500 to-emerald-600'
                    : 'bg-gradient-to-r from-indigo-500 to-purple-500'
              }`}
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.8 }}
            />
          </div>
        </div>
      </motion.div>

      {/* Error Message */}
      {error && isFailed && (
        <motion.div
          variants={itemVariants}
          className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg flex gap-3"
        >
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-red-400 font-medium text-sm">Generation Failed</p>
            <p className="text-red-300/80 text-xs mt-1">{error}</p>
          </div>
        </motion.div>
      )}

      {/* Steps */}
      <motion.div variants={itemVariants} className="space-y-3">
        {steps.map((step) => {
          const stepStatus = getStepStatus(step.percentage)
          const isActive = stepStatus === 'current' || stepStatus === 'completed'

          return (
            <motion.div
              key={step.id}
              className="relative"
              whileHover={{ x: 4 }}
              transition={{ duration: 0.2 }}
            >
              <div className="flex items-start gap-4">
                {/* Step Icon */}
                <div className="flex-shrink-0 mt-1">
                  {stepStatus === 'completed' ? (
                    <motion.div
                      className="w-8 h-8 bg-emerald-500/20 border border-emerald-500 rounded-full flex items-center justify-center"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ duration: 0.3 }}
                    >
                      <Check className="w-4 h-4 text-emerald-400" />
                    </motion.div>
                  ) : stepStatus === 'current' ? (
                    <motion.div
                      className="w-8 h-8 bg-indigo-500 border border-indigo-600 rounded-full flex items-center justify-center"
                      animate={{ scale: [1, 1.1, 1] }}
                      transition={{ duration: 1, repeat: Infinity }}
                    >
                      <Clock className="w-4 h-4 text-white" />
                    </motion.div>
                  ) : (
                    <div className="w-8 h-8 bg-slate-800 border border-slate-700 rounded-full flex items-center justify-center">
                      <div className="w-2 h-2 bg-slate-600 rounded-full" />
                    </div>
                  )}
                </div>

                {/* Step Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p
                      className={`font-medium text-sm ${
                        isActive ? 'text-slate-100' : 'text-slate-400'
                      }`}
                    >
                      {step.label}
                    </p>
                    <span className="text-xs text-slate-500">{step.percentage}%</span>
                  </div>

                  {stepStatus === 'current' && (
                    <motion.div
                      className="mt-2 h-1 bg-slate-800 rounded-full overflow-hidden"
                      initial={{ width: 0 }}
                      animate={{ width: '100%' }}
                    >
                      <motion.div
                        className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                        initial={{ x: '-100%' }}
                        animate={{ x: '100%' }}
                        transition={{ duration: 1, repeat: Infinity }}
                      />
                    </motion.div>
                  )}
                </div>
              </div>
            </motion.div>
          )
        })}
      </motion.div>

      {/* Time Estimate */}
      {!isComplete && !isFailed && (
        <motion.div variants={itemVariants} className="text-center">
          <p className="text-slate-400 text-sm">
            Estimated time remaining: <span className="text-slate-100 font-medium">
              ~{Math.ceil((100 - progress) / 10)} minutes
            </span>
          </p>
        </motion.div>
      )}

      {/* Actions */}
      {!isComplete && onCancel && (
        <motion.div variants={itemVariants} className="flex justify-center pt-4">
          <button
            onClick={onCancel}
            className="text-red-400 hover:text-red-300 text-sm font-medium transition-colors"
          >
            Cancel Generation
          </button>
        </motion.div>
      )}

      {/* Success Message */}
      {isComplete && (
        <motion.div
          variants={itemVariants}
          className="p-4 bg-emerald-500/10 border border-emerald-500/50 rounded-lg text-center"
        >
          <p className="text-emerald-400 font-medium">✓ Video generated successfully!</p>
          <p className="text-emerald-300/80 text-sm mt-1">Your video is ready to download</p>
        </motion.div>
      )}
    </motion.div>
  )
}

