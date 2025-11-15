import React, { useState, useRef, useEffect } from 'react'
import { cn } from '../../utils/cn'

export interface TooltipProps {
  content: React.ReactNode
  children: React.ReactNode
  position?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
  className?: string
}

const positionClasses = {
  top: 'bottom-full mb-2 left-1/2 -translate-x-1/2',
  bottom: 'top-full mt-2 left-1/2 -translate-x-1/2',
  left: 'right-full mr-2 top-1/2 -translate-y-1/2',
  right: 'left-full ml-2 top-1/2 -translate-y-1/2',
}

const arrowClasses = {
  top: 'top-full border-l-transparent border-r-transparent border-t-slate-700',
  bottom: 'bottom-full border-l-transparent border-r-transparent border-b-slate-700',
  left: 'left-full border-t-transparent border-b-transparent border-l-slate-700',
  right: 'right-full border-t-transparent border-b-transparent border-r-slate-700',
}

const Tooltip = React.forwardRef<HTMLDivElement, TooltipProps>(
  ({ content, children, position = 'top', delay = 200, className }, ref) => {
    const [isVisible, setIsVisible] = useState(false)
    const [showAfterDelay, setShowAfterDelay] = useState(false)
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const triggerRef = useRef<HTMLDivElement>(null)

    const handleMouseEnter = () => {
      const timeoutId = setTimeout(() => {
        setShowAfterDelay(true)
      }, delay)
      timeoutRef.current = timeoutId
      setIsVisible(true)
    }

    const handleMouseLeave = () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      setIsVisible(false)
      setShowAfterDelay(false)
    }

    useEffect(() => {
      return () => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current)
      }
    }, [])

    return (
      <div
        ref={ref}
        className="inline-block relative w-fit"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <div ref={triggerRef}>{children}</div>

        {isVisible && showAfterDelay && (
          <>
            {/* Tooltip */}
            <div
              className={cn(
                'absolute z-50 px-3 py-2 bg-slate-700 text-slate-100 text-xs font-medium rounded shadow-lg whitespace-nowrap pointer-events-none animate-fade-in',
                positionClasses[position],
                className
              )}
            >
              {content}
              {/* Arrow */}
              <div
                className={cn('absolute w-0 h-0 border-4', arrowClasses[position])}
              />
            </div>
          </>
        )}
      </div>
    )
  }
)

Tooltip.displayName = 'Tooltip'

export { Tooltip }

