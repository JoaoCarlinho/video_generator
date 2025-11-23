/**
 * PHASE 7: useStyleSelector Hook
 * 
 * Manages video style selection for ad creation.
 * Loads available styles from backend and manages user selection.
 */

import { useState, useEffect } from 'react';
import { api } from '../services/api';

export interface VideoStyle {
  id: string;
  name: string;
  description: string;
  short_description?: string;
  keywords: string[];
  examples?: string[];
  best_for?: string[];
  icon?: string;
  color?: string;
}

export function useStyleSelector() {
  const [styles, setStyles] = useState<VideoStyle[]>([]);
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load available styles from backend
  useEffect(() => {
    const loadStyles = async () => {
      try {
        setIsLoading(true);
        const response = await api.get('/api/campaigns/styles/available');
        
        if (response.data && response.data.styles) {
          setStyles(response.data.styles);
        }
      } catch (err) {
        console.error('Failed to load styles:', err);
        setError('Failed to load video styles');
      } finally {
        setIsLoading(false);
      }
    };

    loadStyles();
  }, []);

  const selectStyle = (styleId: string) => {
    const validStyle = styles.find(s => s.id === styleId);
    if (validStyle) {
      setSelectedStyle(styleId);
    }
  };

  const clearSelection = () => {
    setSelectedStyle(null);
  };

  const getStyleById = (styleId: string): VideoStyle | undefined => {
    return styles.find(s => s.id === styleId);
  };

  return {
    styles,
    selectedStyle,
    setSelectedStyle: selectStyle,
    clearSelection,
    isLoading,
    error,
    getStyleById,
    hasSelection: selectedStyle !== null,
  };
}

