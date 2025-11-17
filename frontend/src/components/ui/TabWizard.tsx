import React from 'react'
import { Check } from 'lucide-react'
import { cn } from '../../utils/cn'

export interface TabConfig {
  id: string
  label: string
  icon?: React.ReactNode
}

export interface TabWizardProps {
  tabs: TabConfig[]
  currentTab: number
  onTabChange: (index: number) => void
  completedTabs: number[]
  className?: string
}

export const TabWizard: React.FC<TabWizardProps> = ({
  tabs,
  currentTab,
  onTabChange,
  completedTabs,
  className,
}) => {
  const canNavigateToTab = (index: number) => {
    // Can navigate to current tab, completed tabs, or the next sequential tab
    return index === currentTab || completedTabs.includes(index) || index === currentTab + 1
  }

  return (
    <div className={cn('w-full', className)}>
      {/* Progress indicator */}
      <div className="mb-6">
        <p className="text-sm text-gray-500 mb-4">
          Step {currentTab + 1} of {tabs.length}
        </p>

        {/* Tab navigation */}
        <div className="relative flex items-center justify-between">
          {tabs.map((tab, index) => {
            const isCompleted = completedTabs.includes(index)
            const isCurrent = index === currentTab
            const isClickable = canNavigateToTab(index)
            const isLocked = !isClickable && index > currentTab

            return (
              <React.Fragment key={tab.id}>
                {/* Tab button */}
                <button
                  onClick={() => isClickable && onTabChange(index)}
                  disabled={!isClickable}
                  className={cn(
                    'relative z-10 flex flex-col items-center gap-2 transition-all duration-200',
                    isClickable && 'cursor-pointer',
                    isLocked && 'cursor-not-allowed opacity-50'
                  )}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  {/* Circle indicator */}
                  <div
                    className={cn(
                      'flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all duration-200',
                      isCompleted && 'bg-success-500 border-success-500 text-gray-50',
                      isCurrent && !isCompleted && 'bg-primary-500 border-primary-500 text-gray-50',
                      !isCurrent && !isCompleted && !isLocked && 'bg-white border-gray-300 text-gray-400',
                      isLocked && 'bg-gray-100 border-gray-200 text-gray-300'
                    )}
                  >
                    {isCompleted ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      <span className="text-sm font-semibold">{index + 1}</span>
                    )}
                  </div>

                  {/* Label (hidden on mobile) */}
                  <span
                    className={cn(
                      'hidden sm:block text-xs font-medium transition-colors duration-200',
                      isCurrent && 'text-gray-900',
                      isCompleted && 'text-success-600',
                      !isCurrent && !isCompleted && 'text-gray-500'
                    )}
                  >
                    {tab.label}
                  </span>
                </button>

                {/* Connector line */}
                {index < tabs.length - 1 && (
                  <div className="flex-1 h-0.5 mx-2 bg-gray-200 relative">
                    <div
                      className={cn(
                        'absolute inset-0 bg-success-500 transition-all duration-500',
                        completedTabs.includes(index) ? 'w-full' : 'w-0'
                      )}
                    />
                  </div>
                )}
              </React.Fragment>
            )
          })}
        </div>
      </div>

      {/* Mobile tab labels */}
      <div className="sm:hidden text-center mb-6">
        <h3 className="text-lg font-semibold text-gray-900">{tabs[currentTab].label}</h3>
      </div>
    </div>
  )
}
