import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Container, Header } from '@/components/layout'
import { Button } from '@/components/ui'
import { ProgressTracker } from '@/components/PageComponents'
import { useProgressPolling } from '@/hooks/useProgressPolling'
import { useGeneration } from '@/hooks/useGeneration'
import { ArrowLeft } from 'lucide-react'
import { storeVideo, formatBytes, getStorageUsage } from '@/services/videoStorage'
import { api } from '@/services/api'

export const GenerationProgress = () => {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const { cancelGeneration, generateVideo } = useGeneration()
  const [isCancelling, setIsCancelling] = useState(false)
  const [isStartingGeneration, setIsStartingGeneration] = useState(false)
  // Use ref to track if generation has been started (for this mount cycle)
  const hasStartedGenerationRef = useRef(false)
  // Use sessionStorage key to persist across StrictMode remounts
  const storageKey = `generation_started_${projectId}`

  // Start generation job when component mounts
  useEffect(() => {
    // Skip if already started (check both ref and sessionStorage)
    const alreadyStarted = hasStartedGenerationRef.current || sessionStorage.getItem(storageKey) === 'true'
    
    if (!projectId || alreadyStarted) {
      return
    }

    let isMounted = true

    const startGenerationIfNeeded = async () => {
      // Double-check before starting (prevents race conditions)
      if (!isMounted || hasStartedGenerationRef.current || sessionStorage.getItem(storageKey) === 'true') {
        return
      }
      
      try {
        // Mark as started in both ref and sessionStorage
        hasStartedGenerationRef.current = true
        sessionStorage.setItem(storageKey, 'true')
        setIsStartingGeneration(true)
        console.log('🚀 Starting generation for project:', projectId)
        
        // Queue the job in Redis
        const result = await generateVideo(projectId)
        
        if (isMounted) {
          console.log('✅ Generation queued:', result)
        }
      } catch (err) {
        if (isMounted) {
          console.error('❌ Failed to queue generation:', err)
          // Reset both on error so user can retry
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
    
    // Cleanup: prevent state updates if component unmounts
    return () => {
      isMounted = false
    }
  }, [projectId, generateVideo, storageKey])

  const { progress, isPolling, stopPolling, startPolling } = useProgressPolling({
    projectId,
    enabled: true,
    interval: 2000,
    onComplete: async () => {
      // Clear sessionStorage when generation completes
      sessionStorage.removeItem(storageKey)
      
      // Download video to IndexedDB for preview
      try {
        console.log('📥 Downloading video to local storage...')
        
        // Fetch project to get the aspect_ratio that was generated
        const projectResponse = await api.get(`/api/projects/${projectId}`)
        const project = projectResponse.data
        const projectAspectRatio = project.aspect_ratio || '16:9'
        
        console.log(`📐 Project aspect ratio: ${projectAspectRatio}`)
        
        try {
          // Get video from local disk (NOT S3!)
          const response = await api.get(`/api/projects/${projectId}/preview`, {
            responseType: 'blob'
          })
          
          if (response.data) {
            await storeVideo(projectId, projectAspectRatio as '9:16' | '1:1' | '16:9', response.data, false)
            console.log(`✅ Downloaded video from local storage`)
          }
        } catch (err) {
          console.error(`⚠️ Failed to download video:`, err)
        }
        
        const usage = await getStorageUsage(projectId)
        console.log(`📊 Total local storage used: ${formatBytes(usage)}`)
      } catch (err) {
        console.error('⚠️ Failed to download video to local storage:', err)
      }
      
      // Redirect to results page after download completes
      setTimeout(() => {
        navigate(`/projects/${projectId}/results`)
      }, 1000)
    },
    onError: (error) => {
      console.error('Generation error:', error)
      // Clear sessionStorage on error so user can retry
      sessionStorage.removeItem(storageKey)
    },
  })

  // Clear sessionStorage when status becomes FAILED
  useEffect(() => {
    if (progress?.status === 'FAILED' || progress?.status === 'failed') {
      sessionStorage.removeItem(storageKey)
    }
  }, [progress?.status, storageKey])

  const handleCancel = async () => {
    if (
      !confirm(
        'Are you sure you want to cancel this generation? Your project will be reset.'
      )
    ) {
      return
    }

    try {
      setIsCancelling(true)
      stopPolling()
      // Clear sessionStorage when cancelling
      sessionStorage.removeItem(storageKey)
      hasStartedGenerationRef.current = false
      await cancelGeneration(projectId)
      // Redirect back to dashboard after cancellation
      setTimeout(() => {
        navigate('/dashboard')
      }, 1000)
    } catch (err) {
      console.error('Failed to cancel generation:', err)
      setIsCancelling(false)
      startPolling()
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

  const currentProgress = progress?.progress || 0
  const status = (progress?.status as 'EXTRACTING' | 'PLANNING' | 'GENERATING' | 'COMPOSITING' | 'TEXT_OVERLAY' | 'AUDIO' | 'RENDERING' | 'QUEUED' | 'COMPLETED' | 'FAILED') || 'QUEUED'
  const error = progress?.error

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 flex flex-col">
      {/* Header */}
      <Header
        logo="GenAds"
        title="Generation in Progress"
        actions={
          <button
            onClick={() => navigate('/dashboard')}
            className="text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
        }
      />

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center">
        <Container size="md" className="py-12">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-8"
          >
            {/* Project ID */}
            <motion.div variants={itemVariants} className="text-center">
              <p className="text-slate-500 text-sm">Project ID</p>
              <p className="text-slate-400 font-mono text-xs">{projectId}</p>
            </motion.div>

            {/* Progress Tracker */}
            <motion.div variants={itemVariants}>
              <ProgressTracker
                status={status}
                progress={currentProgress}
                error={error}
                onCancel={handleCancel}
              />
            </motion.div>

            {/* Info Messages */}
            <motion.div
              variants={itemVariants}
              className="space-y-4 text-center"
            >
              {status === 'QUEUED' && (
                <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
                  <p className="text-slate-300 text-sm">
                    ⏳ Your video is queued and will start generating soon...
                  </p>
                </div>
              )}

              {status !== 'COMPLETED' &&
                status !== 'FAILED' &&
                status !== 'QUEUED' && (
                  <>
                    <p className="text-slate-400 text-sm">
                      🎬 Your video is being generated...
                    </p>
                    <p className="text-slate-500 text-xs">
                      This usually takes 3-10 minutes depending on complexity.
                    </p>
                    <p className="text-slate-500 text-xs">
                      Feel free to leave this page and check back later.
                    </p>
                  </>
                )}

              {status === 'COMPLETED' && (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/50 rounded-lg">
                  <p className="text-emerald-400 text-sm font-medium">
                    ✓ Video generation complete! Redirecting...
                  </p>
                </div>
              )}

              {status === 'FAILED' && (
                <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
                  <p className="text-red-400 text-sm font-medium">
                    ✗ Generation failed. Please try again.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate('/dashboard')}
                    className="mt-4"
                  >
                    Back to Dashboard
                  </Button>
                </div>
              )}
            </motion.div>

            {/* Stats */}
            <motion.div
              variants={itemVariants}
              className="grid grid-cols-3 gap-4 text-center"
            >
              <div className="p-4 bg-slate-800/30 border border-slate-700 rounded-lg">
                <p className="text-slate-500 text-xs">Progress</p>
                <p className="text-2xl font-bold text-indigo-400">
                  {Math.round(currentProgress)}%
                </p>
              </div>
              <div className="p-4 bg-slate-800/30 border border-slate-700 rounded-lg">
                <p className="text-slate-500 text-xs">Status</p>
                <p className="text-slate-100 font-semibold capitalize text-sm">
                  {status.replace(/_/g, ' ')}
                </p>
              </div>
              <div className="p-4 bg-slate-800/30 border border-slate-700 rounded-lg">
                <p className="text-slate-500 text-xs">Est. Time Left</p>
                <p className="text-slate-100 font-semibold text-sm">
                  ~{Math.ceil((100 - currentProgress) / 10)}m
                </p>
              </div>
            </motion.div>

            {/* Action Buttons */}
            {!isCancelling && status !== 'COMPLETED' && (
              <motion.div
                variants={itemVariants}
                className="flex gap-4 justify-center pt-4"
              >
                <Button
                  variant="outline"
                  onClick={() => navigate('/dashboard')}
                >
                  Go to Dashboard
                </Button>
                {status !== 'FAILED' && status !== 'QUEUED' && (
                  <Button
                    variant="ghost"
                    onClick={handleCancel}
                    className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                  >
                    Cancel Generation
                  </Button>
                )}
              </motion.div>
            )}
          </motion.div>
        </Container>
      </div>
    </div>
  )
}

