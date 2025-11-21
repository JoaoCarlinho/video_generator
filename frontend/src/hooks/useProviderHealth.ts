/**
 * useProviderHealth Hook
 * Polls provider health status to enable/disable provider selection dynamically
 *
 * Story 5.2: Add Provider Health Polling Hook
 */

import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/services/api';

export interface HealthStatus {
  provider: string;
  healthy: boolean;
  message: string;
}

export interface ProviderHealthResponse {
  replicate: HealthStatus;
  ecs: HealthStatus;
}

export interface UseProviderHealthReturn {
  replicate: HealthStatus;
  ecs: HealthStatus;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

const POLL_INTERVAL = 30000; // 30 seconds
const RETRY_DELAY = 5000; // 5 seconds on error

// Default health status (fallback when API isn't available)
const DEFAULT_HEALTH: ProviderHealthResponse = {
  replicate: {
    provider: 'replicate',
    healthy: true,
    message: 'Replicate Cloud API is always available',
  },
  ecs: {
    provider: 'ecs',
    healthy: false,
    message: 'ECS provider endpoint not configured (Story 3.3 pending)',
  },
};

/**
 * Fetch provider health from backend API
 * NOTE: Health check endpoint will be implemented in Story 3.3
 */
async function fetchProviderHealth(): Promise<ProviderHealthResponse> {
  try {
    const response = await apiClient.get<ProviderHealthResponse>('/api/providers/health');
    return response.data;
  } catch (error) {
    // If endpoint doesn't exist yet (404), return default
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosError = error as { response?: { status?: number } };
      if (axiosError.response?.status === 404) {
        console.warn(
          '[useProviderHealth] Health check endpoint not implemented yet (Story 3.3). ' +
          'Using default: Replicate-only mode.'
        );
        return DEFAULT_HEALTH;
      }
    }

    // On other errors, default to replicate-only for safety
    console.error('[useProviderHealth] Failed to fetch provider health:', error);
    return DEFAULT_HEALTH;
  }
}

/**
 * Custom hook for monitoring provider health status
 *
 * Features:
 * - Polls health endpoint every 30 seconds
 * - Pauses polling when tab is inactive (saves bandwidth)
 * - Graceful error handling with replicate-only fallback
 * - Manual refetch capability
 *
 * @returns Provider health status and control functions
 */
export function useProviderHealth(): UseProviderHealthReturn {
  const [health, setHealth] = useState<ProviderHealthResponse>(DEFAULT_HEALTH);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [retryTimeout, setRetryTimeout] = useState<number | null>(null);

  // Fetch health status
  const fetchHealth = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const healthData = await fetchProviderHealth();
      setHealth(healthData);

      // Log ECS status changes
      if (healthData.ecs.healthy !== health.ecs.healthy) {
        console.log(
          `[useProviderHealth] ECS provider ${healthData.ecs.healthy ? 'became available' : 'became unavailable'}`
        );
      }
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      setError(errorObj);

      // Fall back to default (replicate-only)
      setHealth(DEFAULT_HEALTH);
    } finally {
      setLoading(false);
    }
  }, [health.ecs.healthy]);

  // Manual refetch function
  const refetch = useCallback(async () => {
    await fetchHealth();
  }, [fetchHealth]);

  // Set up polling with visibility detection
  useEffect(() => {
    // Initial fetch
    fetchHealth();

    let pollInterval: number | null = null;

    // Function to start polling
    const startPolling = () => {
      if (pollInterval) return; // Already polling

      pollInterval = setInterval(() => {
        fetchHealth();
      }, POLL_INTERVAL);
    };

    // Function to stop polling
    const stopPolling = () => {
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
    };

    // Handle visibility change (pause when tab inactive)
    const handleVisibilityChange = () => {
      if (document.hidden) {
        console.log('[useProviderHealth] Tab inactive, pausing health checks');
        stopPolling();
      } else {
        console.log('[useProviderHealth] Tab active, resuming health checks');
        fetchHealth(); // Immediate check on resume
        startPolling();
      }
    };

    // Start initial polling
    startPolling();

    // Listen for visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Cleanup
    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);

      if (retryTimeout) {
        clearTimeout(retryTimeout);
      }
    };
  }, [fetchHealth, retryTimeout]);

  return {
    replicate: health.replicate,
    ecs: health.ecs,
    loading,
    error,
    refetch,
  };
}
