import React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../utils/cn'

const progressVariants = cva('w-full rounded-full overflow-hidden bg-slate-700', {
  variants: {
    size: {
      sm: 'h-1',
      md: 'h-2',
      lg: 'h-3',
    },
  },
  defaultVariants: {
    size: 'md',
  },
})

const progressBarVariants = cva('h-full rounded-full transition-all duration-300', {
  variants: {
    variant: {
      default: 'bg-indigo-600',
      success: 'bg-emerald-500',
      warning: 'bg-amber-500',
      danger: 'bg-red-500',
      gradient: 'bg-gradient-to-r from-indigo-600 to-purple-600',
    },
    animated: {
      true: 'animate-pulse-subtle',
      false: '',
    },
  },
  defaultVariants: {
    variant: 'default',
    animated: false,
  },
})

export interface ProgressBarProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof progressVariants> {
  value: number
  max?: number
  label?: string
  showValue?: boolean
  variant?: VariantProps<typeof progressBarVariants>['variant']
  animated?: boolean
}

const ProgressBar = React.forwardRef<HTMLDivElement, ProgressBarProps>(
  (
    {
      value,
      max = 100,
      label,
      showValue,
      size,
      variant = 'default',
      animated = false,
      className,
      ...props
    },
    ref
  ) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

    return (
      <div ref={ref} className="w-full" {...props}>
        {(label || showValue) && (
          <div className="flex items-center justify-between mb-2">
            {label && <span className="text-sm font-medium text-slate-300">{label}</span>}
            {showValue && (
              <span className="text-sm font-medium text-slate-400">
                {Math.round(percentage)}%
              </span>
            )}
          </div>
        )}
        <div className={cn(progressVariants({ size }), className)}>
          <div
            className={cn(progressBarVariants({ variant, animated }))}
            style={{ width: `${percentage}%` }}
            role="progressbar"
            aria-valuenow={value}
            aria-valuemin={0}
            aria-valuemax={max}
          />
        </div>
      </div>
    )
  }
)

ProgressBar.displayName = 'ProgressBar'

// Circular Progress variant
export interface CircularProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number
  max?: number
  size?: number
  strokeWidth?: number
  variant?: VariantProps<typeof progressBarVariants>['variant']
  showValue?: boolean
}

const CircularProgress = React.forwardRef<HTMLDivElement, CircularProgressProps>(
  (
    {
      value,
      max = 100,
      size = 100,
      strokeWidth = 4,
      variant = 'default',
      showValue,
      className,
      ...props
    },
    ref
  ) => {
    const radius = (size - strokeWidth) / 2
    const circumference = radius * 2 * Math.PI
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100)
    const offset = circumference - (percentage / 100) * circumference

    const colorMap = {
      default: '#4f46e5',
      success: '#10b981',
      warning: '#f59e0b',
      danger: '#ef4444',
      gradient: 'url(#gradient)',
    }

    return (
      <div ref={ref} className={cn('inline-flex items-center justify-center', className)} {...props}>
        <svg width={size} height={size} className="transform -rotate-90">
          <defs>
            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#4f46e5" />
              <stop offset="100%" stopColor="#9333ea" />
            </linearGradient>
          </defs>
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#334155"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colorMap[variant]}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-300"
          />
        </svg>
        {showValue && (
          <div className="absolute flex flex-col items-center justify-center">
            <span className="text-lg font-semibold text-slate-100">{Math.round(percentage)}%</span>
          </div>
        )}
      </div>
    )
  }
)

CircularProgress.displayName = 'CircularProgress'

export { ProgressBar, CircularProgress }

