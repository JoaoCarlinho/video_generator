import React from 'react'
import { Link } from 'react-router-dom'
import { cn } from '../../utils/cn'
import { Button } from '../ui'

export interface HeaderProps extends React.HTMLAttributes<HTMLElement> {
  logo?: React.ReactNode
  title?: string
  subtitle?: string
  actions?: React.ReactNode
  sticky?: boolean
  transparent?: boolean
}

const Header = React.forwardRef<HTMLElement, HeaderProps>(
  ({
    logo,
    title,
    subtitle,
    actions,
    sticky = true,
    transparent = false,
    className,
    ...props
  }, ref) => {
    return (
      <header
        ref={ref}
        className={cn(
          'border-b transition-all duration-200',
          sticky && 'sticky top-0 z-40',
          transparent
            ? 'border-slate-700/20 bg-slate-900/50 backdrop-blur'
            : 'border-slate-700 bg-slate-900',
          className
        )}
        {...props}
      >
        <div className="px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            {/* Logo & Title */}
            <div className="flex items-center gap-3">
              {logo && (
                <div className="flex-shrink-0">
                  {typeof logo === 'string' ? (
                    <Link to="/" className="text-xl font-bold text-indigo-600">
                      {logo}
                    </Link>
                  ) : (
                    logo
                  )}
                </div>
              )}
              {title && (
                <div className="hidden sm:block">
                  <h1 className="text-sm font-semibold text-slate-100">{title}</h1>
                  {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
                </div>
              )}
            </div>

            {/* Actions */}
            {actions && <div className="flex items-center gap-2">{actions}</div>}
          </div>
        </div>
      </header>
    )
  }
)

Header.displayName = 'Header'

export { Header }

