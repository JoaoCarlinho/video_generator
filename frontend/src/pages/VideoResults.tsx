import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { VideoPlayer } from '@/components/PageComponents'
import { SceneSidebar } from '@/components/SceneSidebar'
import { ToastContainer } from '@/components/ui/Toast'
import type { ToastProps } from '@/components/ui/Toast'
import { useProjects } from '@/hooks/useProjects'
import { useCampaigns } from '@/hooks/useCampaigns'
import { api } from '@/services/api'
import { ArrowLeft, Download, Sparkles, Trash2, Cloud, HardDrive, CheckCircle2, Play, Loader2 } from 'lucide-react'
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
  const [selectedVariationIndex, setSelectedVariationIndex] = useState<number>(0)
  const [campaignBlobUrl, setCampaignBlobUrl] = useState<string>('')
  const [isVideoFetching, setIsVideoFetching] = useState<boolean>(false)
  const [storageUsage, setStorageUsage] = useState<number>(0)
  const [isFinalized, setIsFinalized] = useState(false)
  const [isFinalizing, setIsFinalizing] = useState(false)
  const [useLocalStorage, setUseLocalStorage] = useState(true)
  const [isEditingScene, setIsEditingScene] = useState(false)
  const [videoKey, setVideoKey] = useState(0) // Force video reload
  const [toasts, setToasts] = useState<ToastProps[]>([])

  const handleBackToDashboard = () => navigate('/dashboard', { replace: true })

  const addToast = (toast: Omit<ToastProps, 'id'>) => {
    const id = Math.random().toString(36).substring(7)
    setToasts((prev) => [...prev, { ...toast, id }])
  }

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  const handleVideoUpdate = async () => {
    // Called after successful edit
    setIsEditingScene(false)
    
    // Small delay to ensure database update is committed
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // Reload campaign/project data
    try {
      let data: any
      if (isCampaign) {
        // Force reload by adding cache-busting parameter
        data = await getCampaign(id)
        // Reload again to ensure we get fresh data
        await new Promise(resolve => setTimeout(resolve, 300))
        data = await getCampaign(id)
      } else {
        data = await getProject(id)
      }
      setProject(data)
      
      // Clear old video URL first
      if (campaignBlobUrl) {
        URL.revokeObjectURL(campaignBlobUrl)
        setCampaignBlobUrl('')
      }
      setVideoUrl('')
      
      // Reload video
      const aspectRatio = isCampaign ? '9:16' : (data.aspect_ratio || '9:16')
      const { url: displayVideoPath, selectedIndex } = getDisplayVideo(
        data,
        aspectRatio as '9:16' | '1:1' | '16:9'
      )
      setSelectedVariationIndex(selectedIndex)
      
      if (isCampaign && displayVideoPath) {
        // Force reload with cache-busting after edit
        await fetchCampaignVideoBlob(data, aspectRatio as '9:16' | '1:1' | '16:9', selectedIndex, true)
        // Force video player reload by updating key AFTER blob is loaded
        setVideoKey(prev => prev + 1)
      } else {
        // For non-campaigns, just update the key
        setVideoKey(prev => prev + 1)
      }
      
      // Show success toast
      addToast({
        type: 'success',
        title: 'Scene edited successfully!',
        message: 'The video has been updated with your changes.',
        duration: 5000
      })
    } catch (err) {
      console.error('Failed to reload video after edit:', err)
      addToast({
        type: 'error',
        title: 'Failed to reload video',
        message: 'Please refresh the page to see your changes.',
        duration: 5000
      })
    }
  }

  const handleEditStart = () => {
    setIsEditingScene(true)
  }

  const handleEditError = () => {
    // Clear loading state on error
    setIsEditingScene(false)
  }

  /**
   * Helper function to extract the display video path from project/campaign data.
   * Handles both single video (string) and multi-variation (array) cases.
   */
  const getDisplayVideo = (
    data: any,
    aspectRatio: '9:16' | '1:1' | '16:9'
  ): { url: string | null; selectedIndex: number } => {
    if (isCampaign) {
      // Campaign structure: campaign_json.variationPaths
      // Backend stores as object: {"variation_0": {"aspectExports": {"9:16": "url"}}, ...}
      // Handle case where campaign_json might be a string (JSONB serialization)
      let campaignJson = data?.campaign_json || {}
      if (typeof campaignJson === 'string') {
        try {
          campaignJson = JSON.parse(campaignJson)
        } catch (e) {
          console.error('❌ Failed to parse campaign_json:', e)
          return null
        }
      }
      const variationPaths = campaignJson?.variationPaths || {}
      
      console.log('🔍 getDisplayVideo - variationPaths:', variationPaths)
      console.log('🔍 getDisplayVideo - variationPaths type:', typeof variationPaths)
      console.log('🔍 getDisplayVideo - isArray:', Array.isArray(variationPaths))
      
      // Handle both object format (from backend) and array format (legacy)
      let variations: any[] = []
      
      if (Array.isArray(variationPaths)) {
        // Legacy array format
        console.log('📋 Using array format (legacy)')
        variations = variationPaths
      } else if (typeof variationPaths === 'object' && variationPaths !== null) {
        // Current object format: convert to array
        console.log('📋 Using object format, converting to array')
        const keys = Object.keys(variationPaths).sort() // Ensure variation_0, variation_1, variation_2 order
        console.log('📋 Variation keys:', keys)
        variations = keys.map(key => {
          const variation = variationPaths[key]
          console.log(`📋 Variation ${key}:`, variation)
          return variation
        })
      }
      
      console.log('📋 Final variations array:', variations)
      
      if (variations.length === 0) {
        console.warn('⚠️ No variations found')
        return { url: null, selectedIndex: 0 }
      }
      
      // Use selected_variation_index if set, otherwise default to 0
      const selectedIndex = data?.selected_variation_index ?? 0
      console.log('📋 Selected index:', selectedIndex)
      const variation = variations[selectedIndex] || variations[0]
      console.log('📋 Selected variation:', variation)
      
      // Get video URL - check both new format (aspectExports) and legacy format (final_video_url/video_url)
      if (variation?.aspectExports) {
        console.log('📋 aspectExports found:', variation.aspectExports)
        const url = variation.aspectExports[aspectRatio]
        console.log(`📋 URL for ${aspectRatio}:`, url)
        if (url) {
          return { url, selectedIndex }
        }
      }
      // Fallback to legacy format
      const legacyUrl = variation?.final_video_url || variation?.video_url || null
      console.log('📋 Legacy URL:', legacyUrl)
      return { url: legacyUrl, selectedIndex }
    } else {
      // Project structure: ad_project_json.local_video_paths or local_video_paths
      const videoPaths = data?.ad_project_json?.local_video_paths?.[aspectRatio] 
        || data?.local_video_paths?.[aspectRatio]
    
    const selectedIndex = data?.selected_variation_index ?? 0
    if (!videoPaths) {
      return { url: null, selectedIndex }
    }
    
    // If array (multi-variation case)
    if (Array.isArray(videoPaths)) {
      const url = videoPaths[selectedIndex] || videoPaths[0] || null
      return { url, selectedIndex }
    }
    
    // If string (single video case)
    if (typeof videoPaths === 'string') {
      return { url: videoPaths, selectedIndex }
    }
    
    return { url: null, selectedIndex }
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

  const fetchCampaignVideoBlob = async (
    campaignData: any,
    aspectRatio: '9:16' | '1:1' | '16:9',
    variationIndex: number,
    forceReload: boolean = false
  ) => {
    if (!campaignData?.campaign_id) {
      setError('Invalid campaign data')
      return
    }
    try {
      setIsVideoFetching(true)
      
      // Add cache-busting parameter if forcing reload
      const params: any = { variation_index: variationIndex }
      if (forceReload) {
        params._t = Date.now() // Cache-busting timestamp
      }
      
      const response = await api.get(
        `/api/generation/campaigns/${campaignData.campaign_id}/stream/${aspectRatio}`,
        {
          responseType: 'blob',
          params,
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          }
        }
      )
      
      const blobUrl = URL.createObjectURL(response.data)
      setCampaignBlobUrl(blobUrl)
      setVideoUrl(blobUrl)
      setUseLocalStorage(false)
      setError(null)
    } catch (err) {
      console.error('Failed to fetch campaign video blob:', err)
      const message = err instanceof Error ? err.message : 'Failed to load campaign video'
      setError(message)
      setVideoUrl('')
    } finally {
      setIsVideoFetching(false)
    }
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
        const { url: displayVideoPath, selectedIndex } = getDisplayVideo(
          data,
          aspectRatio as '9:16' | '1:1' | '16:9'
        )
        setSelectedVariationIndex(selectedIndex)
        
        console.log('🔍 Campaign data:', data)
        console.log('🔍 Campaign JSON:', data?.campaign_json)
        console.log('🔍 Display video path:', displayVideoPath)
        console.log('🔍 Aspect ratio:', aspectRatio)
        
        if (isCampaign) {
          // Campaigns: videos are in S3, use the URL directly
          if (displayVideoPath) {
            console.log('✅ Using display video path (S3):', displayVideoPath)
            await fetchCampaignVideoBlob(data, aspectRatio as '9:16' | '1:1' | '16:9', selectedIndex)
          } else {
            console.warn('⚠️ No display video path, trying fallback')
            // Fallback: try to get from campaign_json
            let campaignJson = data?.campaign_json || {}
            // Handle case where campaign_json might be a string (JSONB serialization)
            if (typeof campaignJson === 'string') {
              try {
                campaignJson = JSON.parse(campaignJson)
              } catch (e) {
                console.error('❌ Failed to parse campaign_json:', e)
                campaignJson = {}
              }
            }
            const variationPaths = campaignJson?.variationPaths || {}
            
            // Handle both object format (from backend) and array format (legacy)
            let variations: any[] = []
            if (Array.isArray(variationPaths)) {
              variations = variationPaths
            } else if (typeof variationPaths === 'object') {
              variations = Object.keys(variationPaths)
                .sort()
                .map(key => variationPaths[key])
            }
            
            if (variations.length > 0) {
              const selectedIndex = data?.selected_variation_index ?? 0
              const variation = variations[selectedIndex] || variations[0]
              
              console.log('🔍 Selected variation:', variation)
              console.log('🔍 Variation aspectExports:', variation?.aspectExports)
              
              // Get video URL - check both new format (aspectExports) and legacy format
            const videoUrl = variation?.aspectExports?.[aspectRatio] 
                || variation?.final_video_url 
                || variation?.video_url 
                || ''
              
              console.log('🔍 Extracted video URL:', videoUrl)
              
              if (videoUrl) {
              await fetchCampaignVideoBlob(data, aspectRatio as '9:16' | '1:1' | '16:9', selectedIndex)
              } else {
                console.error('❌ No video URL found in variation')
                setError('Video URL not found in campaign data')
              }
            } else {
              console.error('❌ No variations found in campaign_json')
              setError('No video variations found')
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
    return () => {
      if (campaignBlobUrl) {
        URL.revokeObjectURL(campaignBlobUrl)
      }
    }
  }, [campaignBlobUrl])
  
  useEffect(() => {
    const loadVideoForAspect = async () => {
      if (!id || !aspect || !project) return
      
      try {
        if (isCampaign) {
          // Campaigns: fetch video via backend stream to avoid S3 CORS
          const { selectedIndex } = getDisplayVideo(project, aspect)
          setSelectedVariationIndex(selectedIndex)
          await fetchCampaignVideoBlob(project, aspect, selectedIndex)
        } else {
          // Projects: Try IndexedDB first (for videos stored locally in browser)
          const localVideoUrl = await getVideoURL(id, aspect)
        if (localVideoUrl) {
          setVideoUrl(localVideoUrl)
          setUseLocalStorage(true)
        } else {
          // Get the display video path (handles multi-variation selection)
          const { url: displayVideoPath } = getDisplayVideo(project, aspect)
          
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
        // Campaigns: videos are stored in S3 - use direct URL for download
        const { url: displayVideoPath } = getDisplayVideo(project, aspectRatio)
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
        <nav className="border-b border-charcoal-800/60 backdrop-blur-md bg-charcoal-900/70 sticky top-0">
          <div className="max-w-5xl mx-auto w-full px-4 py-4">
            <div className="flex items-center gap-3">
              <button
                onClick={handleBackToDashboard}
                className="p-2 hover:bg-charcoal-800/60 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-muted-gray" />
              </button>
              <span className="text-xl font-bold text-gradient-gold">GenAds</span>
            </div>
          </div>
        </nav>
        <div className="flex-1 flex items-center justify-center px-4">
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
    <div className="min-h-screen bg-gradient-hero flex flex-col">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-32 -right-32 w-72 h-72 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-32 -left-32 w-72 h-72 bg-gold-silky/10 rounded-full blur-3xl"></div>
        <div className="absolute inset-0 bg-gradient-to-br from-gold/5 via-transparent to-transparent" />
      </div>

      {/* Navigation Header */}
      <nav className="relative z-10 border-b border-charcoal-800/60 backdrop-blur-md bg-charcoal-900/70 sticky top-0">
        <div className="max-w-7xl mx-auto w-full px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={handleBackToDashboard}
                className="p-2 hover:bg-charcoal-800/60 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-muted-gray" />
              </button>
              <div className="flex items-center gap-2">
                <div className="p-2 bg-gold rounded-lg shadow-gold">
                  <Sparkles className="h-5 w-5 text-gold-foreground" />
                </div>
                <span className="text-xl font-bold text-gradient-gold hidden sm:inline">GenAds</span>
              </div>
            </div>

            {/* Top Actions */}
            <div className="flex items-center gap-3">
              {isCampaign && project?.perfume_id && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/perfumes/${project.perfume_id}`)}
                  className="hidden sm:flex gap-2 border-olive-600 text-muted-gray hover:text-gold hover:border-gold"
                >
                  <Play className="w-3 h-3" />
                  Back to Campaign Dashboard
                </Button>
              )}
              {!isCampaign && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate('/create')}
                  className="hidden sm:flex gap-2 border-olive-600 text-muted-gray hover:text-gold hover:border-gold"
                >
                  <Play className="w-3 h-3" />
                  Create New
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDeleteProject}
                disabled={deleting}
                className="text-red-400 hover:bg-red-500/10 hover:text-red-300"
              >
                {deleting ? (
                  <div className="w-4 h-4 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="relative z-10 flex-1 w-full max-w-[1600px] mx-auto px-4 py-8">
        <div className={`grid grid-cols-1 ${isCampaign ? 'lg:grid-cols-12' : 'max-w-4xl mx-auto'} gap-8 items-start`}>
          
          {/* LEFT COLUMN: Video Player & Details */}
          <div className={`${isCampaign ? 'lg:col-span-8' : 'w-full'}`}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="w-full bg-charcoal-900/70 backdrop-blur-sm border border-charcoal-800/70 rounded-2xl overflow-hidden shadow-gold-lg flex flex-col"
            >
              {/* Card Header */}
              <div className="p-6 border-b border-charcoal-800/70 flex items-center justify-between bg-charcoal-950/30">
                <div className="flex items-center gap-4">
                  <div className="p-2.5 bg-gold/10 rounded-xl border border-gold/20">
                    <CheckCircle2 className="w-6 h-6 text-gold" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-off-white tracking-tight">
                      {isCampaign ? project.campaign_name : project.title}
                    </h2>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-charcoal-800 text-muted-gray border border-charcoal-700">
                        {aspect === '9:16' ? 'Vertical Story' : aspect === '16:9' ? 'Cinematic Wide' : 'Square Post'}
                      </span>
                      {isFinalized && (
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Finalized
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Primary Actions - Right side of header */}
                <div className="flex items-center gap-3">
                  {!isCampaign && storageUsage > 0 && !isFinalized && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleFinalizeVideo}
                      disabled={isFinalizing}
                      className="border-gold/30 text-gold hover:bg-gold/10 hover:border-gold"
                    >
                      {isFinalizing ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin mr-2" />
                          Finalizing...
                        </>
                      ) : (
                        <>
                          <Cloud className="w-3 h-3 mr-2" />
                          Finalize
                        </>
                      )}
                    </Button>
                  )}
                  
                  <Button
                    variant="hero"
                    onClick={() => handleDownload(aspect)}
                    disabled={!!downloadingAspect}
                    className="gap-2 min-w-[120px]"
                  >
                    {downloadingAspect === aspect ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Download className="w-4 h-4" />
                        Download
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Video Player Container */}
              <div className="p-8 bg-black/20 min-h-[400px] flex items-center justify-center relative">
                {videoUrl ? (
                  <>
                    <div className="w-full max-w-3xl mx-auto shadow-2xl rounded-xl overflow-hidden border border-charcoal-800">
                      <VideoPlayer
                        key={videoKey}
                        videoUrl={videoUrl}
                        title={isCampaign ? project.campaign_name : project.title}
                        aspect={aspect}
                        onDownload={() => handleDownload(aspect)}
                        isLoading={isVideoFetching}
                        size="standard"
                      />
                    </div>
                    
                    {/* Loading Overlay During Edit */}
                    {isEditingScene && (
                      <div className="absolute inset-0 bg-charcoal-950/80 backdrop-blur-sm flex flex-col items-center justify-center z-20">
                        <div className="bg-charcoal-900 border border-gold/30 p-8 rounded-2xl shadow-2xl text-center max-w-md mx-4">
                          <Loader2 className="w-12 h-12 text-gold animate-spin mb-4 mx-auto" />
                          <h3 className="text-xl font-semibold text-white mb-2">
                            Refining Scene...
                          </h3>
                          <p className="text-gray-400 mb-4">
                            AI is regenerating this scene with your new instructions.
                          </p>
                          <div className="w-full bg-charcoal-800 rounded-full h-1.5 mb-2 overflow-hidden">
                            <div className="h-full bg-gold animate-pulse w-2/3 rounded-full"></div>
                          </div>
                          <p className="text-xs text-gray-500">
                            Estimated time: ~2-3 minutes
                          </p>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center text-center p-12 border-2 border-dashed border-charcoal-700 rounded-xl w-full max-w-lg">
                    <div className="p-4 bg-charcoal-800 rounded-full mb-4">
                      <Play className="w-8 h-8 text-muted-gray" />
                    </div>
                    <p className="text-off-white font-medium text-lg mb-1">No video available</p>
                    <p className="text-muted-gray text-sm mb-4">The video could not be loaded.</p>
                    {error && (
                      <p className="text-red-400 text-sm bg-red-500/10 px-3 py-1 rounded-lg border border-red-500/20">{error}</p>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          </div>

          {/* RIGHT COLUMN: Scene Sidebar */}
          {isCampaign && (
            <div className="lg:col-span-4 flex flex-col h-full">
              <div className="sticky top-24">
                <SceneSidebar
                  campaignId={id}
                  variationIndex={selectedVariationIndex}
                  onVideoUpdate={handleVideoUpdate}
                  onEditStart={handleEditStart}
                  onEditError={handleEditError}
                />
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Toast Container */}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </div>
  )
}
