import React from 'react';
import type { SceneInfo } from '../types';
import { Edit2, Loader2, Video } from 'lucide-react';
import { Button } from './ui';

interface SceneCardProps {
  scene: SceneInfo;
  isEditing: boolean;
  onEditClick: () => void;
}

export const SceneCard: React.FC<SceneCardProps> = ({
  scene,
  isEditing,
  onEditClick
}) => {
  return (
    <div className="scene-card bg-slate-800/80 rounded-xl p-3 border border-slate-700/40 hover:border-slate-500/50 transition-colors w-full max-w-[320px] shadow-lg/20 flex items-start gap-3">
      {/* Thumbnail */}
      <div className="w-20 h-32 bg-charcoal-900 rounded-lg overflow-hidden border border-slate-700/40 shrink-0">
        {scene.thumbnail_url ? (
          <img
            src={scene.thumbnail_url}
            alt={`Scene ${scene.scene_index + 1}`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-600/70">
            <Video className="w-5 h-5" />
          </div>
        )}
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

