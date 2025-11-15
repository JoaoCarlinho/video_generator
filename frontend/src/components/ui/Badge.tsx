import React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../utils/cn'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors duration-200',
  {
    variants: {
      variant: {
        default: 'bg-indigo-600/20 text-indigo-400 border border-indigo-600/30',
        secondary: 'bg-slate-700 text-slate-300 border border-slate-600',
        success: 'bg-emerald-600/20 text-emerald-400 border border-emerald-600/30',
        danger: 'bg-red-600/20 text-red-400 border border-red-600/30',
        warning: 'bg-amber-600/20 text-amber-400 border border-amber-600/30',
        info: 'bg-blue-600/20 text-blue-400 border border-blue-600/30',
        outline: 'bg-transparent border border-slate-600 text-slate-300',
        gradient: 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white',
      },
      size: {
        sm: 'text-xs px-2 py-0.5',
        md: 'text-xs px-3 py-1',
        lg: 'text-sm px-4 py-1.5',
      },
      animated: {
        true: 'animate-pulse-subtle',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
      animated: false,
    },
  }
)

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {
  icon?: React.ReactNode
  removable?: boolean
  onRemove?: () => void
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant, size, animated, icon, removable, onRemove, children, ...props }, ref) => {
    return (
      <div className={cn(badgeVariants({ variant, size, animated, className }))} ref={ref} {...props}>
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <span>{children}</span>
        {removable && (
          <button
            onClick={onRemove}
            className="ml-1 text-current hover:opacity-70 transition-opacity"
            aria-label="Remove badge"
          >
            ×
          </button>
        )}
      </div>
    )
  }
)

Badge.displayName = 'Badge'

export { Badge, badgeVariants }

