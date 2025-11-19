import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { VideoPlayer } from '@/components/PageComponents'
import { useProjects } from '@/hooks/useProjects'
import { useCampaigns } from '@/hooks/useCampaigns'
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

// Get API base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const VideoResults = () => {
  const { projectId, campaignId } = useParams<{ projectId?: string; campaignId?: string }>()
  const navigate = useNavigate()
  const { getProject } = useProjects()
  const { getCampaign, deleteCampaign } = useCampaigns()

  // Use campaignId if available, otherwise fall back to projectId (legacy)
  const id = campaignId || projectId || ''
  const isCampaign = !!campaignId

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

  /**
   * Helper function to extract the display video path from project/campaign data.
   * Handles both single video (string) and multi-variation (array) cases.
   */
  const getDisplayVideo = (data: any, aspectRatio: '9:16' | '1:1' | '16:9'): string | null => {
    if (isCampaign) {
      // Campaign structure: campaign_json.variationPaths
      const campaignJson = data?.campaign_json || {}
      const variationPaths = campaignJson?.variationPaths || []
      
      if (variationPaths.length === 0) {
        return null
      }
      
      // Use selected_variation_index if set, otherwise default to 0
      const selectedIndex = data?.selected_variation_index ?? 0
      const variation = variationPaths[selectedIndex] || variationPaths[0]
      
      // Get video URL for the aspect ratio (campaigns use 9:16 by default)
      return variation?.final_video_url || variation?.video_url || null
    } else {
      // Project structure: ad_project_json.local_video_paths or local_video_paths
      const videoPaths = data?.ad_project_json?.local_video_paths?.[aspectRatio] 
        || data?.local_video_paths?.[aspectRatio]
    
    if (!videoPaths) {
      return null
    }
    
    // If array (multi-variation case)
    if (Array.isArray(videoPaths)) {
      // Use selected_variation_index if set, otherwise default to 0
        const selectedIndex = data?.selected_variation_index ?? 0
      return videoPaths[selectedIndex] || videoPaths[0] || null
    }
    
    // If string (single video case)
    if (typeof videoPaths === 'string') {
      return videoPaths
    }
    
    return null
    }
  }

  /**
   * Helper to convert a local path to a valid API URL if needed.
   */
  const getPlayableVideoUrl = (path: string, entityId: string, variationIndex?: number): string => {
    if (!path) return ''
    
    // If it's already a URL, return as is
    if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('blob:')) {
      return path
    }
    
    // If it's a local file path (starts with /), convert to API endpoint
    if (path.startsWith('/')) {
      if (isCampaign) {
        // Campaign download endpoint
        const variationParam = variationIndex !== undefined ? `?variation=${variationIndex}` : ''
        return `${API_BASE_URL}/api/generation/campaigns/${entityId}/download/9:16${variationParam}`
      } else {
        // Project preview endpoint
      const variationParam = variationIndex !== undefined ? `?variation=${variationIndex}` : ''
        return `${API_BASE_URL}/api/local-generation/projects/${entityId}/preview${variationParam}`
      }
    }
    
    return path
  }

  useEffect(() => {
    const loadProjectAndVideos = async () => {
      try {
        setLoading(true)
        
        let data: any
        if (isCampaign) {
          data = await getCampaign(id)
        } else {
          data = await getProject(id)
        }
        setProject(data)
        
        // Campaigns always use 9:16, projects can have different aspect ratios
        const aspectRatio = isCampaign ? '9:16' : (data.aspect_ratio || '9:16')
        setAspect(aspectRatio as '9:16' | '1:1' | '16:9')
        
        // Get the display video path (handles multi-variation selection)
        const displayVideoPath = getDisplayVideo(data, aspectRatio as '9:16' | '1:1' | '16:9')
        
        if (isCampaign) {
          // Campaigns: videos are in S3, use the URL directly
          if (displayVideoPath) {
            setVideoUrl(displayVideoPath)
            setUseLocalStorage(false)
          } else {
            // Fallback: try to get from campaign_json
            const campaignJson = data?.campaign_json || {}
            const variationPaths = campaignJson?.variationPaths || []
            if (variationPaths.length > 0) {
              const variation = variationPaths[data?.selected_variation_index ?? 0] || variationPaths[0]
              setVideoUrl(variation?.final_video_url || variation?.video_url || '')
              setUseLocalStorage(false)
            }
          }
          setStorageUsage(0) // Campaigns don't use local storage
        } else {
          // Projects: Try IndexedDB first (for videos stored locally in browser)
          const localVideoUrl = await getVideoURL(id, aspectRatio as '9:16' | '1:1' | '16:9')
        if (localVideoUrl) {
          setVideoUrl(localVideoUrl)
          setUseLocalStorage(true)
        } else if (displayVideoPath) {
          // If no IndexedDB video, use the path from project data
          // Convert local path to API URL if necessary
          const playableUrl = getPlayableVideoUrl(
            displayVideoPath, 
              id, 
            data.selected_variation_index ?? undefined
          )
          setVideoUrl(playableUrl)
          setUseLocalStorage(false)
        } else {
          // Fallback to output_videos (S3 URLs)
            setVideoUrl(data.output_videos?.[aspectRatio] || '')
          setUseLocalStorage(false)
        }
        
          const usage = await getStorageUsage(id)
        setStorageUsage(usage)
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : `Failed to load ${isCampaign ? 'campaign' : 'project'}`
        setError(message)
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      loadProjectAndVideos()
    }
  }, [id, isCampaign, getProject, getCampaign])
  
  useEffect(() => {
    const loadVideoForAspect = async () => {
      if (!id || !aspect || !project) return
      
      try {
        if (isCampaign) {
          // Campaigns: videos are in S3, aspect ratio is always 9:16
          const displayVideoPath = getDisplayVideo(project, aspect)
          if (displayVideoPath) {
            setVideoUrl(displayVideoPath)
            setUseLocalStorage(false)
          }
        } else {
          // Projects: Try IndexedDB first (for videos stored locally in browser)
          const localVideoUrl = await getVideoURL(id, aspect)
        if (localVideoUrl) {
          setVideoUrl(localVideoUrl)
          setUseLocalStorage(true)
        } else {
          // Get the display video path (handles multi-variation selection)
          const displayVideoPath = getDisplayVideo(project, aspect)
          
          if (displayVideoPath) {
            // Use the path from project data (could be local file path or S3 URL)
            const playableUrl = getPlayableVideoUrl(
              displayVideoPath, 
                id, 
              project.selected_variation_index ?? undefined
            )
            setVideoUrl(playableUrl)
            setUseLocalStorage(false)
          } else {
            // Fallback to output_videos (S3 URLs)
            const s3Url = project?.output_videos?.[aspect] || ''
            setVideoUrl(s3Url)
            setUseLocalStorage(false)
            }
          }
        }
      } catch (err) {
        console.error(`Failed to load video for ${aspect}:`, err)
      }
    }
    
    if (project) {
      loadVideoForAspect()
    }
  }, [aspect, id, project, isCampaign])

  const handleDownload = async (aspectRatio: '9:16' | '1:1' | '16:9') => {
    try {
      setDownloadingAspect(aspectRatio)
      
      let videoUrlToDownload: string
      
      if (isCampaign) {
        // Campaigns: videos are in S3, download directly from URL
        const displayVideoPath = getDisplayVideo(project, aspectRatio)
        videoUrlToDownload = displayVideoPath || ''
        
        if (!videoUrlToDownload) {
          setError('Video URL not available')
          setDownloadingAspect(null)
          return
        }
      } else {
        // Projects: Try local storage first, then S3
        const videoBlob = await getVideo(id, aspectRatio)
      
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
      const entityTitle = isCampaign 
        ? (project?.campaign_name || 'campaign').replace(/\s+/g, '-')
        : (project?.title || 'video').replace(/\s+/g, '-')
      const filename = `${entityTitle}_${aspectNames[aspectRatio]}_${resolutions[aspectRatio]}_${timestamp}.mp4`
      
      link.setAttribute('download', filename)
      link.style.display = 'none'
      
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      if (videoUrlToDownload.startsWith('blob:')) {
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
      
      if (isCampaign) {
        // Campaigns are already finalized (videos in S3)
        setIsFinalized(true)
        setError(null)
      } else {
        const response = await api.post(`/api/projects/${id}/finalize`)
      
      setIsFinalized(true)
      
        const updatedProject = await getProject(id)
      setProject(updatedProject)
      
        await markAsFinalized(id)
      
      setTimeout(async () => {
          await deleteProjectVideos(id)
        setStorageUsage(0)
      }, 2000)
      
      setError(null)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to finalize video'
      setError(message)
      setIsFinalizing(false)
    }
  }

  const handleDeleteProject = async () => {
    if (!confirm(`Delete this ${isCampaign ? 'campaign' : 'project'}? This will remove all videos and ${isCampaign ? 'campaign' : 'project'} files from storage. This action cannot be undone.`)) {
      return
    }

    try {
      setDeleting(true)
      if (isCampaign) {
        await deleteCampaign(id)
      } else {
        await api.delete(`/api/projects/${id}/`)
      }
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const message = err instanceof Error ? `Failed to delete ${isCampaign ? 'campaign' : 'project'}` : 'Failed to delete'
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
            <p className="text-red-400 font-medium mb-4">{error || `${isCampaign ? 'Campaign' : 'Project'} not found`}</p>
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
              <h1 className="text-sm font-semibold text-off-white">
                {isCampaign ? project.campaign_name : project.title}
              </h1>
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
                    <h2 className="text-lg sm:text-xl font-bold text-off-white">
                      {isCampaign ? project.campaign_name : project.title}
                    </h2>
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
                    title={isCampaign ? project.campaign_name : project.title}
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
                
                {!isCampaign && storageUsage > 0 && !isFinalized && (
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
                {isCampaign && (
                  <div className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 rounded text-xs text-emerald-400 border border-emerald-500/30">
                    <CheckCircle2 className="w-3 h-3" />
                    Finalized
                  </div>
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
                Back to {isCampaign ? 'Dashboard' : 'Projects'}
              </Button>
              {isCampaign && project?.perfume_id && (
                <Button
                  variant="hero"
                  onClick={() => navigate(`/perfumes/${project.perfume_id}`)}
                  className="gap-2 transition-transform duration-200 hover:scale-105"
                >
                  <Play className="w-4 h-4" />
                  Back to Perfume
                </Button>
              )}
              {!isCampaign && (
              <Button
                variant="hero"
                onClick={() => navigate('/create')}
                className="gap-2 transition-transform duration-200 hover:scale-105"
              >
                <Play className="w-4 h-4" />
                Create Another
              </Button>
              )}
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
