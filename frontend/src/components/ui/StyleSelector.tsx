/**
 * PHASE 7: StyleSelector Component - Luxury Theme
 * 
 * Displays 5 video styles for user selection in CreateProject
 * Styles: Cinematic, Dark Premium, Minimal Studio, Lifestyle, 2D Animated  (Shows style cards with descriptions, keywords, and use cases.)
 * User can select one style or leave blank for LLM to choose.
 */

import type { VideoStyle } from '../../hooks/useStyleSelector';
import { cn } from '../../utils/cn';
import { Check } from 'lucide-react';

interface StyleSelectorProps {
  styles: VideoStyle[];
  selectedStyle: string | null;
  onSelectStyle: (styleId: string) => void;
  onClearStyle: () => void;
  isLoading?: boolean;
}

export const StyleSelector = ({
  styles,
  selectedStyle,
  onSelectStyle,
  onClearStyle,
  isLoading = false,
}: StyleSelectorProps) => {
  if (isLoading) {
    return (
      <div className="p-6 bg-neutral-50 rounded-lg border border-neutral-200">
        <p className="text-neutral-600">Loading video styles...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-neutral-900">Video Style</h3>
          <p className="text-sm text-neutral-600 mt-1">
            Choose a visual style for your video (optional - AI will decide if not selected)
          </p>
        </div>
        {selectedStyle && (
          <button
            onClick={onClearStyle}
            className="px-3 py-1 text-sm bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded-md transition-colors"
          >
            Clear Selection
          </button>
        )}
      </div>

      {/* Style Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
        {styles.map((style) => (
          <button
            key={style.id}
            onClick={() => onSelectStyle(style.id)}
            className={cn(
              'p-4 rounded-lg border-2 text-left transition-all',
              'hover:shadow-md',
              selectedStyle === style.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-neutral-200 bg-white hover:border-neutral-300'
            )}
          >
            {/* Style Name */}
            <h4 className="font-semibold text-neutral-900 text-sm mb-1">
              {style.name}
            </h4>

            {/* Short Description */}
            <p className="text-xs text-neutral-600 mb-2 line-clamp-2">
              {style.description}
            </p>

            {/* Keywords */}
            <div className="mb-2">
              <p className="text-xs font-medium text-neutral-700 mb-1">Keywords:</p>
              <div className="flex flex-wrap gap-1">
                {style.keywords.slice(0, 2).map((keyword) => (
                  <span
                    key={keyword}
                    className="px-2 py-0.5 bg-neutral-100 text-neutral-700 rounded text-xs"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            </div>

            {/* Use Cases */}
            <div>
              <p className="text-xs font-medium text-neutral-700 mb-1">Used by:</p>
              <p className="text-xs text-neutral-600">
                {style.examples?.slice(0, 2).join(', ') || 'Various brands'}
              </p>
            </div>

            {/* Selection Indicator */}
            {selectedStyle === style.id && (
              <div className="mt-2 pt-2 border-t border-blue-200 flex items-center justify-center">
                <svg
                  className="w-4 h-4 text-blue-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                <span className="ml-1 text-xs font-medium text-blue-600">Selected</span>
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Info Message */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-900">
          💡 <strong>Tip:</strong> All scenes in your video will use the same style for visual
          consistency. Leave blank to let AI choose based on your creative brief.
        </p>
      </div>
    </div>
  );
};

