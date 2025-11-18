/**
 * PHASE 7: StyleSelector Component - Luxury Theme
 * 
 * Displays 5 video styles for user selection in CreateProject
 * Styles: Cinematic, Dark Premium, Minimal Studio, Lifestyle, 2D Animated
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
      <div className="p-6 bg-olive-700/30 rounded-xl border border-olive-600/50">
        <p className="text-muted-gray">Loading video styles...</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-off-white">Video Style</h3>
        {selectedStyle && (
          <button
            onClick={onClearStyle}
            className="px-2 py-1 text-xs bg-olive-700/30 hover:bg-olive-700/50 text-muted-gray hover:text-gold border border-olive-600 rounded-lg transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Style Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {styles.map((style) => (
          <button
            key={style.id}
            onClick={() => onSelectStyle(style.id)}
            className={cn(
              'group relative p-2.5 rounded-lg border-2 text-center transition-all duration-200',
              'hover:scale-105',
              selectedStyle === style.id
                ? 'border-gold bg-gold/10 shadow-gold'
                : 'border-olive-600 bg-olive-700/20 hover:border-olive-500 hover:bg-olive-700/30'
            )}
          >
            {/* Selection indicator */}
            {selectedStyle === style.id && (
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-gold rounded-full flex items-center justify-center shadow-gold">
                <Check className="w-2.5 h-2.5 text-gold-foreground" />
              </div>
            )}

            {/* Style Name Only */}
            <h4 className={cn(
              'font-semibold text-xs',
              selectedStyle === style.id ? 'text-gold' : 'text-off-white'
            )}>
              {style.name}
            </h4>
          </button>
        ))}
      </div>
    </div>
  );
};
