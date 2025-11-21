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
    <div className="scene-card bg-slate-800 rounded-lg p-4 space-y-3 border border-slate-700/50 hover:border-slate-600 transition-colors">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h4 className="text-sm font-semibold text-white">
            Scene {scene.scene_index + 1} - {scene.role.charAt(0).toUpperCase() + scene.role.slice(1)}
          </h4>
          <p className="text-xs text-gray-400">{scene.duration}s</p>
        </div>
        {scene.edit_count > 0 && (
          <span className="text-xs bg-gold/20 text-gold px-2 py-1 rounded border border-gold/30">
            Edited {scene.edit_count}x
          </span>
        )}
      </div>
      
      {/* Thumbnail */}
      <div className="aspect-[9/16] bg-charcoal-900 rounded overflow-hidden border border-slate-700/50">
        {scene.thumbnail_url ? (
          <img 
            src={scene.thumbnail_url} 
            alt={`Scene ${scene.scene_index + 1}`} 
            className="w-full h-full object-cover" 
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-600">
            <Video className="w-8 h-8" />
          </div>
        )}
      </div>
      
      {/* Prompt Preview */}
      <p className="text-xs text-gray-400 line-clamp-2 min-h-[2.5rem]">
        {scene.background_prompt}
      </p>
      
      {/* Edit Button */}
      <Button
        onClick={onEditClick}
        disabled={isEditing}
        variant="outline"
        className="w-full py-2 px-3 bg-slate-700 hover:bg-slate-600 text-white text-sm border-slate-600 hover:border-slate-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isEditing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            Editing...
          </>
        ) : (
          <>
            <Edit2 className="w-4 h-4 mr-2" />
            Edit Scene
          </>
        )}
      </Button>
    </div>
  );
};

