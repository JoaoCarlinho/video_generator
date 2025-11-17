import React from 'react'
import { cn } from '../../utils/cn'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  icon?: React.ReactNode
  iconPosition?: 'left' | 'right'
  helpText?: string
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, icon, iconPosition = 'left', helpText, type = 'text', disabled, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-gray-900 mb-2">
            {label}
            {props.required && <span className="text-error-500 ml-1">*</span>}
          </label>
        )}
        <div className="relative">
          {icon && iconPosition === 'left' && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
              {icon}
            </div>
          )}
          <input
            type={type}
            className={cn(
              'w-full px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 transition-all duration-150',
              'focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
              'hover:border-gray-300',
              error && 'border-error-500 focus:border-error-500 focus:ring-error-500/20',
              icon && iconPosition === 'left' && 'pl-10',
              icon && iconPosition === 'right' && 'pr-10',
              className
            )}
            disabled={disabled}
            ref={ref}
            {...props}
          />
          {icon && iconPosition === 'right' && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
              {icon}
            </div>
          )}
        </div>
        {error && <p className="text-error-500 text-xs mt-1">{error}</p>}
        {helpText && !error && <p className="text-gray-500 text-xs mt-1">{helpText}</p>}
      </div>
    )
  }
)

Input.displayName = 'Input'

export { Input }

