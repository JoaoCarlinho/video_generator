/**
 * PreviewPlayer - Video preview component for the timeline editor
 * Displays video playback with controls synced to the timeline
 */

import React, { useRef, useEffect, useCallback } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { Play, Pause, SkipBack, Volume2, VolumeX } from 'lucide-react'
import { Button } from '../ui/Button'
import {
  selectCurrentTime,
  selectIsPlaying,
  selectTimelineVideoClips,
  selectTimelineTotalDuration,
  setCurrentTime,
  setIsPlaying,
} from '../../store/slices/editorSlice'

interface PreviewPlayerProps {
  className?: string
}

export const PreviewPlayer: React.FC<PreviewPlayerProps> = ({ className = '' }) => {
  const dispatch = useDispatch()
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const currentTime = useSelector(selectCurrentTime)
  const isPlaying = useSelector(selectIsPlaying)
  const videoClips = useSelector(selectTimelineVideoClips)
  const totalDuration = useSelector(selectTimelineTotalDuration)

  const [isMuted, setIsMuted] = React.useState(false)
  const [currentVideoUrl, setCurrentVideoUrl] = React.useState<string | null>(null)

  // Find the active video clip based on current time
  const findActiveClip = useCallback(() => {
    for (const clip of videoClips) {
      const clipStart = clip.position
      const clipEnd = clip.position + clip.effectiveDuration
      if (currentTime >= clipStart && currentTime < clipEnd) {
        return clip
      }
    }
    return videoClips[0] || null
  }, [videoClips, currentTime])

  // Update video source when active clip changes
  useEffect(() => {
    const activeClip = findActiveClip()
    if (activeClip?.videoUrl && activeClip.videoUrl !== currentVideoUrl) {
      setCurrentVideoUrl(activeClip.videoUrl)
    }
  }, [findActiveClip, currentVideoUrl])

  // Sync playback state
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    if (isPlaying) {
      video.play().catch(() => {
        dispatch(setIsPlaying(false))
      })
    } else {
      video.pause()
    }
  }, [isPlaying, dispatch])

  // Animation frame for time updates during playback
  useEffect(() => {
    let animationFrame: number

    const updateTime = () => {
      if (isPlaying && videoRef.current) {
        const newTime = currentTime + (1 / 60) // ~60fps update
        if (newTime < totalDuration) {
          dispatch(setCurrentTime(newTime))
          animationFrame = requestAnimationFrame(updateTime)
        } else {
          dispatch(setCurrentTime(0))
          dispatch(setIsPlaying(false))
        }
      }
    }

    if (isPlaying) {
      animationFrame = requestAnimationFrame(updateTime)
    }

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame)
      }
    }
  }, [isPlaying, currentTime, totalDuration, dispatch])

  const handlePlayPause = () => {
    dispatch(setIsPlaying(!isPlaying))
  }

  const handleRestart = () => {
    dispatch(setCurrentTime(0))
    dispatch(setIsPlaying(false))
  }

  const handleMuteToggle = () => {
    setIsMuted(!isMuted)
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
    }
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className={`flex flex-col bg-olive-900 rounded-lg overflow-hidden ${className}`} ref={containerRef}>
      {/* Video Display */}
      <div className="relative aspect-video bg-black flex items-center justify-center">
        {currentVideoUrl ? (
          <video
            ref={videoRef}
            src={currentVideoUrl}
            className="w-full h-full object-contain"
            muted={isMuted}
            playsInline
            crossOrigin="anonymous"
          />
        ) : (
          <div className="text-olive-400 text-center">
            <p className="text-lg">No video loaded</p>
            <p className="text-sm mt-2">Add scenes to the timeline to preview</p>
          </div>
        )}

        {/* Overlay controls on hover */}
        <div className="absolute inset-0 bg-black/20 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center">
          <Button
            variant="ghost"
            size="icon"
            className="w-16 h-16 rounded-full bg-white/20 hover:bg-white/30"
            onClick={handlePlayPause}
          >
            {isPlaying ? (
              <Pause className="w-8 h-8 text-white" />
            ) : (
              <Play className="w-8 h-8 text-white ml-1" />
            )}
          </Button>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="flex items-center gap-2 p-3 bg-olive-800">
        <Button
          variant="ghost"
          size="icon"
          onClick={handleRestart}
          className="text-olive-200 hover:text-white hover:bg-olive-700"
        >
          <SkipBack className="w-4 h-4" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={handlePlayPause}
          className="text-olive-200 hover:text-white hover:bg-olive-700"
        >
          {isPlaying ? (
            <Pause className="w-4 h-4" />
          ) : (
            <Play className="w-4 h-4" />
          )}
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={handleMuteToggle}
          className="text-olive-200 hover:text-white hover:bg-olive-700"
        >
          {isMuted ? (
            <VolumeX className="w-4 h-4" />
          ) : (
            <Volume2 className="w-4 h-4" />
          )}
        </Button>

        {/* Time display */}
        <div className="flex-1 flex items-center justify-center">
          <span className="text-olive-200 font-mono text-sm">
            {formatTime(currentTime)} / {formatTime(totalDuration)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default PreviewPlayer
