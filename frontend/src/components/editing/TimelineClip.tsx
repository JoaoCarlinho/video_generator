/**
 * TimelineClip - Individual clip component on the timeline
 * Displays clip with visual representation and handles selection
 */

import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Film, Music } from 'lucide-react'
import {
  type TimelineClip as TimelineClipType,
  setSelectedClipId,
  selectSelectedClipId,
} from '../../store/slices/editorSlice'

interface TimelineClipProps {
  clip: TimelineClipType
  pixelsPerSecond: number
}

export const TimelineClip: React.FC<TimelineClipProps> = ({
  clip,
  pixelsPerSecond,
}) => {
  const dispatch = useDispatch()
  const selectedClipId = useSelector(selectSelectedClipId)

  const isSelected = selectedClipId === clip.id
  const isVideo = clip.trackType === 'video'

  // Calculate dimensions
  const width = clip.effectiveDuration * pixelsPerSecond
  const left = clip.position * pixelsPerSecond

  // Clip colors
  const bgColor = isVideo
    ? isSelected
      ? 'bg-emerald-600'
      : 'bg-emerald-700'
    : isSelected
    ? 'bg-purple-600'
    : 'bg-purple-700'

  const borderColor = isSelected ? 'ring-2 ring-gold-400' : ''

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    dispatch(setSelectedClipId(isSelected ? null : clip.id))
  }

  return (
    <div
      className={`absolute top-1 bottom-1 rounded cursor-pointer ${bgColor} ${borderColor}
                  transition-all hover:brightness-110 overflow-hidden`}
      style={{
        left: `${left}px`,
        width: `${Math.max(width, 20)}px`,
      }}
      onClick={handleClick}
    >
      {/* Clip content */}
      <div className="flex items-center h-full px-2 gap-1">
        {/* Icon */}
        <div className="flex-shrink-0">
          {isVideo ? (
            <Film className="w-3 h-3 text-white/70" />
          ) : (
            <Music className="w-3 h-3 text-white/70" />
          )}
        </div>

        {/* Clip name - only show if width allows */}
        {width > 60 && (
          <span className="text-xs text-white truncate">
            {clip.name}
          </span>
        )}
      </div>

      {/* Waveform pattern for audio */}
      {!isVideo && (
        <div className="absolute inset-0 opacity-20 pointer-events-none">
          <svg width="100%" height="100%" preserveAspectRatio="none">
            <pattern id={`wave-${clip.id}`} width="10" height="100%" patternUnits="userSpaceOnUse">
              <rect x="0" y="40%" width="2" height="20%" fill="white" />
              <rect x="4" y="30%" width="2" height="40%" fill="white" />
              <rect x="8" y="35%" width="2" height="30%" fill="white" />
            </pattern>
            <rect width="100%" height="100%" fill={`url(#wave-${clip.id})`} />
          </svg>
        </div>
      )}

      {/* Trim handles - only show when selected */}
      {isSelected && (
        <>
          <div
            className="absolute left-0 top-0 bottom-0 w-1 bg-gold-400 cursor-ew-resize"
            title="Trim start"
          />
          <div
            className="absolute right-0 top-0 bottom-0 w-1 bg-gold-400 cursor-ew-resize"
            title="Trim end"
          />
        </>
      )}

      {/* Duration tooltip */}
      {isSelected && (
        <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-olive-800 text-white text-[10px] px-2 py-0.5 rounded whitespace-nowrap">
          {clip.effectiveDuration.toFixed(1)}s
        </div>
      )}
    </div>
  )
}

export default TimelineClip
