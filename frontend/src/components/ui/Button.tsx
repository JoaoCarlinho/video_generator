import React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../utils/cn'

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-charcoal-950 disabled:opacity-50 disabled:cursor-not-allowed',
  {
    variants: {
      variant: {
        default: 'bg-gold text-gold-foreground hover:bg-gold-dark shadow-gold hover:shadow-gold-lg',
        secondary: 'bg-slate-800 text-off-white hover:bg-slate-700 border border-neutral-dim',
        outline: 'border border-gold text-gold hover:bg-gold hover:text-gold-foreground',
        ghost: 'text-muted-gray hover:text-off-white hover:bg-slate-800',
        danger: 'bg-red-500 text-white hover:bg-red-600 shadow-md hover:shadow-lg',
        success: 'bg-emerald-500 text-white hover:bg-emerald-600 shadow-md hover:shadow-lg',
        gradient: 'bg-gradient-gold text-gold-foreground hover:opacity-90 shadow-gold hover:shadow-gold-lg',
        hero: 'bg-gold text-gold-foreground hover:bg-gold-dark shadow-gold hover:shadow-gold-lg font-semibold',
        gold: 'bg-gradient-gold text-gold-foreground hover:opacity-90 shadow-gold hover:shadow-gold-lg',
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
        icon: 'h-10 w-10 p-0',
      },
      fullWidth: {
        true: 'w-full',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
      fullWidth: false,
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean
  icon?: React.ReactNode
  iconPosition?: 'left' | 'right'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, fullWidth, isLoading, icon, iconPosition = 'left', children, disabled, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, fullWidth, className }))}
        disabled={disabled || isLoading}
        ref={ref}
        {...props}
      >
        <div className="flex items-center justify-center gap-2">
          {isLoading ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          ) : icon && iconPosition === 'left' ? (
            icon
          ) : null}
          {children}
          {!isLoading && icon && iconPosition === 'right' ? icon : null}
        </div>
      </button>
    )
  }
)

Button.displayName = 'Button'

export { Button, buttonVariants }
export type ButtonVariant = 'default' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'gradient' | 'hero' | 'gold'

