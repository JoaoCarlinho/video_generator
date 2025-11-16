import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Container, Header } from '@/components/layout'
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui'
import { VideoPlayer } from '@/components/PageComponents'
import { useProjects } from '@/hooks/useProjects'
import { api } from '@/services/api'
import { ArrowLeft, Download, Copy, Check, Trash2, Cloud, HardDrive, Lock } from 'lucide-react'
import {
  getVideoURL,
  deleteProjectVideos,
  getStorageUsage,
  formatBytes,
  markAsFinalized,
} from '@/services/videoStorage'

export const VideoResults = () => {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const { getProject } = useProjects()

  const [project, setProject] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aspect, setAspect] = useState<'16:9'>('16:9')
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null)
  const [downloadingAspect, setDownloadingAspect] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  
  // Local storage state
  const [videoUrl, setVideoUrl] = useState<string>('')
  const [storageUsage, setStorageUsage] = useState<number>(0)
  const [isFinalized, setIsFinalized] = useState(false)
  const [isFinalizing, setIsFinalizing] = useState(false)
  const [useLocalStorage, setUseLocalStorage] = useState(true)

  // Load project and videos from local storage
  useEffect(() => {
    const loadProjectAndVideos = async () => {
      try {
        setLoading(true)
        const data = await getProject(projectId)
        setProject(data)
        
        // Try to load video from local storage
        const localVideoUrl = await getVideoURL(projectId, aspect)
        if (localVideoUrl) {
          setVideoUrl(localVideoUrl)
          setUseLocalStorage(true)
          console.log(`✅ Loaded video from local storage for ${aspect}`)
        } else {
          // Fallback to S3 URL if local storage is empty
          setVideoUrl(data.output_videos?.[aspect] || '')
          setUseLocalStorage(false)
        }
        
        // Get storage usage
        const usage = await getStorageUsage(projectId)
        setStorageUsage(usage)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load project'
        setError(message)
      } finally {
        setLoading(false)
      }
    }

    if (projectId) {
      loadProjectAndVideos()
    }
  }, [projectId, getProject, aspect])

  const handleDownload = (aspectRatio: '16:9') => {
    const videoUrl = project.output_videos?.[aspectRatio]
    if (!videoUrl) {
      setError('Video URL not available')
      return
    }

    try {
      setDownloadingAspect(aspectRatio)
      
      // Create a temporary anchor element for download
      const link = document.createElement('a')
      link.href = videoUrl
      
      // Generate filename based on aspect ratio
      const aspectNames: Record<string, string> = {
        '16:9': 'horizontal',
      }
      const resolutions: Record<string, string> = {
        '16:9': '1920x1080',
      }
      
      const timestamp = new Date().toISOString().slice(0, 10)
      const projectTitle = project?.title ? project.title.replace(/\s+/g, '-') : 'video'
      const filename = `${projectTitle}_${aspectNames[aspectRatio]}_${resolutions[aspectRatio]}_${timestamp}.mp4`
      
      link.setAttribute('download', filename)
      link.style.display = 'none'
      
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Clear the downloading state after a short delay
      setTimeout(() => setDownloadingAspect(null), 1000)
    } catch (err) {
      console.error('Download failed:', err)
      setError('Failed to download video')
      setDownloadingAspect(null)
    }
  }

  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url)
    setCopiedUrl(url)
    setTimeout(() => setCopiedUrl(null), 2000)
  }

  // Finalize video: upload to S3 and cleanup local storage
  const handleFinalizeVideo = async () => {
    if (!confirm('Finalize this video? This will upload the final videos to S3 and delete all local files. This action cannot be undone.')) {
      return
    }

    try {
      setIsFinalizing(true)
      setError(null)
      
      console.log('🚀 Finalizing video - uploading to S3...')
      
      // Call backend finalize endpoint
      const response = await api.post(`/api/projects/${projectId}/finalize`)
      
      console.log('✅ Video finalized and uploaded to S3!')
      console.log('📊 S3 URLs:', response.data.output_videos)
      
      // Update local state
      setIsFinalized(true)
      
      // Reload project to get S3 URLs
      const updatedProject = await getProject(projectId)
      setProject(updatedProject)
      
      // Mark as finalized and cleanup IndexedDB
      await markAsFinalized(projectId)
      
      // Delete local storage after 2 seconds
      setTimeout(async () => {
        await deleteProjectVideos(projectId)
        setStorageUsage(0)
        console.log('✅ Local storage cleaned up')
      }, 2000)
      
      // Show success message
      setError(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to finalize video'
      setError(message)
      console.error('❌ Finalization error:', err)
      setIsFinalizing(false)
    }
  }

  // S3 RESTRUCTURING: Delete project and S3 folder
  const handleDeleteProject = async () => {
    if (!confirm('Delete this project? This will remove all videos and project files from storage. This action cannot be undone.')) {
      return
    }

    try {
      setDeleting(true)
      await api.delete(`/api/projects/${projectId}/`)
      // Redirect to dashboard after successful deletion
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete project'
      setError(message)
      setDeleting(false)
    }
  }

  const aspectInfo = {
    '16:9': {
      label: 'Horizontal',
      description: 'YouTube, Web, Presentations',
      icon: '🖥️',
    },
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-3 border-slate-600 border-t-indigo-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading your video...</p>
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 flex flex-col">
        <Header logo="GenAds" title="Video Results" />
        <div className="flex-1 flex items-center justify-center">
          <Container size="md" className="py-12">
            <div className="text-center">
              <p className="text-red-400 font-medium mb-4">{error || 'Project not found'}</p>
              <Button variant="gradient" onClick={() => navigate('/dashboard')}>
                Back to Dashboard
              </Button>
            </div>
          </Container>
        </div>
      </div>
    )
  }

  const cost = project?.cost_estimate || 0

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 flex flex-col">
      {/* Header */}
      <Header
        logo="GenAds"
        title="Video Complete"
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
      <div className="flex-1">
        <Container size="lg" className="py-12">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-8"
          >
            {/* Success Message */}
            <motion.div
              variants={itemVariants}
              className="p-4 bg-emerald-500/10 border border-emerald-500/50 rounded-lg text-center"
            >
              <p className="text-emerald-400 font-medium">
                ✓ Your video is ready!
              </p>
            </motion.div>

            {/* Video Player */}
            <motion.div variants={itemVariants}>
              <Card variant="glass">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle>Preview - {aspectInfo[aspect].label}</CardTitle>
                    {useLocalStorage && (
                      <div className="flex items-center gap-1 px-2 py-1 bg-slate-700/50 rounded text-xs text-slate-300">
                        <HardDrive className="w-3 h-3" />
                        Local
                      </div>
                    )}
                    {!useLocalStorage && (
                      <div className="flex items-center gap-1 px-2 py-1 bg-slate-700/50 rounded text-xs text-slate-400">
                        <Cloud className="w-3 h-3" />
                        S3
                      </div>
                    )}
                  </div>
                  {isFinalized && (
                    <div className="flex items-center gap-1 px-2 py-1 bg-emerald-500/20 rounded text-xs text-emerald-400">
                      <Lock className="w-3 h-3" />
                      Finalized
                    </div>
                  )}
                </CardHeader>
                <CardContent>
                  {videoUrl ? (
                    <VideoPlayer
                      videoUrl={videoUrl}
                      title={project.title}
                      aspect={aspect}
                      onDownload={() => handleDownload(aspect)}
                    />
                  ) : (
                    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-8 text-center">
                      <p className="text-slate-400">No video available</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Local Storage Information */}
            {storageUsage > 0 && (
                <>
                    {!isFinalized && (
                      <Button
                        variant="gradient"
                        onClick={handleFinalizeVideo}
                        disabled={isFinalizing}
                        className="w-full gap-2"
                      >
                        {isFinalizing ? (
                          <>
                            <div className="w-4 h-4 border-2 border-slate-300 border-t-white rounded-full animate-spin" />
                            Finalizing...
                          </>
                        ) : (
                          <>
                            <Cloud className="w-4 h-4" />
                            Finalize
                          </>
                        )}
                      </Button>
                    )}
                    
                    {isFinalized && (
                      <div className="p-3 bg-emerald-500/10 border border-emerald-500/50 rounded-lg">
                        <p className="text-emerald-400 text-sm font-medium">
                          ✓ Video finalized and uploaded to S3
                        </p>
                      </div>
                    )}
                </>
            )}

            {/* Share Section */}
            <motion.div variants={itemVariants}>
              <Card variant="glass">
                <CardHeader>
                  <CardTitle>Share Videos</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(() => {
                    const url = project.output_videos?.['16:9'] || ''
                    if (!url) return null
                    return (
                      <div className="flex items-center gap-2 p-3 bg-slate-800/30 border border-slate-700 rounded-lg">
                        <input
                          type="text"
                          value={url}
                          readOnly
                          className="flex-1 bg-transparent text-slate-400 text-xs font-mono outline-none"
                        />
                        <button
                          onClick={() => handleCopyUrl(url)}
                          className="p-2 hover:bg-slate-700 rounded transition-colors"
                        >
                          {copiedUrl === url ? (
                            <Check className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <Copy className="w-4 h-4 text-slate-400" />
                          )}
                        </button>
                      </div>
                    )
                  })()}
                </CardContent>
              </Card>
            </motion.div>

            {/* Action Buttons */}
            <motion.div
              variants={itemVariants}
              className="flex gap-4 justify-center pt-4 flex-wrap"
            >
              <Button
                variant="outline"
                onClick={() => navigate('/dashboard')}
              >
                Back to Projects
              </Button>
              <Button
                variant="gradient"
                onClick={() => navigate('/create')}
                className="gap-2"
              >
                Create Another
              </Button>
              {/* S3 RESTRUCTURING: Delete project button */}
              <Button
                variant="outline"
                onClick={handleDeleteProject}
                disabled={deleting}
                className="gap-2 border-red-500/50 text-red-400 hover:bg-red-500/10"
              >
                {deleting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete Project
                  </>
                )}
              </Button>
            </motion.div>
          </motion.div>
        </Container>
      </div>
    </div>
  )
}

