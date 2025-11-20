import React, { useState, useRef, useEffect } from 'react'
import { cn } from '../../utils/cn'
import { ChevronDown } from 'lucide-react'

export interface SelectOption {
  value: string | number
  label: string
  icon?: React.ReactNode
}

export interface SelectProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onChange'> {
  options: SelectOption[]
  value?: string | number
  onChange?: (value: string | number) => void
  placeholder?: string
  label?: string
  error?: string
  disabled?: boolean
  searchable?: boolean
  clearable?: boolean
  icon?: React.ReactNode
  required?: boolean
}

const Select = React.forwardRef<HTMLDivElement, SelectProps>(
  (
    {
      options,
      value,
      onChange,
      placeholder = 'Select an option...',
      label,
      error,
      disabled,
      searchable,
      clearable,
      icon,
      required,
      className,
      ...props
    },
    ref
  ) => {
    const [isOpen, setIsOpen] = useState(false)
    const [searchTerm, setSearchTerm] = useState('')
    const containerRef = useRef<HTMLDivElement>(null)
    const searchInputRef = useRef<HTMLInputElement>(null)

    const selectedOption = options.find((opt) => opt.value === value)
    const filteredOptions = searchable
      ? options.filter((opt) => opt.label.toLowerCase().includes(searchTerm.toLowerCase()))
      : options

    // Close dropdown when clicking outside
    useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
          setIsOpen(false)
          setSearchTerm('')
        }
      }

      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    // Focus search input when opening
    useEffect(() => {
      if (isOpen && searchable && searchInputRef.current) {
        searchInputRef.current.focus()
      }
    }, [isOpen, searchable])

    return (
      <div ref={ref} className="w-full" {...props}>
        {label && (
          <label className="block text-sm font-medium text-slate-300 mb-2">
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}

        <div ref={containerRef} className="relative">
          {/* Trigger Button */}
          <button
            onClick={() => !disabled && setIsOpen(!isOpen)}
            disabled={disabled}
            className={cn(
              'w-full px-4 py-3 bg-charcoal-900/70 border border-charcoal-700/70 rounded-xl text-off-white text-left flex items-center justify-between transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-gold focus:border-gold/40',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'hover:border-gold/30',
              isOpen && 'ring-2 ring-gold border-transparent',
              error && 'border-red-500 focus:ring-red-600',
              icon && 'pl-10'
            )}
          >
            <div className="flex items-center gap-2">
              {icon && <div className="absolute left-3 text-slate-400">{icon}</div>}
              <span>{selectedOption ? selectedOption.label : placeholder}</span>
            </div>
            <ChevronDown size={18} className={cn('transition-transform', isOpen && 'rotate-180')} />
          </button>

          {/* Dropdown Menu */}
          {isOpen && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-charcoal-900 border border-charcoal-700 rounded-xl shadow-lg z-50 animate-scale-in">
              {/* Search Input */}
              {searchable && (
                <div className="p-2 border-b border-charcoal-700/70">
                  <input
                    ref={searchInputRef}
                    type="text"
                    placeholder="Search..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className={cn(
                      'w-full px-3 py-2 bg-charcoal-800 border border-charcoal-700/70 rounded text-off-white text-sm placeholder-muted-gray',
                      'focus:outline-none focus:ring-2 focus:ring-gold focus:border-gold/40'
                    )}
                  />
                </div>
              )}

              {/* Options */}
              <div className="max-h-48 overflow-y-auto">
                {filteredOptions.length > 0 ? (
                  filteredOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        onChange?.(option.value)
                        setIsOpen(false)
                        setSearchTerm('')
                      }}
                      className={cn(
                        'w-full px-4 py-2 text-left text-sm flex items-center gap-2 transition-colors duration-150',
                        'hover:bg-charcoal-800',
                        value === option.value && 'bg-gold/10 text-gold'
                      )}
                    >
                      {option.icon && <span>{option.icon}</span>}
                      <span>{option.label}</span>
                    </button>
                  ))
                ) : (
                  <div className="px-4 py-8 text-center text-slate-400 text-sm">No options found</div>
                )}
              </div>

              {/* Clear Button */}
              {clearable && value && (
                <div className="border-t border-charcoal-700/70 p-2">
                  <button
                    onClick={() => {
                      onChange?.('')
                      setIsOpen(false)
                      setSearchTerm('')
                    }}
                    className="w-full px-3 py-2 text-sm text-muted-gray hover:text-off-white hover:bg-charcoal-800 rounded transition-colors text-left"
                  >
                    Clear
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
      </div>
    )
  }
)

Select.displayName = 'Select'

export { Select }

