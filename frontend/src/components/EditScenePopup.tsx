import React, { useState, useEffect } from 'react';
import type { SceneInfo } from '../types';
import { Modal, Button } from './ui';
import { Loader2 } from 'lucide-react';

interface EditScenePopupProps {
  scene: SceneInfo;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (editPrompt: string) => Promise<void>;
}

export const EditScenePopup: React.FC<EditScenePopupProps> = ({
  scene,
  isOpen,
  onClose,
  onSubmit
}) => {
  const [editPrompt, setEditPrompt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const maxLength = 500;

  useEffect(() => {
    if (!isOpen) {
      // Reset form when popup closes
      setEditPrompt('');
      setError(null);
    }
  }, [isOpen]);

  const handleSubmit = async () => {
    if (!editPrompt.trim()) {
      setError('Please enter an edit instruction');
      return;
    }

    if (editPrompt.length > maxLength) {
      setError(`Edit prompt must be ${maxLength} characters or less`);
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit(editPrompt.trim());
      // Don't close immediately - let the parent handle closing after video updates
      // The popup will be closed by SceneSidebar after successful edit
    } catch (err: any) {
      setError(err.message || 'Failed to submit edit');
      setIsSubmitting(false); // Only reset submitting state on error
      // Don't close on error so user can see the error message
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Edit Scene ${scene.scene_index + 1} - ${scene.role.charAt(0).toUpperCase() + scene.role.slice(1)}`}
      size="md"
      className="bg-slate-800 border-slate-700"
    >
      <div className="space-y-4">
        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            What would you like to change on this scene?
          </label>
          <textarea
            value={editPrompt}
            onChange={(e) => {
              setEditPrompt(e.target.value);
              setError(null);
            }}
            onKeyDown={handleKeyDown}
            placeholder="e.g., 'Make brighter and add golden tones'"
            rows={4}
            maxLength={maxLength}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gold/50 focus:border-gold/50 resize-none"
            disabled={isSubmitting}
          />
          <div className="flex justify-between items-center mt-1">
            <span className="text-xs text-gray-500">
              {editPrompt.length}/{maxLength} characters
            </span>
            {error && (
              <span className="text-xs text-red-400">{error}</span>
            )}
          </div>
        </div>

        {/* Cost and Time Estimate */}
        <div className="p-3 bg-slate-900/50 border border-slate-700 rounded-lg">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Estimated cost:</span>
            <span className="text-gold font-medium">~$0.21</span>
          </div>
          <div className="flex items-center justify-between text-sm mt-1">
            <span className="text-gray-400">Estimated time:</span>
            <span className="text-gray-300">~3 minutes</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            onClick={onClose}
            disabled={isSubmitting}
            variant="outline"
            className="border-slate-600 text-gray-300 hover:bg-slate-700"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !editPrompt.trim()}
            variant="hero"
            className="bg-gold hover:bg-gold-dark text-gold-foreground disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Editing...
              </>
            ) : (
              'Edit Scene'
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

