/**
 * Timeline - Main timeline component for video editing
 * Contains video and audio tracks with clips
 */

import React, { useRef, useCallback } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import {
  selectTimelineVideoClips,
  selectTimelineAudioClips,
  selectTimelineTotalDuration,
  selectCurrentTime,
  setCurrentTime,
} from '../../store/slices/editorSlice'
import { TimelineClip } from './TimelineClip'
import { TrackHeader } from './TrackHeader'

interface TimelineProps {
  className?: string
  pixelsPerSecond?: number
}

export const Timeline: React.FC<TimelineProps> = ({
  className = '',
  pixelsPerSecond = 50,
}) => {
  const dispatch = useDispatch()
  const timelineRef = useRef<HTMLDivElement>(null)

  const videoClips = useSelector(selectTimelineVideoClips)
  const audioClips = useSelector(selectTimelineAudioClips)
  const totalDuration = useSelector(selectTimelineTotalDuration)
  const currentTime = useSelector(selectCurrentTime)

  // Calculate timeline width
  const timelineWidth = Math.max(totalDuration * pixelsPerSecond, 600)

  // Generate time markers
  const timeMarkers = []
  const markerInterval = 1 // seconds
  for (let i = 0; i <= totalDuration + 5; i += markerInterval) {
    timeMarkers.push(i)
  }

  // Handle click on timeline to seek
  const handleTimelineClick = useCallback((e: React.MouseEvent) => {
    const timeline = timelineRef.current
    if (!timeline) return

    const rect = timeline.getBoundingClientRect()
    const x = e.clientX - rect.left + timeline.scrollLeft
    const time = Math.max(0, Math.min(x / pixelsPerSecond, totalDuration))
    dispatch(setCurrentTime(time))
  }, [dispatch, pixelsPerSecond, totalDuration])

  // Format time for display
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className={`flex flex-col bg-olive-900 rounded-lg overflow-hidden ${className}`}>
      {/* Time ruler */}
      <div className="flex border-b border-olive-700">
        <div className="w-24 flex-shrink-0 bg-olive-800" />
        <div
          ref={timelineRef}
          className="flex-1 overflow-x-auto relative h-8 bg-olive-850"
          onClick={handleTimelineClick}
        >
          <div className="relative h-full" style={{ width: timelineWidth }}>
            {/* Time markers */}
            {timeMarkers.map((time) => (
              <div
                key={time}
                className="absolute top-0 h-full flex flex-col items-center"
                style={{ left: time * pixelsPerSecond }}
              >
                <div className="h-2 w-px bg-olive-500" />
                <span className="text-[10px] text-olive-400 mt-1">{formatTime(time)}</span>
              </div>
            ))}

            {/* Playhead */}
            <div
              className="absolute top-0 h-full w-px bg-gold-500 z-10 pointer-events-none"
              style={{ left: currentTime * pixelsPerSecond }}
            >
              <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-gold-500 rotate-45" />
            </div>
          </div>
        </div>
      </div>

      {/* Tracks */}
      <div className="flex-1 overflow-y-auto">
        {/* Video Track */}
        <div className="flex border-b border-olive-700 min-h-[80px]">
          <TrackHeader
            label="Video"
            trackType="video"
            className="w-24 flex-shrink-0"
          />
          <div
            className="flex-1 overflow-x-auto relative bg-olive-850"
            style={{ minWidth: timelineWidth }}
          >
            <div className="relative h-full" style={{ width: timelineWidth }}>
              {videoClips.map((clip) => (
                <TimelineClip
                  key={clip.id}
                  clip={clip}
                  pixelsPerSecond={pixelsPerSecond}
                />
              ))}

              {/* Playhead line */}
              <div
                className="absolute top-0 h-full w-px bg-gold-500/50 z-10 pointer-events-none"
                style={{ left: currentTime * pixelsPerSecond }}
              />
            </div>
          </div>
        </div>

        {/* Audio Track */}
        <div className="flex min-h-[60px]">
          <TrackHeader
            label="Audio"
            trackType="audio"
            className="w-24 flex-shrink-0"
          />
          <div
            className="flex-1 overflow-x-auto relative bg-olive-850"
            style={{ minWidth: timelineWidth }}
          >
            <div className="relative h-full" style={{ width: timelineWidth }}>
              {audioClips.map((clip) => (
                <TimelineClip
                  key={clip.id}
                  clip={clip}
                  pixelsPerSecond={pixelsPerSecond}
                />
              ))}

              {/* Playhead line */}
              <div
                className="absolute top-0 h-full w-px bg-gold-500/50 z-10 pointer-events-none"
                style={{ left: currentTime * pixelsPerSecond }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Timeline
