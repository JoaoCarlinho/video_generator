import React, { useState, useEffect } from 'react';
import { useSceneEditing } from '../hooks/useSceneEditing';
import { SceneCard } from './SceneCard';
import { EditScenePopup } from './EditScenePopup';
import { Loader2 } from 'lucide-react';

interface SceneSidebarProps {
  campaignId: string;
  variationIndex?: number;
  onVideoUpdate: () => void;
  onEditStart?: () => void;
  onEditError?: () => void;
  className?: string;
}

export const SceneSidebar: React.FC<SceneSidebarProps> = ({
  campaignId,
  variationIndex = 0,
  onVideoUpdate,
  onEditStart,
  onEditError,
  className
}) => {
  const {
    scenes,
    isLoading,
    editingSceneIndex,
    error,
    loadScenes,
    editScene
  } = useSceneEditing();
  
  const [popupSceneIndex, setPopupSceneIndex] = useState<number | null>(null);
  
  useEffect(() => {
    if (campaignId) {
      loadScenes(campaignId, variationIndex);
    }
  }, [campaignId, variationIndex, loadScenes]);
  
  const handleEditSubmit = async (sceneIndex: number, editPrompt: string) => {
    try {
      // Notify parent that editing has started
      if (onEditStart) {
        onEditStart();
      }
      
      // Close popup immediately when edit starts (polling happens in background)
      setPopupSceneIndex(null);
      
      // Edit scene (this will poll for completion)
      await editScene(campaignId, sceneIndex, editPrompt);
      
      // After successful edit, refresh scenes and update video
      await loadScenes(campaignId, variationIndex); // Refresh scenes
      onVideoUpdate(); // Tell parent to reload video and clear loading state
    } catch (error) {
      // Error handling - clear loading state on error
      console.error('Edit submission failed:', error);
      // Notify parent to clear loading state
      if (onEditError) {
        onEditError();
      }
      // Re-open popup to show error
      setPopupSceneIndex(sceneIndex);
      throw error; // Re-throw so popup can show error
    }
  };
  
  if (isLoading && scenes.length === 0) {
    return (
      <div className={`scene-sidebar w-full bg-charcoal-900/70 backdrop-blur-sm border border-charcoal-800/70 rounded-lg p-6 ${className}`}>
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-6 h-6 text-gold animate-spin" />
            <div className="text-gray-400">Loading scenes...</div>
          </div>
        </div>
      </div>
    );
  }
  
  if (error && scenes.length === 0) {
    return (
      <div className={`scene-sidebar w-full bg-charcoal-900/70 backdrop-blur-sm border border-charcoal-800/70 rounded-lg p-6 ${className}`}>
        <div className="text-red-400 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="font-medium mb-1">Error loading scenes</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }
  
  return (
    <>
      <div className={`scene-sidebar w-full bg-charcoal-900/70 backdrop-blur-sm border border-charcoal-800/70 rounded-2xl p-4 sm:p-6 flex flex-col shadow-gold-lg h-full ${className}`}>
        {/* Header */}
        <div className="flex justify-between items-center pb-4 border-b border-charcoal-800/70 mb-4 flex-shrink-0">
          <h3 className="text-lg font-semibold text-white">
            Scenes ({scenes.length})
          </h3>
        </div>
        
        {/* Scene List - Scrollable */}
        <div className="space-y-4 overflow-y-auto overflow-x-hidden pr-2 flex-1 min-h-0">
          {scenes.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <p>No scenes available</p>
            </div>
          ) : (
            scenes.map((scene) => (
              <SceneCard
                key={scene.scene_index}
                scene={scene}
                isEditing={editingSceneIndex === scene.scene_index}
                onEditClick={() => setPopupSceneIndex(scene.scene_index)}
                campaignId={campaignId}
                variationIndex={variationIndex}
              />
            ))
          )}
        </div>
      </div>
      
      {/* Edit Popup */}
      {popupSceneIndex !== null && scenes[popupSceneIndex] && (
        <EditScenePopup
          scene={scenes[popupSceneIndex]}
          isOpen={popupSceneIndex !== null}
          onClose={() => setPopupSceneIndex(null)}
          onSubmit={(prompt) => handleEditSubmit(popupSceneIndex, prompt)}
        />
      )}
    </>
  );
};

