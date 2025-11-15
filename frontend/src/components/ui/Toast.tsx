import React, { useEffect, useState } from 'react'
import { cn } from '../../utils/cn'
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface ToastProps {
  id?: string
  type?: ToastType
  title?: string
  message: string
  duration?: number
  onClose?: () => void
  action?: {
    label: string
    onClick: () => void
  }
}

const toastStyles = {
  success: {
    bg: 'bg-emerald-600/20 border-emerald-600/30',
    icon: <CheckCircle size={20} className="text-emerald-400" />,
    text: 'text-emerald-400',
  },
  error: {
    bg: 'bg-red-600/20 border-red-600/30',
    icon: <AlertCircle size={20} className="text-red-400" />,
    text: 'text-red-400',
  },
  info: {
    bg: 'bg-blue-600/20 border-blue-600/30',
    icon: <Info size={20} className="text-blue-400" />,
    text: 'text-blue-400',
  },
  warning: {
    bg: 'bg-amber-600/20 border-amber-600/30',
    icon: <AlertCircle size={20} className="text-amber-400" />,
    text: 'text-amber-400',
  },
}

const Toast = ({ id, type = 'info', title, message, duration = 5000, onClose, action }: ToastProps) => {
  const [isExiting, setIsExiting] = useState(false)
  const style = toastStyles[type]

  useEffect(() => {
    if (duration) {
      const timer = setTimeout(() => {
        setIsExiting(true)
        setTimeout(onClose, 300)
      }, duration)
      return () => clearTimeout(timer)
    }
  }, [duration, onClose])

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-lg border backdrop-blur-sm transition-all duration-300 pointer-events-auto',
        style.bg,
        isExiting ? 'animate-slide-out' : 'animate-slide-in'
      )}
      role="alert"
      data-toast-id={id}
    >
      {/* Icon */}
      <div className="flex-shrink-0 mt-0.5">{style.icon}</div>

      {/* Content */}
      <div className="flex-1">
        {title && <div className={cn('font-medium text-sm', style.text)}>{title}</div>}
        <p className="text-slate-300 text-sm mt-1">{message}</p>
        {action && (
          <button
            onClick={action.onClick}
            className={cn('mt-2 text-xs font-medium underline transition-opacity hover:opacity-70', style.text)}
          >
            {action.label}
          </button>
        )}
      </div>

      {/* Close Button */}
      <button
        onClick={() => {
          setIsExiting(true)
          setTimeout(onClose, 300)
        }}
        className="flex-shrink-0 text-slate-400 hover:text-slate-300 transition-colors"
        aria-label="Close toast"
      >
        <X size={18} />
      </button>
    </div>
  )
}

// Toast Container for managing multiple toasts
interface ToastContainerProps {
  toasts: ToastProps[]
  removeToast: (id: string) => void
}

const ToastContainer = ({ toasts, removeToast }: ToastContainerProps) => {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-3 max-w-md pointer-events-none">
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <Toast {...toast} onClose={() => removeToast(toast.id!)} />
        </div>
      ))}
    </div>
  )
}

export { Toast, ToastContainer }

