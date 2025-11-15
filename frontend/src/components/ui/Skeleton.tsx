import React from 'react'
import { cn } from '../../utils/cn'

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'rect' | 'circle'
  width?: string | number
  height?: string | number
  count?: number
  circle?: boolean
  animated?: boolean
}

const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  (
    {
      variant = 'text',
      width,
      height,
      count = 1,
      circle = false,
      animated = true,
      className,
      style,
      ...props
    },
    ref
  ) => {
    const getDefaultHeight = () => {
      if (height) return height
      if (variant === 'circle') return '40px'
      if (variant === 'rect') return '200px'
      return '16px'
    }

    const getDefaultWidth = () => {
      if (width) return width
      if (variant === 'circle') return '40px'
      if (variant === 'rect') return '100%'
      return '100%'
    }

    const h = getDefaultHeight()
    const w = getDefaultWidth()

    const skeletonStyle: React.CSSProperties = {
      width: typeof w === 'number' ? `${w}px` : w,
      height: typeof h === 'number' ? `${h}px` : h,
      ...style,
    }

    const skeletonClass = cn(
      'bg-gradient-to-r from-slate-800 via-slate-700 to-slate-800',
      circle && 'rounded-full',
      !circle && (variant === 'rect' ? 'rounded-lg' : 'rounded'),
      animated && 'animate-pulse-subtle',
      className
    )

    const skeletons = Array.from({ length: count }).map((_, i) => (
      <div key={i} className={skeletonClass} style={skeletonStyle} />
    ))

    if (count === 1) {
      return (
        <div ref={ref} className={skeletonClass} style={skeletonStyle} {...props} />
      )
    }

    return (
      <div ref={ref} className="space-y-2" {...props}>
        {skeletons}
      </div>
    )
  }
)

Skeleton.displayName = 'Skeleton'

// Predefined skeleton compositions
interface SkeletonTextProps extends Omit<SkeletonProps, 'count'> {
  lines?: number
}

const SkeletonText = ({ lines = 3, ...props }: SkeletonTextProps) => {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          variant="text"
          width={i === lines - 1 ? '75%' : '100%'}
          {...props}
        />
      ))}
    </div>
  )
}

interface SkeletonAvatarProps extends Omit<SkeletonProps, 'variant'> {}

const SkeletonAvatar = (props: SkeletonAvatarProps) => (
  <Skeleton variant="circle" width="48px" height="48px" {...props} />
)

interface SkeletonCardProps {
  className?: string
}

const SkeletonCard = ({ className }: SkeletonCardProps) => (
  <div className={cn('rounded-lg bg-slate-800 p-6 space-y-4', className)}>
    <Skeleton width="100%" height="20px" />
    <Skeleton variant="rect" width="100%" height="100px" />
    <div className="space-y-2">
      <Skeleton width="100%" height="16px" />
      <Skeleton width="75%" height="16px" />
    </div>
  </div>
)

export { Skeleton, SkeletonText, SkeletonAvatar, SkeletonCard }

