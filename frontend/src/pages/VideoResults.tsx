import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Container, Header } from '@/components/layout'
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui'
import { VideoPlayer } from '@/components/PageComponents'
import { useProjects } from '@/hooks/useProjects'
import { api } from '@/services/api'
import { ArrowLeft, Download, Copy, Check, Trash2 } from 'lucide-react'

export const VideoResults = () => {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const { getProject } = useProjects()

  const [project, setProject] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aspect, setAspect] = useState<'9:16' | '1:1' | '16:9'>('9:16')
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null)
  const [downloadingAspect, setDownloadingAspect] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    const fetchProject = async () => {
      try {
        setLoading(true)
        const data = await getProject(projectId)
        setProject(data)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load project'
        setError(message)
      } finally {
        setLoading(false)
      }
    }

    if (projectId) {
      fetchProject()
    }
  }, [projectId, getProject])

  const handleDownload = (aspectRatio: '9:16' | '1:1' | '16:9') => {
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
    '9:16': {
      label: 'Vertical',
      description: 'Perfect for TikTok, Reels, Shorts',
      icon: '📱',
    },
    '1:1': {
      label: 'Square',
      description: 'Great for Instagram Feed',
      icon: '⬜',
    },
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

  const videoUrl = project.output_videos?.[aspect] || ''
  const cost = project.cost_estimate || 0

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
                ✓ Your video is ready! All 3 aspect ratios are available.
              </p>
            </motion.div>

            {/* Video Player */}
            <motion.div variants={itemVariants}>
              <Card variant="glass">
                <CardHeader>
                  <CardTitle>Preview - {aspectInfo[aspect].label}</CardTitle>
                </CardHeader>
                <CardContent>
                  <VideoPlayer
                    videoUrl={videoUrl}
                    title={project.title}
                    aspect={aspect}
                    onDownload={() => handleDownload(aspect)}
                  />
                </CardContent>
              </Card>
            </motion.div>

            {/* Aspect Ratio Selector */}
            <motion.div variants={itemVariants}>
              <div className="space-y-4">
                <h3 className="font-semibold text-slate-100">Choose Format</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {(['9:16', '1:1', '16:9'] as const).map((ar) => (
                    <motion.button
                      key={ar}
                      onClick={() => setAspect(ar)}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        aspect === ar
                          ? 'border-indigo-500 bg-indigo-500/10'
                          : 'border-slate-700 hover:border-slate-600 bg-slate-800/30'
                      }`}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <div className="text-2xl mb-2">
                        {aspectInfo[ar].icon}
                      </div>
                      <p className="font-semibold text-slate-100">
                        {aspectInfo[ar].label}
                      </p>
                      <p className="text-xs text-slate-400 mt-1">
                        {aspectInfo[ar].description}
                      </p>
                    </motion.button>
                  ))}
                </div>
              </div>
            </motion.div>

            {/* Download Section */}
            <motion.div variants={itemVariants}>
              <Card variant="glass">
                <CardHeader>
                  <CardTitle>Download Videos</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(['9:16', '1:1', '16:9'] as const).map((ar) => (
                    <div
                      key={ar}
                      className="flex items-center justify-between p-4 bg-slate-800/30 border border-slate-700 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-slate-100">
                          {aspectInfo[ar].label}
                        </p>
                        <p className="text-xs text-slate-400">
                          {ar === '9:16'
                            ? '1080×1920'
                            : ar === '1:1'
                              ? '1080×1080'
                              : '1920×1080'}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="gradient"
                        onClick={() => handleDownload(ar)}
                        disabled={downloadingAspect === ar}
                        className="gap-2"
                      >
                        {downloadingAspect === ar ? (
                          <>
                            <div className="w-4 h-4 border-2 border-slate-300 border-t-white rounded-full animate-spin" />
                            Downloading...
                          </>
                        ) : (
                          <>
                            <Download className="w-4 h-4" />
                            Download
                          </>
                        )}
                      </Button>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </motion.div>

            {/* S3 Folder Information */}
            {project.s3_project_folder_url && (
              <motion.div variants={itemVariants}>
                <Card variant="glass">
                  <CardHeader>
                    <CardTitle className="text-sm">📁 Project Storage</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-slate-400 mb-2">S3 Project Folder:</p>
                    <div className="flex items-center gap-2 p-2 bg-slate-900/50 border border-slate-700 rounded">
                      <input
                        type="text"
                        value={project.s3_project_folder_url}
                        readOnly
                        className="flex-1 bg-transparent text-slate-300 text-xs font-mono outline-none truncate"
                      />
                      <button
                        onClick={() => handleCopyUrl(project.s3_project_folder_url)}
                        className="p-1.5 hover:bg-slate-700 rounded transition-colors flex-shrink-0"
                      >
                        {copiedUrl === project.s3_project_folder_url ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3 text-slate-400" />
                        )}
                      </button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Project Details */}
            <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Details Card */}
              <Card variant="outlined">
                <CardHeader>
                  <CardTitle className="text-lg">Project Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div>
                    <p className="text-slate-500">Title</p>
                    <p className="text-slate-100 font-medium">{project.title}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Brand</p>
                    <p className="text-slate-100 font-medium">
                      {project.brand_name}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Duration</p>
                    <p className="text-slate-100 font-medium">
                      {project.duration} seconds
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Mood</p>
                    <Badge variant="secondary" className="capitalize">
                      {project.mood ? project.mood.replace(/_/g, ' ') : 'N/A'}
                    </Badge>
                  </div>
                </CardContent>
              </Card>

              {/* Cost & Stats Card */}
              <Card variant="outlined">
                <CardHeader>
                  <CardTitle className="text-lg">Generation Stats</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div>
                    <p className="text-slate-500">Total Cost</p>
                    <p className="text-2xl font-bold text-indigo-400">
                      ${cost.toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Created</p>
                    <p className="text-slate-100">
                      {new Date(project.created_at).toLocaleDateString()} at{' '}
                      {new Date(project.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Status</p>
                    <Badge variant="success" className="capitalize">
                      {project.status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Share Section */}
            <motion.div variants={itemVariants}>
              <Card variant="glass">
                <CardHeader>
                  <CardTitle>Share Videos</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(['9:16', '1:1', '16:9'] as const).map((ar) => {
                    const url = project.output_videos?.[ar] || ''
                    if (!url) return null
                    return (
                      <div
                        key={ar}
                        className="flex items-center gap-2 p-3 bg-slate-800/30 border border-slate-700 rounded-lg"
                      >
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

