import { useState, useCallback } from 'react';
import { editing } from '../services/api';
import type { SceneInfo, EditHistoryRecord } from '../types';
import { api } from '../services/api';

interface UseSceneEditingReturn {
  scenes: SceneInfo[];
  isLoading: boolean;
  editingSceneIndex: number | null;
  error: string | null;
  loadScenes: (campaignId: string, variationIndex?: number) => Promise<void>;
  editScene: (campaignId: string, sceneIndex: number, editPrompt: string) => Promise<void>;
  getEditHistory: (campaignId: string) => Promise<EditHistoryRecord[]>;
}

export const useSceneEditing = (): UseSceneEditingReturn => {
  const [scenes, setScenes] = useState<SceneInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingSceneIndex, setEditingSceneIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadScenes = useCallback(async (campaignId: string, variationIndex: number = 0) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await editing.getScenes(campaignId, variationIndex);
      setScenes(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load scenes');
      console.error('Error loading scenes:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const pollEditJob = async (jobId: string): Promise<void> => {
    const maxAttempts = 120; // 4 minutes max (2s intervals)
    let attempts = 0;
    
    console.log(`[Edit] Starting to poll job ${jobId}`);
    
    while (attempts < maxAttempts) {
      try {
        const response = await api.get(`/api/generation/jobs/${jobId}/status`);
        const data = response.data;
        
        console.log(`[Edit] Job ${jobId} status:`, data.status, `(attempt ${attempts + 1}/${maxAttempts})`);
        
        // RQ job statuses: queued, started, finished, failed
        if (data.status === 'finished' || data.status === 'completed') {
          console.log(`[Edit] Job ${jobId} completed successfully`);
          return; // Success
        } else if (data.status === 'failed') {
          const errorMsg = data.error || data.result?.error || data.exc_info || 'Edit failed';
          console.error(`[Edit] Job ${jobId} failed:`, errorMsg);
          throw new Error(errorMsg);
        }
        
        // Continue polling for queued/started status
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2s
        attempts++;
      } catch (err: any) {
        // If it's a 404, job might not exist yet - continue polling
        if (err.response?.status === 404 && attempts < 10) {
          console.log(`[Edit] Job ${jobId} not found yet (404), continuing to poll...`);
          await new Promise(resolve => setTimeout(resolve, 2000));
          attempts++;
          continue;
        }
        
        // If it's a real error (not 404 or job failed), throw it
        if (err.response?.status !== 404) {
          console.error(`[Edit] Error polling job ${jobId}:`, err);
          throw err;
        }
        
        // If we've tried many times and still 404, throw
        if (attempts >= 10) {
          throw new Error('Job not found after multiple attempts');
        }
      }
    }
    
    console.error(`[Edit] Job ${jobId} polling timeout after ${maxAttempts} attempts`);
    throw new Error('Edit timeout - please refresh page');
  };

  const editScene = useCallback(async (
    campaignId: string,
    sceneIndex: number,
    editPrompt: string
  ) => {
    setEditingSceneIndex(sceneIndex);
    setError(null);
    
    try {
      // Submit edit request
      const response = await editing.editScene(campaignId, sceneIndex, editPrompt);
      const jobId = response.data.job_id;
      
      // Poll for completion
      await pollEditJob(jobId);
      
      // Reload scenes after successful edit
      await loadScenes(campaignId);
      
      // Clear editing state on success
      setEditingSceneIndex(null);
    } catch (err: any) {
      const errorMessage = err.message || err.response?.data?.detail || 'Failed to edit scene';
      setError(errorMessage);
      console.error('Error editing scene:', err);
      // Clear editing state on error
      setEditingSceneIndex(null);
      throw err;
    }
  }, [loadScenes]);

  const getEditHistory = useCallback(async (campaignId: string): Promise<EditHistoryRecord[]> => {
    try {
      const response = await editing.getEditHistory(campaignId);
      return response.data;
    } catch (err: any) {
      console.error('Error loading edit history:', err);
      return [];
    }
  }, []);

  return {
    scenes,
    isLoading,
    editingSceneIndex,
    error,
    loadScenes,
    editScene,
    getEditHistory
  };
};

