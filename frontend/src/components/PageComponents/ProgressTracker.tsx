import { motion, AnimatePresence } from 'framer-motion'
import { Check, Clock, AlertCircle, ChevronDown, Cloud, Server } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'

interface ProgressStep {
  id: string
  label: string
  percentage: number
}

const defaultSteps: ProgressStep[] = [
  { id: 'EXTRACTING', label: 'Extracting Product', percentage: 10 },
  { id: 'PLANNING', label: 'Planning Scenes', percentage: 15 },
  { id: 'GENERATING', label: 'Generating Videos', percentage: 25 },
  { id: 'COMPOSITING', label: 'Compositing Product', percentage: 40 },
  { id: 'TEXT_OVERLAY', label: 'Adding Text', percentage: 60 },
  { id: 'AUDIO', label: 'Generating Audio', percentage: 75 },
  { id: 'RENDERING', label: 'Rendering Output', percentage: 85 },
]

interface ProgressTrackerProps {
  status: 'QUEUED' | 'EXTRACTING' | 'PLANNING' | 'GENERATING' | 'COMPOSITING' | 'TEXT_OVERLAY' | 'AUDIO' | 'RENDERING' | 'COMPLETED' | 'FAILED'
  progress: number
  steps?: ProgressStep[]
  onCancel?: () => void
  error?: string
  // WAN 2.5: Provider tracking
  provider?: 'replicate' | 'ecs'
}

// Helper function to get provider configuration
const getProviderConfig = (provider: 'replicate' | 'ecs') => {
  const config = {
    replicate: {
      label: 'Replicate API',
      icon: Cloud,
      color: 'bg-blue-100 text-blue-800 border-blue-200',
      cost: '$0.80',
      description: 'Cloud API',
    },
    ecs: {
      label: 'VPC Endpoint',
      icon: Server,
      color: 'bg-green-100 text-green-800 border-green-200',
      cost: '$0.20',
      description: 'Self-Hosted GPU',
    },
  }
  return config[provider]
}

