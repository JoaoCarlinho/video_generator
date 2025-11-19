import { useRef, useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Play, Pause, Volume2, VolumeX, Download } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import type { AspectRatio } from '@/components/ui/AspectRatioSelector'
import { useVideoElementManager } from '@/utils/videoElementHelpers'

interface VideoPlayerProps {
  videoUrl?: string
  title?: string
  aspect: AspectRatio
  onDownload?: () => void
  isLoading?: boolean
}

export const VideoPlayer = ({
  videoUrl,
  title = 'Video',
  aspect,
  onDownload,
  isLoading = false,
}: VideoPlayerProps) => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  // Initialize defensive video element manager
  const videoManager = useVideoElementManager({ debug: false })

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  const handleTimeUpdate = (e?: Event) => {
    const video = e ? (e.target as HTMLVideoElement) : videoRef.current
    if (video) {
      setCurrentTime(video.currentTime)
    }
  }

  const handleLoadedMetadata = (e?: Event) => {
    const video = e ? (e.target as HTMLVideoElement) : videoRef.current
    if (video) {
      setDuration(video.duration)
    }
  }

  // Defensive listener attachment when video element is available
  useEffect(() => {
    if (!videoRef.current) return

    // Attach listeners defensively to handle cases where the video element
    // might not be immediately available (e.g., dynamic loading)
    const setupListeners = async () => {
      await videoManager.attachListeners(videoRef.current!, {
        onTimeUpdate: handleTimeUpdate,
        onLoadedMetadata: handleLoadedMetadata,
        onEnded: () => setIsPlaying(false),
      })
    }

    setupListeners()

    // Cleanup on unmount
    return () => {
      videoManager.cleanup()
    }
  }, [videoUrl]) // Re-attach when video URL changes

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value)
    setCurrentTime(newTime)
    if (videoRef.current) {
      videoRef.current.currentTime = newTime
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const aspectRatios = {
    '16:9': 'aspect-video',
  }

  return (
    <motion.div
      className="space-y-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Player Container */}
      <div className={`bg-slate-900 rounded-lg overflow-hidden border border-slate-700/50 ${aspectRatios[aspect]}`}>
        {videoUrl ? (
          <div className="relative w-full h-full bg-black group">
            <video
              ref={videoRef}
              src={videoUrl}
              className="w-full h-full"
            />

            {/* Play Button Overlay */}
            {!isPlaying && (
              <motion.button
                onClick={togglePlay}
                className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm"
                whileHover={{ backgroundColor: 'rgba(0, 0, 0, 0.6)' }}
              >
                <div className="w-16 h-16 bg-indigo-600 rounded-full flex items-center justify-center hover:bg-indigo-700 transition-colors">
                  <Play className="w-8 h-8 text-gray-50 fill-gray-50" />
                </div>
              </motion.button>
            )}

            {/* Top Controls */}
            <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="px-3 py-1 bg-black/50 backdrop-blur rounded text-sm text-gray-50 font-medium">
                Horizontal
              </div>
            </div>

            {/* Bottom Controls */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-4 opacity-0 group-hover:opacity-100 transition-opacity">
              {/* Progress Bar */}
              <input
                type="range"
                min="0"
                max={duration || 0}
                value={currentTime}
                onChange={handleProgressChange}
                className="w-full h-1 bg-slate-700 rounded cursor-pointer accent-indigo-600 mb-4"
              />

              {/* Controls */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={togglePlay}
                    className="text-gray-50 hover:bg-white/10 p-1"
                  >
                    {isPlaying ? (
                      <Pause className="w-4 h-4" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                  </Button>

                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={toggleMute}
                    className="text-gray-50 hover:bg-white/10 p-1"
                  >
                    {isMuted ? (
                      <VolumeX className="w-4 h-4" />
                    ) : (
                      <Volume2 className="w-4 h-4" />
                    )}
                  </Button>

                  <span className="text-xs text-gray-50 font-medium">
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>
                </div>

                {onDownload && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={onDownload}
                    className="text-gray-50 hover:bg-white/10 p-1"
                  >
                    <Download className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>
          </div>
        ) : isLoading ? (
          <div className="w-full h-full flex items-center justify-center bg-slate-900">
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 border-3 border-slate-600 border-t-indigo-600 rounded-full animate-spin" />
              <p className="text-slate-400 text-sm">Loading video...</p>
            </div>
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-slate-900">
            <p className="text-slate-400">No video available</p>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex items-center justify-between text-sm">
        <h3 className="text-slate-100 font-medium">{title}</h3>
        <p className="text-slate-500">{aspect}</p>
      </div>
    </motion.div>
  )
}

