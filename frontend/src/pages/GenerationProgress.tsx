import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { useProgressPolling } from '@/hooks/useProgressPolling'
import { useGeneration } from '@/hooks/useGeneration'
import { ArrowLeft, Sparkles, CheckCircle2, Loader2, Video, Zap, Clock } from 'lucide-react'
import { storeVideo, formatBytes, getStorageUsage } from '@/services/videoStorage'
import { api } from '@/services/api'

const stepLabels: Record<string, string> = {
  QUEUED: 'Queued',
  EXTRACTING: 'Extracting Product',
  PLANNING: 'Planning Scenes',
  GENERATING: 'Generating Videos',
  COMPOSITING: 'Compositing Product',
  TEXT_OVERLAY: 'Adding Text Overlay',
  AUDIO: 'Generating Audio',
  RENDERING: 'Rendering Final Video',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
}

export const GenerationProgress = () => {
  const { campaignId, projectId } = useParams<{ campaignId?: string; projectId?: string }>()
  const navigate = useNavigate()
  const { generateVideo, generateCampaign } = useGeneration()
  const [isStartingGeneration, setIsStartingGeneration] = useState(false)
  const hasStartedGenerationRef = useRef(false)
  
  // Use campaignId if available, otherwise fall back to projectId (legacy)
  const id = campaignId || projectId || ''
  const isCampaign = !!campaignId
  const storageKey = `generation_started_${id}`

  // Start generation job when component mounts
  useEffect(() => {
    const alreadyStarted = hasStartedGenerationRef.current || sessionStorage.getItem(storageKey) === 'true'
    
    if (!id || alreadyStarted) {
      return
    }

    let isMounted = true

    const startGenerationIfNeeded = async () => {
      if (!isMounted || hasStartedGenerationRef.current || sessionStorage.getItem(storageKey) === 'true') {
        return
      }
      
      try {
        hasStartedGenerationRef.current = true
        sessionStorage.setItem(storageKey, 'true')
        setIsStartingGeneration(true)
        console.log(`🚀 Starting generation for ${isCampaign ? 'campaign' : 'project'}:`, id)
        
        const result = isCampaign 
          ? await generateCampaign(id)
          : await generateVideo(id)
        
        if (isMounted) {
          console.log('✅ Generation queued:', result)
        }
      } catch (err) {
        if (isMounted) {
          console.error('❌ Failed to queue generation:', err)
          hasStartedGenerationRef.current = false
          sessionStorage.removeItem(storageKey)
        }
      } finally {
        if (isMounted) {
          setIsStartingGeneration(false)
        }
      }
    }
    
    startGenerationIfNeeded()
    
    return () => {
      isMounted = false
    }
  }, [id, isCampaign, generateVideo, generateCampaign, storageKey])

  const { progress, isPolling, stopPolling } = useProgressPolling({
    projectId: isCampaign ? undefined : id,
    campaignId: isCampaign ? id : undefined,
    enabled: true,
    interval: 2000,
    onComplete: async () => {
      sessionStorage.removeItem(storageKey)
      
      try {
        if (isCampaign) {
          // Campaign-based flow
          console.log('📥 Campaign generation complete, navigating to results...')
          
          try {
            const campaignResponse = await api.get(`/api/campaigns/${id}`)
            const campaign = campaignResponse.data
            const numVariations = campaign.num_variations || 1
            
            console.log(`🎬 Number of variations: ${numVariations}`)
            
            // For campaigns, videos are stored in S3, not local storage
            // Navigate directly to results page
            setTimeout(() => {
              if (numVariations > 1) {
                // Multiple variations - go to selection page
                console.log(`🎯 Routing to selection page for ${numVariations} variations`)
                navigate(`/campaigns/${id}/select`)
              } else {
                // Single variation - go directly to results
                console.log(`🎯 Routing to results page (single variation)`)
                navigate(`/campaigns/${id}/results`)
              }
            }, 1000)
          } catch (err) {
            console.error('⚠️ Failed to fetch campaign:', err)
            // Fallback: navigate to results page
            setTimeout(() => {
              navigate(`/campaigns/${id}/results`)
            }, 1000)
          }
        } else {
          // Legacy project-based flow
        console.log('📥 Downloading video to local storage...')
        
          const projectResponse = await api.get(`/api/projects/${id}`)
        const project = projectResponse.data
        const projectAspectRatio = project.aspect_ratio || '9:16'
        const numVariations = project.num_variations || 1
        
        console.log(`📐 Project aspect ratio: ${projectAspectRatio}`)
        console.log(`🎬 Number of variations: ${numVariations}`)
        
        // For single variation, download video to local storage
        // For multiple variations, videos are already stored locally by the pipeline
        if (numVariations === 1) {
          try {
              const response = await api.get(`/api/local-generation/projects/${id}/preview`, {
              responseType: 'blob'
            })
            
            if (response.data) {
                await storeVideo(id, projectAspectRatio as '9:16' | '1:1' | '16:9', response.data, false)
              console.log(`✅ Downloaded video from local storage`)
            }
          } catch (err) {
            console.error(`⚠️ Failed to download video:`, err)
          }
        } else {
          console.log(`📹 Multiple variations generated - skipping single video download`)
        }
        
          const usage = await getStorageUsage(id)
        console.log(`📊 Total local storage used: ${formatBytes(usage)}`)
        
        // Route based on number of variations
        setTimeout(() => {
          if (numVariations > 1) {
            // Multiple variations - go to selection page
            console.log(`🎯 Routing to selection page for ${numVariations} variations`)
              navigate(`/projects/${id}/select`)
          } else {
            // Single variation - go directly to results
            console.log(`🎯 Routing to results page (single variation)`)
              navigate(`/projects/${id}/results`)
          }
        }, 1000)
        }
      } catch (err) {
        console.error('⚠️ Failed to download video to local storage:', err)
        // Fallback: navigate to results page
        setTimeout(() => {
          if (isCampaign) {
            navigate(`/campaigns/${id}/results`)
          } else {
            navigate(`/projects/${id}/results`)
          }
        }, 1000)
      }
    },
    onError: (error) => {
      console.error('Generation error:', error)
      sessionStorage.removeItem(storageKey)
    },
  })

  useEffect(() => {
    if (progress?.status === 'FAILED' || progress?.status === 'failed') {
      sessionStorage.removeItem(storageKey)
    }
  }, [progress?.status, storageKey])

  const currentProgress = progress?.progress || 0
  const status = (progress?.status as 'EXTRACTING' | 'PLANNING' | 'GENERATING' | 'COMPOSITING' | 'TEXT_OVERLAY' | 'AUDIO' | 'RENDERING' | 'QUEUED' | 'COMPLETED' | 'FAILED') || 'QUEUED'
  const error = progress?.error
  const isComplete = status === 'COMPLETED'
  const isFailed = status === 'FAILED'
  const isQueued = status === 'QUEUED'
  const isGenerating = !isComplete && !isFailed && !isQueued

  return (
    <div className="min-h-screen bg-gradient-hero">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gold-silky/10 rounded-full blur-3xl"></div>
        <div className="absolute inset-0 bg-gradient-to-br from-gold/5 via-transparent to-transparent" />
        
        {/* Animated particles during generation */}
        {isGenerating && (
          <>
            {[...Array(6)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-2 h-2 bg-gold/30 rounded-full"
                initial={{
                  x: `${20 + i * 15}%`,
                  y: '100%',
                  opacity: 0,
                }}
                animate={{
                  y: '-20%',
                  opacity: [0, 1, 0],
                }}
                transition={{
                  duration: 3 + i * 0.5,
                  repeat: Infinity,
                  delay: i * 0.3,
                  ease: 'easeOut',
                }}
              />
            ))}
          </>
        )}
      </div>

      {/* Navigation Header */}
      <nav className="relative z-50 border-b border-olive-600/50 backdrop-blur-md bg-olive-950/30 sticky top-0">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 hover:bg-olive-800/50 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-muted-gray hover:text-gold" />
              </button>
              <div className="flex items-center gap-2">
                <div className="p-2 bg-gold rounded-lg shadow-gold">
                  <Sparkles className="h-5 w-5 text-gold-foreground" />
                </div>
                <span className="text-xl font-bold text-gradient-gold">GenAds</span>
              </div>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-sm font-semibold text-off-white">Video Generation</h1>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 max-w-3xl">
          <div className="flex flex-col items-center justify-center min-h-[calc(100vh-120px)]">
            {/* Main Progress Card */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="w-full bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-2xl p-6 sm:p-8 shadow-gold-lg"
            >
              {/* Status Badge */}
              <div className="flex justify-center mb-6">
                <div className={`px-4 py-2 rounded-lg border ${
                  isComplete 
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : isFailed
                      ? 'bg-red-500/10 border-red-500/30 text-red-400'
                      : isQueued
                        ? 'bg-muted-gray/10 border-olive-600 text-muted-gray'
                        : 'bg-gold/10 border-gold/30 text-gold'
                }`}>
                  <span className="text-sm font-semibold capitalize">
                    {isQueued ? 'Queued' : isFailed ? 'Failed' : isComplete ? 'Complete' : 'In Progress'}
                  </span>
                </div>
              </div>

              {/* Progress Circle */}
              <div className="flex justify-center mb-6">
                <div className="relative w-32 h-32 sm:w-40 sm:h-40">
                  {/* Background circle */}
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="50%"
                      cy="50%"
                      r="45%"
                      fill="none"
                      stroke="rgb(93 107 90)"
                      strokeWidth="4"
                      className="opacity-30"
                    />
                    {/* Progress circle */}
                    <motion.circle
                      cx="50%"
                      cy="50%"
                      r="45%"
                      fill="none"
                      stroke={isFailed ? 'rgb(239 68 68)' : isComplete ? 'rgb(16 185 129)' : 'url(#goldGradient)'}
                      strokeWidth="4"
                      strokeLinecap="round"
                      initial={{ pathLength: 0 }}
                      animate={{ pathLength: currentProgress / 100 }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                    />
                    <defs>
                      <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#F3D9A4" />
                        <stop offset="100%" stopColor="#D4B676" />
                      </linearGradient>
                    </defs>
                  </svg>
                  
                  {/* Center content */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    {isGenerating && (
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                        className="mb-2"
                      >
                        <Loader2 className="w-8 h-8 sm:w-10 sm:h-10 text-gold" />
                      </motion.div>
                    )}
                    {isComplete && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', stiffness: 200 }}
                      >
                        <CheckCircle2 className="w-8 h-8 sm:w-10 sm:h-10 text-emerald-400" />
                      </motion.div>
                    )}
                    {isFailed && (
                      <div className="text-red-400 text-4xl mb-2">✗</div>
                    )}
                    {isQueued && (
                      <Clock className="w-8 h-8 sm:w-10 sm:h-10 text-muted-gray" />
                    )}
                    <span className={`text-2xl sm:text-3xl font-bold ${
                      isComplete ? 'text-emerald-400' : isFailed ? 'text-red-400' : 'text-gold'
                    }`}>
                      {Math.round(currentProgress)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Current Step */}
              {isGenerating && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center mb-6"
                >
                  <div className="flex items-center justify-center gap-3 mb-2">
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                      className="p-2 bg-gold/10 rounded-lg border border-gold/20"
                    >
                      <Video className="w-5 h-5 text-gold" />
                    </motion.div>
                    <h3 className="text-lg sm:text-xl font-bold text-off-white">
                      {stepLabels[status] || status}
                    </h3>
                  </div>
                  <p className="text-sm text-muted-gray">
                    {status === 'EXTRACTING' && 'Analyzing your product image...'}
                    {status === 'PLANNING' && 'Creating scene structure...'}
                    {status === 'GENERATING' && 'Generating video scenes...'}
                    {status === 'COMPOSITING' && 'Compositing product into scenes...'}
                    {status === 'TEXT_OVERLAY' && 'Adding text overlays...'}
                    {status === 'AUDIO' && 'Generating background audio...'}
                    {status === 'RENDERING' && 'Rendering final video...'}
                  </p>
                </motion.div>
              )}

              {isQueued && (
                <div className="text-center mb-6">
                  <h3 className="text-lg sm:text-xl font-bold text-off-white mb-2">
                    Video Queued
                  </h3>
                  <p className="text-sm text-muted-gray">
                    Your video is in the queue and will start generating shortly...
                  </p>
                </div>
              )}

              {isComplete && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-center mb-6"
                >
                  <h3 className="text-lg sm:text-xl font-bold text-emerald-400 mb-2">
                    Generation Complete!
                  </h3>
                  <p className="text-sm text-muted-gray">
                    Your video is ready. Redirecting to results...
                  </p>
                </motion.div>
              )}

              {isFailed && (
                <div className="text-center mb-6">
                  <h3 className="text-lg sm:text-xl font-bold text-red-400 mb-2">
                    Generation Failed
                  </h3>
                  {error && (
                    <p className="text-sm text-red-300/80 mb-4">{error}</p>
                  )}
                  <Button
                    variant="outline"
                    onClick={() => navigate('/dashboard')}
                    className="border-olive-600 text-muted-gray hover:text-gold hover:border-gold"
                  >
                    Back to Dashboard
                  </Button>
                </div>
              )}

              {/* Progress Bar */}
              {isGenerating && (
                <div className="space-y-2 mb-6">
                  <div className="flex justify-between text-xs text-muted-gray">
                    <span>Progress</span>
                    <span className="text-gold font-medium">{Math.round(currentProgress)}%</span>
                  </div>
                  <div className="h-2 bg-olive-700/50 rounded-full overflow-hidden border border-olive-600/50">
                    <motion.div
                      className={`h-full rounded-full ${
                        isFailed
                          ? 'bg-red-500'
                          : isComplete
                            ? 'bg-emerald-500'
                            : 'bg-gradient-gold'
                      }`}
                      initial={{ width: 0 }}
                      animate={{ width: `${currentProgress}%` }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                    >
                      {isGenerating && (
                        <motion.div
                          className="h-full w-1/3 bg-white/30"
                          animate={{ x: ['-100%', '400%'] }}
                          transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                        />
                      )}
                    </motion.div>
                  </div>
                </div>
              )}

              {/* Stats */}
              {isGenerating && (
                <div className="grid grid-cols-2 gap-4 mt-6 pt-6 border-t border-olive-600/50">
                  <div className="text-center">
                    <p className="text-xs text-muted-gray mb-1">Status</p>
                    <p className="text-sm font-semibold text-off-white capitalize">
                      {status.replace(/_/g, ' ')}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted-gray mb-1">Est. Time</p>
                    <p className="text-sm font-semibold text-gold">
                      ~{Math.ceil((100 - currentProgress) / 10)}m
                    </p>
                  </div>
                </div>
              )}

              {/* Info Message */}
              {isGenerating && (
                <div className="mt-6 pt-6 border-t border-olive-600/50">
                  <div className="flex items-start gap-3 p-4 bg-gold/5 border border-gold/20 rounded-lg">
                    <Zap className="w-5 h-5 text-gold flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm text-muted-gray">
                        <strong className="text-gold">Tip:</strong> Generation usually takes 3-10 minutes. You can leave this page and check back later.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>

            {/* Dashboard Button */}
            {!isComplete && !isFailed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="mt-6"
              >
                <Button
                  variant="outline"
                  onClick={() => navigate('/dashboard')}
                  className="border-olive-600 text-muted-gray hover:text-gold hover:border-gold transition-transform duration-200 hover:scale-105"
                >
                  Go to Dashboard
                </Button>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