export const ProgressTracker = ({
  status,
  progress,
  steps = defaultSteps,
  onCancel,
  error,
  provider = 'replicate',
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

  // Calculate current active step
  // First, try to find a step that is currently in progress
  let currentStep = steps.find((step, index) => {
    const stepStatus = getStepStatus(step.percentage)
    if (stepStatus === 'current') return true
    if (stepStatus === 'pending' && index === 0) return true // First step if nothing started
    if (progress === 100) return step.percentage === 100 // Last step if complete
    return false
  })

  // If no step is "current", find the last completed step or the first pending one
  if (!currentStep) {
    // Find the last completed step
    const completedSteps = steps.filter(step => getStepStatus(step.percentage) === 'completed')
    if (completedSteps.length > 0) {
      currentStep = completedSteps[completedSteps.length - 1]
    } else {
      // If no completed steps, use the first pending step
      currentStep = steps.find(step => getStepStatus(step.percentage) === 'pending') || steps[0]
    }
  }

  const currentStepIndex = steps.findIndex(s => s.id === currentStep.id)
  const currentStepStatus = getStepStatus(currentStep.percentage)

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

  // Get provider configuration
  const providerConfig = getProviderConfig(provider)
  const ProviderIcon = providerConfig.icon

  return (
    <motion.div
      className="space-y-8"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* WAN 2.5: Provider Badge */}
      <motion.div variants={itemVariants}>
        <AnimatePresence mode="wait">
          <motion.div
            key={provider}
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between md:gap-4 p-4 bg-slate-800/30 border border-slate-700/50 rounded-lg"
          >
            <div className="flex items-center gap-3">
              <Badge
                className={`flex items-center gap-2 px-3 py-1.5 text-xs md:text-sm ${providerConfig.color}`}
                role="status"
                aria-label={`Video generation using ${providerConfig.label}`}
              >
                <ProviderIcon className="h-3 w-3 md:h-4 md:w-4" aria-hidden="true" />
                <span className="font-medium">Using: {providerConfig.label}</span>
              </Badge>
            </div>
            <div className="text-xs md:text-sm text-slate-400">
              Estimated cost:{' '}
              <span className="font-semibold text-slate-200">~{providerConfig.cost}</span>
            </div>
          </motion.div>
        </AnimatePresence>
      </motion.div>

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

      {/* Current Step - Prominent Display */}
      <motion.div variants={itemVariants} className="space-y-4">
        <div className="p-6 bg-slate-800/50 border border-slate-700/50 rounded-lg">
          <div className="flex items-start gap-4">
            {/* Step Icon */}
            <div className="flex-shrink-0 mt-1">
              {currentStepStatus === 'completed' ? (
                <motion.div
                  className="w-12 h-12 bg-emerald-500/20 border-2 border-emerald-500 rounded-full flex items-center justify-center"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  <Check className="w-6 h-6 text-emerald-400" />
                </motion.div>
              ) : currentStepStatus === 'current' ? (
                <motion.div
                  className="w-12 h-12 bg-indigo-500 border-2 border-indigo-600 rounded-full flex items-center justify-center"
                  animate={{ scale: [1, 1.05, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                >
                  <Clock className="w-6 h-6 text-gray-50" />
                </motion.div>
              ) : (
                <div className="w-12 h-12 bg-slate-800 border-2 border-slate-700 rounded-full flex items-center justify-center">
                  <div className="w-3 h-3 bg-slate-600 rounded-full" />
                </div>
              )}
            </div>

            {/* Step Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2 mb-2">
                <h4 className="text-lg font-semibold text-slate-100">
                  {currentStep.label}
                </h4>
              </div>
              <p className="text-sm text-slate-400 mb-3">
                Step {currentStepIndex + 1} of {steps.length}
              </p>

              {currentStepStatus === 'current' && (
                <motion.div
                  className="h-2 bg-slate-800 rounded-full overflow-hidden"
                  initial={{ width: 0 }}
                  animate={{ width: '100%' }}
                >
                  <motion.div
                    className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                    initial={{ x: '-100%' }}
                    animate={{ x: '100%' }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                </motion.div>
              )}
            </div>
          </div>
        </div>

        {/* Expandable Full Step List */}
        <details className="group">
          <summary className="flex items-center justify-center gap-2 cursor-pointer text-sm text-slate-400 hover:text-slate-300 transition-colors py-2 list-none">
            <span>Show all steps</span>
            <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
          </summary>

          <motion.div
            className="mt-4 space-y-2 px-2"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ duration: 0.3 }}
          >
            {steps.map((step) => {
              const stepStatus = getStepStatus(step.percentage)
              const isActive = stepStatus === 'current' || stepStatus === 'completed'

              return (
                <div key={step.id} className="flex items-center gap-3 py-2">
                  {/* Mini Step Icon */}
                  <div className="flex-shrink-0">
                    {stepStatus === 'completed' ? (
                      <div className="w-6 h-6 bg-emerald-500/20 border border-emerald-500 rounded-full flex items-center justify-center">
                        <Check className="w-3 h-3 text-emerald-400" />
                      </div>
                    ) : stepStatus === 'current' ? (
                      <div className="w-6 h-6 bg-indigo-500 border border-indigo-600 rounded-full flex items-center justify-center">
                        <Clock className="w-3 h-3 text-gray-50" />
                      </div>
                    ) : (
                      <div className="w-6 h-6 bg-slate-800 border border-slate-700 rounded-full flex items-center justify-center">
                        <div className="w-1.5 h-1.5 bg-slate-600 rounded-full" />
                      </div>
                    )}
                  </div>

                  {/* Step Label */}
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm ${isActive ? 'text-slate-100 font-medium' : 'text-slate-400'}`}>
                      {step.label}
                    </p>
                  </div>

                  {/* Step Percentage */}
                  <span className="text-xs text-slate-500">{step.percentage}%</span>
                </div>
              )
            })}
          </motion.div>
        </details>
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

