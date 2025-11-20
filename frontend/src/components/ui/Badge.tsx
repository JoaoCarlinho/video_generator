import React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../utils/cn'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors duration-200',
  {
    variants: {
      variant: {
        default: 'bg-gold/10 text-gold border border-gold/30',
        secondary: 'bg-charcoal-800 text-muted-gray border border-charcoal-700/80',
        success: 'bg-emerald-600/20 text-emerald-300 border border-emerald-600/30',
        danger: 'bg-red-600/20 text-red-300 border border-red-600/30',
        warning: 'bg-amber-600/20 text-amber-300 border border-amber-600/30',
        info: 'bg-blue-600/15 text-blue-300 border border-blue-600/30',
        outline: 'bg-transparent border border-charcoal-700/70 text-off-white',
        gradient: 'bg-gradient-to-r from-gold to-gold-dark text-gold-foreground',
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

