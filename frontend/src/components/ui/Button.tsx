import React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../utils/cn'

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/20 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed',
  {
    variants: {
      variant: {
        // Primary button (solid red)
        default: 'bg-primary-500 hover:bg-primary-600 active:bg-primary-700 text-gray-50 shadow-sm hover:shadow-md',
        // Secondary button (light with border)
        secondary: 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50 hover:border-gray-400',
        // Outline button (subtle border, text only)
        outline: 'border border-gray-300 text-gray-900 hover:border-primary-500 hover:text-primary-600',
        // Ghost button (minimal, text only)
        ghost: 'text-gray-600 hover:text-primary-500 hover:bg-gray-50',
        // Danger button (solid red)
        danger: 'bg-error-500 text-gray-50 hover:bg-error-600 active:bg-error-700 shadow-sm hover:shadow-md',
        // Success button (solid green)
        success: 'bg-success-500 text-gray-50 hover:bg-success-600 active:bg-success-700 shadow-sm hover:shadow-md',
        // Gradient variant (kept for backward compatibility, but using solid primary)
        gradient: 'bg-primary-500 hover:bg-primary-600 active:bg-primary-700 text-gray-50 shadow-sm hover:shadow-md',
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

