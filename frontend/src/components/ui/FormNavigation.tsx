import React from 'react'
import { ChevronLeft, ChevronRight, Save } from 'lucide-react'
import { Button } from './Button'
import { cn } from '../../utils/cn'

export interface FormNavigationProps {
  onBack?: () => void
  onNext?: () => void
  onSaveDraft?: () => void
  canProceed?: boolean
  backLabel?: string
  nextLabel?: string
  showSaveDraft?: boolean
  isLoading?: boolean
  className?: string
}

export const FormNavigation: React.FC<FormNavigationProps> = ({
  onBack,
  onNext,
  onSaveDraft,
  canProceed = true,
  backLabel = 'Back',
  nextLabel = 'Continue',
  showSaveDraft = true,
  isLoading = false,
  className,
}) => {
  return (
    <div className={cn('flex flex-col gap-4 pt-6 border-t border-gray-200', className)}>
      {/* Primary navigation buttons */}
      <div className="flex gap-4">
        {onBack && (
          <Button
            type="button"
            variant="outline"
            onClick={onBack}
            disabled={isLoading}
            className="flex-1"
            icon={<ChevronLeft className="w-4 h-4" />}
            iconPosition="left"
          >
            {backLabel}
          </Button>
        )}

        {onNext && (
          <Button
            type="button"
            variant="default"
            onClick={onNext}
            disabled={!canProceed || isLoading}
            isLoading={isLoading}
            className="flex-1"
            icon={!isLoading && <ChevronRight className="w-4 h-4" />}
            iconPosition="right"
          >
            {nextLabel}
          </Button>
        )}
      </div>

      {/* Save draft button (centered, subtle) */}
      {showSaveDraft && onSaveDraft && (
        <div className="text-center">
          <button
            type="button"
            onClick={onSaveDraft}
            disabled={isLoading}
            className={cn(
              'inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700',
              'transition-colors duration-150',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            <Save className="w-4 h-4" />
            Save as Draft
          </button>
        </div>
      )}
    </div>
  )
}
