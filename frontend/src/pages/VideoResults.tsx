import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { VideoPlayer } from '@/components/PageComponents'
import { useProjects } from '@/hooks/useProjects'
import { api } from '@/services/api'
import { ArrowLeft, Download, Sparkles, Trash2, Cloud, HardDrive, CheckCircle2, Play } from 'lucide-react'
import {
  getVideoURL,
  getVideo,
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
  const [aspect, setAspect] = useState<'9:16' | '1:1' | '16:9'>('16:9')
  const [downloadingAspect, setDownloadingAspect] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  
  const [videoUrl, setVideoUrl] = useState<string>('')
  const [storageUsage, setStorageUsage] = useState<number>(0)
  const [isFinalized, setIsFinalized] = useState(false)
  const [isFinalizing, setIsFinalizing] = useState(false)
  const [useLocalStorage, setUseLocalStorage] = useState(true)

  useEffect(() => {
    const loadProjectAndVideos = async () => {
      try {
        setLoading(true)
        const data = await getProject(projectId)
        setProject(data)
        
        const projectAspectRatio = (data.aspect_ratio || '16:9') as '9:16' | '1:1' | '16:9'
        setAspect(projectAspectRatio)
        
        const localVideoUrl = await getVideoURL(projectId, projectAspectRatio)
        if (localVideoUrl) {
          setVideoUrl(localVideoUrl)
          setUseLocalStorage(true)
        } else {
          setVideoUrl(data.output_videos?.[projectAspectRatio] || '')
          setUseLocalStorage(false)
        }
        
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
  }, [projectId, getProject])
  
  useEffect(() => {
    const loadVideoForAspect = async () => {
      if (!projectId || !aspect) return
      
      try {
        const localVideoUrl = await getVideoURL(projectId, aspect)
        if (localVideoUrl) {
          setVideoUrl(localVideoUrl)
          setUseLocalStorage(true)
        } else {
          const s3Url = project?.output_videos?.[aspect] || ''
          setVideoUrl(s3Url)
          setUseLocalStorage(false)
        }
      } catch (err) {
        console.error(`Failed to load video for ${aspect}:`, err)
      }
    }
    
    if (project) {
      loadVideoForAspect()
    }
  }, [aspect, projectId, project])

  const handleDownload = async (aspectRatio: '9:16' | '1:1' | '16:9') => {
    try {
      setDownloadingAspect(aspectRatio)
      
      const videoBlob = await getVideo(projectId, aspectRatio)
      let videoUrlToDownload: string
      
      if (videoBlob) {
        videoUrlToDownload = URL.createObjectURL(videoBlob)
      } else {
        videoUrlToDownload = project.output_videos?.[aspectRatio] || ''
        if (!videoUrlToDownload) {
          setError('Video URL not available')
          setDownloadingAspect(null)
          return
        }
      }
      
      const link = document.createElement('a')
      link.href = videoUrlToDownload
      
      const aspectNames: Record<string, string> = {
        '9:16': 'vertical',
        '1:1': 'square',
        '16:9': 'horizontal',
      }
      const resolutions: Record<string, string> = {
        '9:16': '1080x1920',
        '1:1': '1080x1080',
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
      
      if (videoBlob && videoUrlToDownload.startsWith('blob:')) {
        URL.revokeObjectURL(videoUrlToDownload)
      }
      
      setTimeout(() => setDownloadingAspect(null), 1000)
    } catch (err) {
      console.error('Download failed:', err)
      setError('Failed to download video')
      setDownloadingAspect(null)
    }
  }

  const handleFinalizeVideo = async () => {
    if (!confirm('Finalize this video? This will upload the final videos to S3 and delete all local files. This action cannot be undone.')) {
      return
    }

    try {
      setIsFinalizing(true)
      setError(null)
      
      const response = await api.post(`/api/projects/${projectId}/finalize`)
      
      setIsFinalized(true)
      
      const updatedProject = await getProject(projectId)
      setProject(updatedProject)
      
      await markAsFinalized(projectId)
      
      setTimeout(async () => {
        await deleteProjectVideos(projectId)
        setStorageUsage(0)
      }, 2000)
      
      setError(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to finalize video'
      setError(message)
      setIsFinalizing(false)
    }
  }

  const handleDeleteProject = async () => {
    if (!confirm('Delete this project? This will remove all videos and project files from storage. This action cannot be undone.')) {
      return
    }

    try {
      setDeleting(true)
      await api.delete(`/api/projects/${projectId}/`)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete project'
      setError(message)
      setDeleting(false)
    }
  }


  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-hero flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-3 border-olive-600 border-t-gold rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-gray">Loading your video...</p>
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gradient-hero flex flex-col">
        <nav className="border-b border-olive-600/50 backdrop-blur-md bg-olive-950/50 sticky top-0">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 hover:bg-olive-800/50 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-muted-gray hover:text-gold" />
              </button>
              <span className="text-xl font-bold text-gradient-gold">GenAds</span>
            </div>
          </div>
        </nav>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-400 font-medium mb-4">{error || 'Project not found'}</p>
            <Button variant="hero" onClick={() => navigate('/dashboard')}>
              Back to Dashboard
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-hero">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gold-silky/10 rounded-full blur-3xl"></div>
        <div className="absolute inset-0 bg-gradient-to-br from-gold/5 via-transparent to-transparent" />
      </div>

      {/* Navigation Header */}
      <nav className="relative z-10 border-b border-olive-600/50 backdrop-blur-md bg-olive-950/50 sticky top-0">
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
            <div className="hidden sm:flex items-center gap-4">
              <h1 className="text-sm font-semibold text-off-white">{project.title}</h1>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-6 max-w-5xl">
          <div className="flex flex-col items-center justify-center min-h-[calc(100vh-120px)]">
            {/* Main Video Card */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="w-full bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-2xl p-4 sm:p-6 shadow-gold-lg"
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gold/10 rounded-lg border border-gold/20">
                    <CheckCircle2 className="w-5 h-5 text-gold" />
                  </div>
                  <div>
                    <h2 className="text-lg sm:text-xl font-bold text-off-white">{project.title}</h2>
                    <div className="flex items-center gap-2 mt-1">
                      {useLocalStorage && (
                        <div className="flex items-center gap-1 px-2 py-0.5 bg-olive-700/30 rounded text-xs text-muted-gray border border-olive-600">
                          <HardDrive className="w-3 h-3" />
                          Local
                        </div>
                      )}
                      {!useLocalStorage && (
                        <div className="flex items-center gap-1 px-2 py-0.5 bg-olive-700/30 rounded text-xs text-muted-gray border border-olive-600">
                          <Cloud className="w-3 h-3" />
                          S3
                        </div>
                      )}
                      {isFinalized && (
                        <div className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 rounded text-xs text-emerald-400 border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          Finalized
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Video Player */}
              <div className="mb-4">
                {videoUrl ? (
                  <VideoPlayer
                    videoUrl={videoUrl}
                    title={project.title}
                    aspect={aspect}
                    onDownload={() => handleDownload(aspect)}
                  />
                ) : (
                  <div className="bg-olive-700/30 border border-olive-600 rounded-xl p-12 text-center">
                    <p className="text-muted-gray">No video available</p>
                  </div>
                )}
              </div>

              {/* Action Buttons Row */}
              <div className="flex items-center gap-3 pt-4 border-t border-olive-600/50">
                <Button
                  variant="hero"
                  onClick={() => handleDownload(aspect)}
                  disabled={!!downloadingAspect}
                  className="gap-2 transition-transform duration-200 hover:scale-105"
                >
                  {downloadingAspect === aspect ? (
                    <>
                      <div className="w-4 h-4 border-2 border-gold-foreground/30 border-t-gold-foreground rounded-full animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      Download
                    </>
                  )}
                </Button>
                
                {storageUsage > 0 && !isFinalized && (
                  <Button
                    variant="outline"
                    onClick={handleFinalizeVideo}
                    disabled={isFinalizing}
                    className="border-gold/30 text-gold hover:bg-gold/10 hover:border-gold transition-transform duration-200 hover:scale-105"
                  >
                    {isFinalizing ? (
                      <>
                        <div className="w-4 h-4 border-2 border-gold/30 border-t-gold rounded-full animate-spin mr-2" />
                        Finalizing...
                      </>
                    ) : (
                      <>
                        <Cloud className="w-4 h-4 mr-2" />
                        Finalize
                      </>
                    )}
                  </Button>
                )}
              </div>

              {isFinalized && (
                <div className="pt-4 border-t border-olive-600/50">
                  <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                    <p className="text-sm text-emerald-400 font-medium flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" />
                      Video finalized and uploaded to S3
                    </p>
                  </div>
                </div>
              )}
            </motion.div>

            {/* Action Buttons */}
            <div className="flex items-center gap-3 mt-6 flex-wrap justify-center">
              <Button
                variant="outline"
                onClick={() => navigate('/dashboard')}
                className="border-olive-600 text-muted-gray hover:text-gold hover:border-gold transition-transform duration-200 hover:scale-105"
              >
                Back to Projects
              </Button>
              <Button
                variant="hero"
                onClick={() => navigate('/create')}
                className="gap-2 transition-transform duration-200 hover:scale-105"
              >
                <Play className="w-4 h-4" />
                Create Another
              </Button>
              <Button
                variant="outline"
                onClick={handleDeleteProject}
                disabled={deleting}
                className="border-red-500/50 text-red-400 hover:bg-red-500/10 hover:border-red-500 transition-transform duration-200 hover:scale-105"
              >
                {deleting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin mr-2" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
