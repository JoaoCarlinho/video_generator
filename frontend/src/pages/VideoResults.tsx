import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Container, Header } from '@/components/layout'
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui'
import { VideoPlayer } from '@/components/PageComponents'
import { useProjects } from '@/hooks/useProjects'
import { api } from '@/services/api'
import { ArrowLeft, Copy, Check, Trash2, Cloud, Lock } from 'lucide-react'
import type { AspectRatio } from '@/components/ui/AspectRatioSelector'

export const VideoResults = () => {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const { getProject } = useProjects()

  const [project, setProject] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aspect, setAspect] = useState<AspectRatio>('16:9')
  const [availableAspects, setAvailableAspects] = useState<AspectRatio[]>(['16:9'])
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null)
  const [downloadingAspect, setDownloadingAspect] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  // Video state
  const [videoUrl, setVideoUrl] = useState<string>('')
  const [isFinalized, setIsFinalized] = useState(false)
  const [isFinalizing, setIsFinalizing] = useState(false)

  // Load project and videos from local storage
  useEffect(() => {
    const loadProjectAndVideos = async () => {
      try {
        setLoading(true)
        const data = await getProject(projectId)
        setProject(data)

        // STORY 3 (AC#7): Detect available aspect ratios from local_video_paths or output_videos
        const localPaths = data.local_video_paths || {}
        const outputVideos = data.output_videos || {}
        const aspects = Object.keys({...localPaths, ...outputVideos}) as AspectRatio[]

        if (aspects.length > 0) {
          setAvailableAspects(aspects)
          // Set first available aspect as default if current aspect not available
          if (!aspects.includes(aspect)) {
            setAspect(aspects[0])
          }
        }

        // Load video from S3
        const s3VideoUrl = data.output_videos?.[aspect]
        if (s3VideoUrl) {
          setVideoUrl(s3VideoUrl)
          console.log(`✅ Loaded video from S3 for ${aspect}`)
        } else {
          setVideoUrl('')
          console.log(`⚠️ No video found for ${aspect}`)
        }
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

  const handleDownload = (aspectRatio: string) => {
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

      // STORY 3: Generate filename based on aspect ratio (support all formats)
      const aspectNames: Record<string, string> = {
        '16:9': 'horizontal',
        '9:16': 'vertical',
        '1:1': 'square',
      }
      const resolutions: Record<string, string> = {
        '16:9': '1920x1080',
        '9:16': '1080x1920',
        '1:1': '1080x1080',
      }

      const timestamp = new Date().toISOString().slice(0, 10)
      const projectTitle = project?.title ? project.title.replace(/\s+/g, '-') : 'video'
      const filename = `${projectTitle}_${aspectNames[aspectRatio] || aspectRatio}_${resolutions[aspectRatio] || 'unknown'}_${timestamp}.mp4`

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

  // Finalize video: mark as finalized
  const handleFinalizeVideo = async () => {
    if (!confirm('Finalize this video? This will mark the project as complete and ready for sharing.')) {
      return
    }

    try {
      setIsFinalizing(true)
      setError(null)

      console.log('🚀 Finalizing video...')

      // Call backend finalize endpoint
      const response = await api.post(`/api/projects/${projectId}/finalize`)

      console.log('✅ Video finalized!')

      // Update local state
      setIsFinalized(true)

      // Reload project
      const updatedProject = await getProject(projectId)
      setProject(updatedProject)

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
      await api.delete(`/api/projects/${projectId}`)
      // Redirect to dashboard after successful deletion
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete project'
      setError(message)
      setDeleting(false)
    }
  }

  // STORY 3 (AC#7): Support all aspect ratios
  const aspectInfo: Record<string, { label: string; description: string; icon: string }> = {
    '16:9': {
      label: 'Horizontal',
      description: 'YouTube, Web, Presentations',
      icon: '🖥️',
    },
    '9:16': {
      label: 'Vertical',
      description: 'Instagram Stories, TikTok, Reels',
      icon: '📱',
    },
    '1:1': {
      label: 'Square',
      description: 'Instagram Feed, Facebook, LinkedIn',
      icon: '⬛',
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

            {/* STORY 3 (AC#7): Aspect Ratio Selector */}
            {availableAspects.length > 1 && (
              <motion.div variants={itemVariants}>
                <div className="flex gap-2 justify-center flex-wrap">
                  {availableAspects.map((ar) => (
                    <button
                      key={ar}
                      onClick={() => setAspect(ar)}
                      className={`px-4 py-2 rounded-lg border transition-all ${
                        aspect === ar
                          ? 'bg-indigo-600 border-indigo-500 text-gray-50'
                          : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{aspectInfo[ar]?.icon || '📺'}</span>
                        <div className="text-left">
                          <div className="font-medium">{aspectInfo[ar]?.label || ar}</div>
                          <div className="text-xs opacity-70">{ar}</div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Video Player */}
            <motion.div variants={itemVariants}>
              <Card variant="glass">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle>Preview - {aspectInfo[aspect]?.label || aspect}</CardTitle>
                    <div className="flex items-center gap-1 px-2 py-1 bg-slate-700/50 rounded text-xs text-slate-400">
                      <Cloud className="w-3 h-3" />
                      S3
                    </div>
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

            {/* Finalization Section */}
            {videoUrl && !isFinalized && (
              <motion.div variants={itemVariants}>
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
                      Finalize Project
                    </>
                  )}
                </Button>
              </motion.div>
            )}

            {isFinalized && (
              <motion.div variants={itemVariants}>
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/50 rounded-lg">
                  <p className="text-emerald-400 text-sm font-medium">
                    ✓ Video finalized
                  </p>
                </div>
              </motion.div>
            )}

            {/* STORY 3 (AC#7): Share Section - Show all formats */}
            <motion.div variants={itemVariants}>
              <Card variant="glass">
                <CardHeader>
                  <CardTitle>Share Videos</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {availableAspects.map((ar) => {
                    const url = project.output_videos?.[ar] || ''
                    if (!url) return null
                    return (
                      <div key={ar} className="space-y-1">
                        <div className="text-xs text-slate-400 font-medium">
                          {aspectInfo[ar]?.label || ar} ({ar})
                        </div>
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
                      </div>
                    )
                  })}
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

