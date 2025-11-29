/**
 * TrackHeader - Header component for timeline tracks
 * Shows track label and controls
 */

import React from 'react'
import { Eye, EyeOff, Volume2, VolumeX } from 'lucide-react'
import { Button } from '../ui/Button'

interface TrackHeaderProps {
  label: string
  trackType: 'video' | 'audio'
  className?: string
}

export const TrackHeader: React.FC<TrackHeaderProps> = ({
  label,
  trackType,
  className = '',
}) => {
  const [isVisible, setIsVisible] = React.useState(true)
  const [isMuted, setIsMuted] = React.useState(false)

  const isVideo = trackType === 'video'
  const bgColor = isVideo ? 'bg-emerald-900/30' : 'bg-purple-900/30'

  return (
    <div className={`flex flex-col justify-center p-2 bg-olive-800 border-r border-olive-700 ${className}`}>
      {/* Track label */}
      <div className="flex items-center gap-2 mb-1">
        <div className={`w-2 h-2 rounded-full ${isVideo ? 'bg-emerald-500' : 'bg-purple-500'}`} />
        <span className="text-xs font-medium text-olive-200">{label}</span>
      </div>

      {/* Track controls */}
      <div className="flex items-center gap-1">
        {/* Visibility toggle (for video) */}
        {isVideo && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-olive-400 hover:text-white hover:bg-olive-700"
            onClick={() => setIsVisible(!isVisible)}
            title={isVisible ? 'Hide track' : 'Show track'}
          >
            {isVisible ? (
              <Eye className="w-3 h-3" />
            ) : (
              <EyeOff className="w-3 h-3" />
            )}
          </Button>
        )}

        {/* Mute toggle (for audio) */}
        {!isVideo && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-olive-400 hover:text-white hover:bg-olive-700"
            onClick={() => setIsMuted(!isMuted)}
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? (
              <VolumeX className="w-3 h-3" />
            ) : (
              <Volume2 className="w-3 h-3" />
            )}
          </Button>
        )}
      </div>
    </div>
  )
}

export default TrackHeader
