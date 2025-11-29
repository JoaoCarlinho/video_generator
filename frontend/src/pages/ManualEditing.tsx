/**
 * ManualEditing Page - Video timeline editor for manual editing
 * Allows users to edit scenes, trim clips, and export final video
 */

import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { motion } from 'framer-motion'
import { Container, Header } from '@/components/layout'
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui'
import { ToastContainer } from '@/components/ui/Toast'
import type { ToastProps } from '@/components/ui/Toast'
import { PreviewPlayer, Timeline, MediaLibrarySidebar } from '@/components/editing'
import { api } from '@/services/api'
import {
  ArrowLeft,
  Save,
  Download,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react'
import {
  setMediaLibrary,
  setTimelineVideoClips,
  setTimelineAudioClips,
  setIsLoading,
  setError,
  resetEditor,
  selectIsLoading,
  selectError,
  selectTimelineState,
  type TimelineClip,
  type MediaLibraryItem,
} from '@/store/slices/editorSlice'

interface Campaign {
  id: string
  name: string
  seasonal_event: string
  year: number
  status: string
  manual_editing_done: boolean
  product_id: string
  product?: {
    name: string
    brand_id: string
    brand?: {
      company_name: string
    }
  }
}

interface SceneInfo {
  scene_index: number
  scene_id: number
  role: string
  duration: number
  background_prompt: string
  video_url: string
  thumbnail_url?: string
}

interface MusicInfo {
  audio_url: string
  duration: number
}

export function ManualEditing() {
  const { campaignId } = useParams<{ campaignId: string }>()
  const navigate = useNavigate()
  const dispatch = useDispatch()

  const isLoading = useSelector(selectIsLoading)
  const error = useSelector(selectError)
  const timelineState = useSelector(selectTimelineState)

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [toasts, setToasts] = useState<ToastProps[]>([])

  // Add toast helper
  const addToast = useCallback((toast: Omit<ToastProps, 'id' | 'onClose'>) => {
    const id = Date.now().toString()
    setToasts(prev => [...prev, { ...toast, id, onClose: () => removeToast(id) }])
  }, [])

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  // Reset editor state on unmount
  useEffect(() => {
    return () => {
      dispatch(resetEditor())
    }
  }, [dispatch])

  // Load campaign data
  useEffect(() => {
    if (!campaignId) return

    const loadCampaign = async () => {
      dispatch(setIsLoading(true))
      dispatch(setError(null))

      try {
        // Fetch campaign details
        const campaignResponse = await api.get(`/api/campaigns/${campaignId}`)
        const campaignData = campaignResponse.data

        // Check if manual editing is already done
        if (campaignData.manual_editing_done) {
          addToast({
            type: 'error',
            message: 'This campaign has already been finalized',
          })
          navigate(`/campaigns/${campaignId}/video`)
          return
        }

        setCampaign(campaignData)

        // Fetch scenes for editing
        const scenesResponse = await api.get(`/api/campaigns/${campaignId}/editing/scenes`)
        const scenes: SceneInfo[] = scenesResponse.data

        // Fetch music for editing
        let music: MusicInfo | null = null
        try {
          const musicResponse = await api.get(`/api/campaigns/${campaignId}/editing/music`)
          music = musicResponse.data
        } catch (err) {
          console.warn('No music available for this campaign')
        }

        // Convert scenes to media library items
        const mediaItems: MediaLibraryItem[] = scenes.map((scene, index) => ({
          id: `scene-${scene.scene_index}`,
          name: `Scene ${scene.scene_index + 1}: ${scene.role}`,
          type: 'video' as const,
          duration: scene.duration,
          url: scene.video_url,
          thumbnailUrl: scene.thumbnail_url,
          sceneIndex: scene.scene_index,
        }))

        // Add music to media library if available
        if (music) {
          mediaItems.push({
            id: 'audio-music',
            name: 'Background Music',
            type: 'audio',
            duration: music.duration,
            url: music.audio_url,
          })
        }

        dispatch(setMediaLibrary(mediaItems))

        // Initialize timeline with scenes in order
        const initialVideoClips: TimelineClip[] = scenes.map((scene, index) => {
          const position = scenes
            .slice(0, index)
            .reduce((acc, s) => acc + s.duration, 0)

          return {
            id: `clip-video-${scene.scene_index}`,
            libraryId: `scene-${scene.scene_index}`,
            name: `Scene ${scene.scene_index + 1}`,
            trackType: 'video',
            duration: scene.duration,
            trimStart: 0,
            trimEnd: 0,
            effectiveDuration: scene.duration,
            position,
            videoUrl: scene.video_url,
          }
        })

        dispatch(setTimelineVideoClips(initialVideoClips))

        // Add music to audio track if available
        if (music) {
          const audioClip: TimelineClip = {
            id: 'clip-audio-music',
            libraryId: 'audio-music',
            name: 'Background Music',
            trackType: 'audio',
            duration: music.duration,
            trimStart: 0,
            trimEnd: 0,
            effectiveDuration: music.duration,
            position: 0,
            audioUrl: music.audio_url,
          }
          dispatch(setTimelineAudioClips([audioClip]))
        }
      } catch (err: any) {
        console.error('Failed to load campaign for editing:', err)
        dispatch(setError(err.response?.data?.detail || 'Failed to load campaign'))
        addToast({
          type: 'error',
          message: err.response?.data?.detail || 'Failed to load campaign for editing',
        })
      } finally {
        dispatch(setIsLoading(false))
      }
    }

    loadCampaign()
  }, [campaignId, dispatch, navigate, addToast])

  // Handle export
  const handleExport = async () => {
    if (!campaignId) return

    setIsSaving(true)

    try {
      // Create a canvas to record the timeline playback
      // For now, we'll use a simpler approach - upload the first scene's video
      // In a full implementation, this would use MediaRecorder to capture canvas playback

      addToast({
        type: 'info',
        message: 'Exporting video... This may take a moment.',
      })

      // Get the video clips' URLs to create a composite
      const videoClips = timelineState.video_clips

      if (videoClips.length === 0) {
        throw new Error('No video clips to export')
      }

      // For MVP: Upload the timeline state and let backend handle composition
      // This is a simplified approach - full implementation would do client-side rendering
      const formData = new FormData()

      // Fetch the first video and upload as a placeholder
      // In production, this would be a properly composed video
      const firstClipUrl = videoClips[0]?.library_id
      const mediaItem = (await api.get(`/api/campaigns/${campaignId}/editing/scenes`)).data[0]

      if (mediaItem?.video_url) {
        // Fetch the video blob
        const videoResponse = await fetch(mediaItem.video_url)
        const videoBlob = await videoResponse.blob()

        formData.append('file', videoBlob, 'edited-video.mp4')

        // Upload to backend
        await api.post(`/api/campaigns/${campaignId}/editing/export-upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
      }

      addToast({
        type: 'success',
        message: 'Video exported successfully!',
      })

      // Navigate back to video results
      setTimeout(() => {
        navigate(`/campaigns/${campaignId}/video`)
      }, 1500)
    } catch (err: any) {
      console.error('Export failed:', err)
      addToast({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to export video',
      })
    } finally {
      setIsSaving(false)
    }
  }

  // Render loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-olive-950 via-olive-900 to-olive-950">
        <Header />
        <Container className="py-8">
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 text-gold-400 animate-spin" />
            <span className="ml-3 text-olive-200">Loading editor...</span>
          </div>
        </Container>
      </div>
    )
  }

  // Render error state
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-olive-950 via-olive-900 to-olive-950">
        <Header />
        <Container className="py-8">
          <Card className="max-w-md mx-auto">
            <CardContent className="p-6 text-center">
              <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <h2 className="text-lg font-semibold text-olive-100 mb-2">
                Error Loading Editor
              </h2>
              <p className="text-olive-300 mb-4">{error}</p>
              <Button
                variant="hero"
                onClick={() => navigate(-1)}
              >
                Go Back
              </Button>
            </CardContent>
          </Card>
        </Container>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-olive-950 via-olive-900 to-olive-950">
      <Header />
      <Container className="py-6">
        {/* Top navigation bar */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-6"
        >
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              onClick={() => navigate(-1)}
              className="text-olive-300 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>

            <div>
              <h1 className="text-xl font-bold text-white">
                Manual Editor
              </h1>
              {campaign && (
                <p className="text-sm text-olive-300">
                  {campaign.name} - {campaign.seasonal_event} {campaign.year}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="hero"
              onClick={handleExport}
              disabled={isSaving}
              className="gap-2"
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Export Video
                </>
              )}
            </Button>
          </div>
        </motion.div>

        {/* Main editor layout */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-12 gap-4"
        >
          {/* Media Library Sidebar */}
          <div className="col-span-3">
            <MediaLibrarySidebar className="h-[calc(100vh-240px)]" />
          </div>

          {/* Main Editor Area */}
          <div className="col-span-9 flex flex-col gap-4">
            {/* Preview Player */}
            <PreviewPlayer className="aspect-video max-h-[400px]" />

            {/* Timeline */}
            <Timeline className="flex-1 min-h-[200px]" />
          </div>
        </motion.div>

        {/* Toast notifications */}
        <ToastContainer toasts={toasts} removeToast={removeToast} />
      </Container>
    </div>
  )
}

export default ManualEditing
