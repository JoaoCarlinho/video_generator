/**
 * useAutoSave hook
 * Automatically saves form data after a debounce period
 */

import { useEffect, useRef, useState, useCallback } from 'react'

interface UseAutoSaveOptions<T> {
  data: T
  onSave: (data: T) => Promise<void>
  debounceMs?: number
  enabled?: boolean
}

interface UseAutoSaveReturn {
  isSaving: boolean
  lastSaved: Date | null
  error: string | null
  saveNow: () => Promise<void>
}

export function useAutoSave<T>({
  data,
  onSave,
  debounceMs = 30000, // 30 seconds default
  enabled = true,
}: UseAutoSaveOptions<T>): UseAutoSaveReturn {
  const [isSaving, setIsSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const dataRef = useRef<T>(data)

  // Update ref when data changes
  useEffect(() => {
    dataRef.current = data
  }, [data])

  const saveNow = useCallback(async () => {
    if (!enabled) return

    setIsSaving(true)
    setError(null)

    try {
      await onSave(dataRef.current)
      setLastSaved(new Date())
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save'
      setError(message)
      console.error('Auto-save error:', err)
    } finally {
      setIsSaving(false)
    }
  }, [enabled, onSave])

  // Set up debounced save
  useEffect(() => {
    if (!enabled) return

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      saveNow()
    }, debounceMs)

    // Cleanup
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [data, enabled, debounceMs, saveNow])

  return {
    isSaving,
    lastSaved,
    error,
    saveNow,
  }
}
