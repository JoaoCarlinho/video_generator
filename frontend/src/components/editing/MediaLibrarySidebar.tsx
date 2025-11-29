/**
 * MediaLibrarySidebar - Sidebar component for media library
 * Shows available scenes and audio for adding to timeline
 */

import React from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { Film, Music, Plus } from 'lucide-react'
import { Button } from '../ui/Button'
import {
  selectMediaLibrary,
  addVideoClip,
  addAudioClip,
  selectTimelineVideoClips,
  selectTimelineAudioClips,
  type TimelineClip,
  type MediaLibraryItem,
} from '../../store/slices/editorSlice'

interface MediaLibrarySidebarProps {
  className?: string
}

export const MediaLibrarySidebar: React.FC<MediaLibrarySidebarProps> = ({
  className = '',
}) => {
  const dispatch = useDispatch()
  const mediaLibrary = useSelector(selectMediaLibrary)
  const videoClips = useSelector(selectTimelineVideoClips)
  const audioClips = useSelector(selectTimelineAudioClips)

  // Separate video and audio items
  const videoItems = mediaLibrary.filter(item => item.type === 'video')
  const audioItems = mediaLibrary.filter(item => item.type === 'audio')

  // Calculate next position for adding clips
  const getNextVideoPosition = (): number => {
    if (videoClips.length === 0) return 0
    const lastClip = videoClips.reduce((a, b) =>
      a.position + a.effectiveDuration > b.position + b.effectiveDuration ? a : b
    )
    return lastClip.position + lastClip.effectiveDuration
  }

  const getNextAudioPosition = (): number => {
    if (audioClips.length === 0) return 0
    const lastClip = audioClips.reduce((a, b) =>
      a.position + a.effectiveDuration > b.position + b.effectiveDuration ? a : b
    )
    return lastClip.position + lastClip.effectiveDuration
  }

  // Add item to timeline
  const handleAddToTimeline = (item: MediaLibraryItem) => {
    const newClip: TimelineClip = {
      id: `clip-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      libraryId: item.id,
      name: item.name,
      trackType: item.type,
      duration: item.duration,
      trimStart: 0,
      trimEnd: 0,
      effectiveDuration: item.duration,
      position: item.type === 'video' ? getNextVideoPosition() : getNextAudioPosition(),
      videoUrl: item.type === 'video' ? item.url : undefined,
      audioUrl: item.type === 'audio' ? item.url : undefined,
    }

    if (item.type === 'video') {
      dispatch(addVideoClip(newClip))
    } else {
      dispatch(addAudioClip(newClip))
    }
  }

  return (
    <div className={`flex flex-col bg-olive-900 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-3 border-b border-olive-700">
        <h3 className="text-sm font-semibold text-olive-100">Media Library</h3>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-2 space-y-4">
        {/* Video Scenes */}
        {videoItems.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Film className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-medium text-olive-300 uppercase tracking-wider">
                Scenes
              </span>
            </div>
            <div className="space-y-2">
              {videoItems.map((item) => (
                <MediaItem
                  key={item.id}
                  item={item}
                  onAdd={() => handleAddToTimeline(item)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Audio */}
        {audioItems.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Music className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-medium text-olive-300 uppercase tracking-wider">
                Audio
              </span>
            </div>
            <div className="space-y-2">
              {audioItems.map((item) => (
                <MediaItem
                  key={item.id}
                  item={item}
                  onAdd={() => handleAddToTimeline(item)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {mediaLibrary.length === 0 && (
          <div className="text-center py-8 text-olive-400">
            <p className="text-sm">No media available</p>
            <p className="text-xs mt-1">Generate a video first</p>
          </div>
        )}
      </div>
    </div>
  )
}

// Individual media item component
interface MediaItemProps {
  item: MediaLibraryItem
  onAdd: () => void
}

const MediaItem: React.FC<MediaItemProps> = ({ item, onAdd }) => {
  const isVideo = item.type === 'video'
  const bgColor = isVideo ? 'bg-emerald-900/30' : 'bg-purple-900/30'
  const hoverColor = isVideo ? 'hover:bg-emerald-900/50' : 'hover:bg-purple-900/50'

  return (
    <div className={`flex items-center gap-2 p-2 rounded ${bgColor} ${hoverColor} transition-colors group`}>
      {/* Thumbnail or icon */}
      <div className={`w-12 h-8 rounded flex items-center justify-center ${isVideo ? 'bg-emerald-800' : 'bg-purple-800'}`}>
        {item.thumbnailUrl ? (
          <img
            src={item.thumbnailUrl}
            alt={item.name}
            className="w-full h-full object-cover rounded"
          />
        ) : isVideo ? (
          <Film className="w-4 h-4 text-emerald-400" />
        ) : (
          <Music className="w-4 h-4 text-purple-400" />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-xs text-olive-100 truncate">{item.name}</p>
        <p className="text-[10px] text-olive-400">{item.duration.toFixed(1)}s</p>
      </div>

      {/* Add button */}
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-olive-300 hover:text-white hover:bg-olive-700"
        onClick={onAdd}
        title="Add to timeline"
      >
        <Plus className="w-3 h-3" />
      </Button>
    </div>
  )
}

export default MediaLibrarySidebar
