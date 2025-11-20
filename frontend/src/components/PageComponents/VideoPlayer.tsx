import { useRef, useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Play, Pause, Volume2, VolumeX, Download, Maximize, Minimize } from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface VideoPlayerProps {
  videoUrl?: string
  title?: string
  aspect: '9:16' | '1:1' | '16:9'
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
  const containerRef = useRef<HTMLDivElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isVideoReady, setIsVideoReady] = useState(false)

  const togglePlay = () => {
    if (videoRef.current && videoUrl && isVideoReady) {
      if (isPlaying) {
        videoRef.current.pause()
        setIsPlaying(false)
      } else {
        videoRef.current.play().catch((err) => {
          console.error('Failed to play video:', err)
          setIsPlaying(false)
        })
        setIsPlaying(true)
      }
    } else if (!isVideoReady) {
      console.warn('Video not ready yet, cannot play')
    }
  }

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime)
    }
  }

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration)
      setIsVideoReady(true)
      console.log('Video metadata loaded, ready to play')
    }
  }

  const toggleFullscreen = () => {
    if (!containerRef.current) return

    if (!isFullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen()
      } else if ((containerRef.current as any).webkitRequestFullscreen) {
        (containerRef.current as any).webkitRequestFullscreen()
      } else if ((containerRef.current as any).mozRequestFullScreen) {
        (containerRef.current as any).mozRequestFullScreen()
      } else if ((containerRef.current as any).msRequestFullscreen) {
        (containerRef.current as any).msRequestFullscreen()
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen()
      } else if ((document as any).webkitExitFullscreen) {
        (document as any).webkitExitFullscreen()
      } else if ((document as any).mozCancelFullScreen) {
        (document as any).mozCancelFullScreen()
      } else if ((document as any).msExitFullscreen) {
        (document as any).msExitFullscreen()
      }
    }
  }

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!(
        document.fullscreenElement ||
        (document as any).webkitFullscreenElement ||
        (document as any).mozFullScreenElement ||
        (document as any).msFullscreenElement
      ))
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
    document.addEventListener('mozfullscreenchange', handleFullscreenChange)
    document.addEventListener('MSFullscreenChange', handleFullscreenChange)

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange)
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange)
    }
  }, [])

  // Reset video ready state when videoUrl changes
  useEffect(() => {
    setIsVideoReady(false)
    setIsPlaying(false)
  }, [videoUrl])

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
    '9:16': 'aspect-[9/16]',
    '1:1': 'aspect-square',
    '16:9': 'aspect-video',
  }

  const aspectLabels = {
    '9:16': 'Vertical',
    '1:1': 'Square',
    '16:9': 'Horizontal',
  }

  const maxWidthClasses = {
    '9:16': 'max-w-sm sm:max-w-md',
    '1:1': 'max-w-md sm:max-w-lg',
    '16:9': 'max-w-2xl sm:max-w-3xl',
  }

  return (
    <motion.div
      className="space-y-3 w-full"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Player Container */}
      <div 
        ref={containerRef}
        className={`bg-olive-900 overflow-hidden border border-olive-600/50 shadow-gold-lg ${
          isFullscreen 
            ? 'fixed inset-0 z-50 rounded-none border-0 w-screen h-screen' 
            : `rounded-xl ${aspectRatios[aspect]} w-full ${maxWidthClasses[aspect]} mx-auto`
        }`}
      >
        {videoUrl ? (
          <div className={`relative bg-black group ${isFullscreen ? 'w-full h-full' : 'w-full h-full'}`}>
            <video
              ref={videoRef}
              src={videoUrl}
              className={`${isFullscreen ? 'w-full h-full object-contain' : 'w-full h-full'}`}
              preload="metadata"
              playsInline
              crossOrigin="anonymous"
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleLoadedMetadata}
              onEnded={() => setIsPlaying(false)}
              onError={(e) => {
                console.error('❌ Video loading error:', e)
                console.error('❌ Video URL:', videoUrl)
                console.error('❌ Video URL type:', typeof videoUrl)
                console.error('❌ Video URL length:', videoUrl?.length)
                const video = e.currentTarget
                console.error('❌ Video error code:', video.error?.code)
                console.error('❌ Video error message:', video.error?.message)
                console.error('❌ Video network state:', video.networkState)
                console.error('❌ Video ready state:', video.readyState)
                setIsVideoReady(false)
              }}
              onLoadStart={() => {
                console.log('Video loading started:', videoUrl)
                setIsVideoReady(false)
              }}
              onCanPlay={() => {
                setIsVideoReady(true)
                console.log('Video can play:', videoUrl)
              }}
              onLoadedData={() => {
                console.log('Video data loaded:', videoUrl)
              }}
              onStalled={() => {
                console.warn('Video stalled:', videoUrl)
              }}
            />

            {/* Play Button Overlay */}
            {!isPlaying && (
              <motion.button
                onClick={togglePlay}
                className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm"
                whileHover={{ backgroundColor: 'rgba(0, 0, 0, 0.6)' }}
              >
                <motion.div
                  className="w-16 h-16 bg-gold rounded-full flex items-center justify-center shadow-gold-lg"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Play className="w-8 h-8 text-gold-foreground fill-gold-foreground" />
                </motion.div>
              </motion.button>
            )}

            {/* Top Controls */}
            <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="px-3 py-1 bg-black/60 backdrop-blur rounded-lg text-sm text-gold font-semibold border border-gold/30">
                {aspectLabels[aspect]}
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={toggleFullscreen}
                className="text-gold hover:bg-gold/10 p-1.5 rounded-lg bg-black/60 backdrop-blur border border-gold/30"
              >
                {isFullscreen ? (
                  <Minimize className="w-4 h-4" />
                ) : (
                  <Maximize className="w-4 h-4" />
                )}
              </Button>
            </div>

            {/* Bottom Controls */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent p-4 opacity-0 group-hover:opacity-100 transition-opacity">
              {/* Progress Bar */}
              <input
                type="range"
                min="0"
                max={duration || 0}
                value={currentTime}
                onChange={handleProgressChange}
                className="w-full h-1.5 bg-olive-700/50 rounded-full cursor-pointer accent-gold mb-4 appearance-none"
                style={{
                  background: `linear-gradient(to right, #F3D9A4 0%, #F3D9A4 ${(currentTime / (duration || 1)) * 100}%, rgba(93, 107, 90, 0.5) ${(currentTime / (duration || 1)) * 100}%, rgba(93, 107, 90, 0.5) 100%)`
                }}
              />

              {/* Controls */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={togglePlay}
                    className="text-gold hover:bg-gold/10 p-1.5 rounded-lg"
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
                    className="text-gold hover:bg-gold/10 p-1.5 rounded-lg"
                  >
                    {isMuted ? (
                      <VolumeX className="w-4 h-4" />
                    ) : (
                      <Volume2 className="w-4 h-4" />
                    )}
                  </Button>

                  <span className="text-xs text-gold font-medium">
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={toggleFullscreen}
                    className="text-gold hover:bg-gold/10 p-1.5 rounded-lg"
                  >
                    {isFullscreen ? (
                      <Minimize className="w-4 h-4" />
                    ) : (
                      <Maximize className="w-4 h-4" />
                    )}
                  </Button>
                  {onDownload && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={onDownload}
                      className="text-gold hover:bg-gold/10 p-1.5 rounded-lg"
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : isLoading ? (
          <div className="w-full h-full flex items-center justify-center bg-olive-900">
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 border-3 border-olive-600 border-t-gold rounded-full animate-spin" />
              <p className="text-muted-gray text-sm">Loading video...</p>
            </div>
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-olive-900">
            <p className="text-muted-gray">No video available</p>
          </div>
        )}
      </div>
    </motion.div>
  )
}
