import React, { useState, useEffect } from 'react';
import type { SceneInfo } from '../types';
import { Edit2, Loader2, Video } from 'lucide-react';
import { Button } from './ui';
import { api } from '../services/api';

interface SceneCardProps {
  scene: SceneInfo;
  isEditing: boolean;
  onEditClick: () => void;
  campaignId: string;
  variationIndex?: number;
}

export const SceneCard: React.FC<SceneCardProps> = ({
  scene,
  isEditing,
  onEditClick,
  campaignId,
  variationIndex = 0
}) => {
  const [videoBlobUrl, setVideoBlobUrl] = useState<string | null>(null);
  const [isLoadingVideo, setIsLoadingVideo] = useState(false);
  const [videoError, setVideoError] = useState(false);
  const hasThumbnail = scene.thumbnail_url && scene.thumbnail_url.trim() !== '';
  const hasVideo = scene.video_url && scene.video_url.trim() !== '';

  // Fetch video as blob through backend stream endpoint to avoid CORS issues
  useEffect(() => {
    if (!hasVideo || !campaignId) {
      return;
    }

    let currentBlobUrl: string | null = null;

    const fetchVideoBlob = async () => {
      try {
        setIsLoadingVideo(true);
        setVideoError(false);
        
        const response = await api.get(
          `/api/campaigns/${campaignId}/scenes/${scene.scene_index}/stream`,
          {
            responseType: 'blob',
            params: { variation_index: variationIndex },
            headers: {
              'Cache-Control': 'no-cache',
              'Pragma': 'no-cache'
            }
          }
        );
        
        const blob = new Blob([response.data], { type: response.headers['content-type'] || 'video/mp4' });
        const blobUrl = URL.createObjectURL(blob);
        currentBlobUrl = blobUrl;
        setVideoBlobUrl(blobUrl);
      } catch (err) {
        console.warn('Failed to load scene video:', err);
        setVideoError(true);
      } finally {
        setIsLoadingVideo(false);
      }
    };

    fetchVideoBlob();

    // Cleanup blob URL on unmount or when dependencies change
    return () => {
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
      }
      // Also clean up any existing blob URL in state
      setVideoBlobUrl((prev) => {
        if (prev) {
          URL.revokeObjectURL(prev);
        }
        return null;
      });
    };
  }, [campaignId, scene.scene_index, variationIndex, hasVideo]);

  return (
    <div className="scene-card group bg-slate-800/80 rounded-xl p-3 border border-slate-700/40 hover:border-gold/50 transition-all duration-300 w-full max-w-[320px] shadow-lg/20 flex items-start gap-3">
      {/* Thumbnail/Video Preview */}
      <div className="relative w-20 h-32 bg-charcoal-900 rounded-lg overflow-hidden border border-slate-700/40 group-hover:border-gold/50 transition-colors shrink-0">
        {videoBlobUrl && !videoError ? (
          <>
            {isLoadingVideo && (
              <div className="absolute inset-0 flex items-center justify-center bg-charcoal-900 z-10">
                <div className="w-6 h-6 border-2 border-gold/30 border-t-gold rounded-full animate-spin" />
              </div>
            )}
            <video
              src={videoBlobUrl}
              className={`w-full h-full object-cover group-hover:scale-110 transition-transform duration-300 ${isLoadingVideo ? 'opacity-0' : 'opacity-100'}`}
              muted
              playsInline
              preload="metadata"
              onMouseEnter={(e) => {
                const video = e.currentTarget;
                video.currentTime = 0.5; // Show frame at 0.5s
                video.play().catch(() => {}); // Muted autoplay
              }}
              onMouseLeave={(e) => {
                e.currentTarget.pause();
              }}
              poster={hasThumbnail ? scene.thumbnail_url : undefined}
            />
          </>
        ) : hasThumbnail ? (
          <img
            src={scene.thumbnail_url}
            alt={`Scene ${scene.scene_index + 1}`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-600/70">
            {isLoadingVideo ? (
              <div className="w-6 h-6 border-2 border-gold/30 border-t-gold rounded-full animate-spin" />
            ) : (
              <Video className="w-5 h-5" />
            )}
          </div>
        )}
        {/* Gold ring on hover */}
        <div className="absolute inset-0 border-2 border-gold opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none rounded-lg" />
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col gap-2 min-w-0">
        {/* Header */}
        <div className="flex justify-between items-start gap-2">
          <div className="min-w-0">
            <h4 className="text-xs font-semibold text-white truncate">
              Scene {scene.scene_index + 1} · {scene.role.charAt(0).toUpperCase() + scene.role.slice(1)}
            </h4>
            <p className="text-[10px] text-gray-400">{scene.duration}s</p>
          </div>
          {scene.edit_count > 0 && (
            <span className="text-[10px] bg-gold/10 text-gold px-1.5 py-0.5 rounded-full border border-gold/40 whitespace-nowrap">
              {scene.edit_count}×
            </span>
          )}
        </div>

        {/* Prompt Preview */}
        <p className="text-[11px] text-gray-400 line-clamp-3 min-h-[2.2rem]">
          {scene.background_prompt}
        </p>

        {/* Edit Button */}
        <Button
          onClick={onEditClick}
          disabled={isEditing}
          variant="outline"
          className="py-1 px-2 bg-slate-700/80 hover:bg-slate-600 text-white text-xs border-slate-600/70 hover:border-slate-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed self-start"
        >
          {isEditing ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" />
              Editing...
            </>
          ) : (
            <>
              <Edit2 className="w-3.5 h-3.5 mr-1.5" />
              Edit Scene
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

