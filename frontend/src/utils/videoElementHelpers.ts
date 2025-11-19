/**
 * Defensive Video Element Helpers
 *
 * Provides robust utilities for handling video elements that may not be
 * immediately available in the DOM, preventing "Video element not found" errors.
 */

interface VideoListenerOptions {
  /**
   * Maximum number of retry attempts to find the video element
   * @default 10
   */
  maxRetries?: number

  /**
   * Delay in milliseconds between retry attempts
   * @default 500
   */
  retryDelay?: number

  /**
   * Whether to observe DOM mutations for dynamic video elements
   * @default true
   */
  useMutationObserver?: boolean

  /**
   * Enable debug logging
   * @default false
   */
  debug?: boolean
}

interface VideoEventListeners {
  onPlay?: (event: Event) => void
  onPause?: (event: Event) => void
  onTimeUpdate?: (event: Event) => void
  onEnded?: (event: Event) => void
  onLoadedMetadata?: (event: Event) => void
  onError?: (event: Event) => void
  [key: string]: ((event: Event) => void) | undefined
}

/**
 * Safely waits for a video element to be available in the DOM and attaches event listeners
 */
export class VideoElementManager {
  private videoElement: HTMLVideoElement | null = null
  private observers: MutationObserver[] = []
  private retryTimeouts: ReturnType<typeof setTimeout>[] = []
  private attachedListeners: Map<string, EventListener> = new Map()
  private options: Required<VideoListenerOptions>

  constructor(options: VideoListenerOptions = {}) {
    this.options = {
      maxRetries: options.maxRetries ?? 10,
      retryDelay: options.retryDelay ?? 500,
      useMutationObserver: options.useMutationObserver ?? true,
      debug: options.debug ?? false,
    }
  }

  /**
   * Attempts to find and attach listeners to a video element
   */
  async attachListeners(
    selector: string | HTMLVideoElement,
    listeners: VideoEventListeners
  ): Promise<HTMLVideoElement | null> {
    // If already a video element, use it directly
    if (selector instanceof HTMLVideoElement) {
      this.videoElement = selector
      this.addEventListeners(this.videoElement, listeners)
      this.log('Video element provided directly, listeners attached')
      return this.videoElement
    }

    // Try to find the video element with retries
    this.videoElement = await this.findVideoElement(selector)

    if (this.videoElement) {
      this.addEventListeners(this.videoElement, listeners)
      this.log(`Video element found and listeners attached: ${selector}`)
      return this.videoElement
    }

    this.log(`Video element not found after ${this.options.maxRetries} attempts: ${selector}`, 'warn')
    return null
  }

  /**
   * Attempts to find a video element with retry logic and mutation observation
   */
  private async findVideoElement(selector: string): Promise<HTMLVideoElement | null> {
    // Immediate check
    const element = this.queryVideoElement(selector)
    if (element) {
      return element
    }

    // Set up mutation observer if enabled
    if (this.options.useMutationObserver) {
      const observerPromise = this.observeForVideoElement(selector)
      const retryPromise = this.retryFindElement(selector)

      // Race between mutation observer and retry logic
      return Promise.race([observerPromise, retryPromise])
    }

    // Fallback to retry logic only
    return this.retryFindElement(selector)
  }

  /**
   * Retry logic with exponential backoff
   */
  private async retryFindElement(selector: string): Promise<HTMLVideoElement | null> {
    for (let attempt = 1; attempt <= this.options.maxRetries; attempt++) {
      const element = this.queryVideoElement(selector)

      if (element) {
        this.log(`Video element found on attempt ${attempt}/${this.options.maxRetries}`)
        return element
      }

      if (attempt < this.options.maxRetries) {
        // Exponential backoff: 500ms, 1000ms, 1500ms, etc.
        const delay = this.options.retryDelay * attempt
        await this.sleep(delay)
      }
    }

    return null
  }

  /**
   * Uses MutationObserver to watch for video element insertion
   */
  private observeForVideoElement(selector: string): Promise<HTMLVideoElement | null> {
    return new Promise((resolve) => {
      const observer = new MutationObserver((mutations) => {
        const element = this.queryVideoElement(selector)
        if (element) {
          this.log('Video element found via MutationObserver')
          observer.disconnect()
          resolve(element)
        }
      })

      // Observe the entire document for child additions
      observer.observe(document.body, {
        childList: true,
        subtree: true,
      })

      this.observers.push(observer)

      // Timeout after max retries * delay
      const timeoutId = setTimeout(() => {
        observer.disconnect()
        resolve(null)
      }, this.options.maxRetries * this.options.retryDelay)

      this.retryTimeouts.push(timeoutId)
    })
  }

  /**
   * Safely queries for a video element
   */
  private queryVideoElement(selector: string): HTMLVideoElement | null {
    try {
      const element = document.querySelector(selector)
      return element instanceof HTMLVideoElement ? element : null
    } catch (error) {
      this.log(`Error querying selector "${selector}": ${error}`, 'error')
      return null
    }
  }

  /**
   * Adds event listeners to video element with defensive checks
   */
  private addEventListeners(videoElement: HTMLVideoElement, listeners: VideoEventListeners): void {
    if (!videoElement) {
      this.log('Cannot attach listeners: video element is null', 'error')
      return
    }

    Object.entries(listeners).forEach(([eventName, handler]) => {
      if (!handler) return

      // Convert camelCase to lowercase event name (e.g., onPlay -> play)
      const cleanEventName = eventName.replace(/^on/, '').toLowerCase()

      try {
        videoElement.addEventListener(cleanEventName, handler as EventListener)
        this.attachedListeners.set(cleanEventName, handler as EventListener)
        this.log(`Attached listener: ${cleanEventName}`)
      } catch (error) {
        this.log(`Failed to attach listener "${cleanEventName}": ${error}`, 'error')
      }
    })
  }

  /**
   * Removes all attached event listeners
   */
  detachListeners(): void {
    if (!this.videoElement) {
      this.log('No video element to detach listeners from')
      return
    }

    this.attachedListeners.forEach((handler, eventName) => {
      try {
        this.videoElement?.removeEventListener(eventName, handler)
        this.log(`Detached listener: ${eventName}`)
      } catch (error) {
        this.log(`Failed to detach listener "${eventName}": ${error}`, 'error')
      }
    })

    this.attachedListeners.clear()
  }

  /**
   * Cleanup method to clear all observers and timeouts
   */
  cleanup(): void {
    this.detachListeners()

    // Clear all observers
    this.observers.forEach((observer) => observer.disconnect())
    this.observers = []

    // Clear all timeouts
    this.retryTimeouts.forEach((timeout) => clearTimeout(timeout))
    this.retryTimeouts = []

    this.videoElement = null
    this.log('Cleanup completed')
  }

  /**
   * Gets the current video element (if found)
   */
  getVideoElement(): HTMLVideoElement | null {
    return this.videoElement
  }

  /**
   * Checks if video element exists and is ready
   */
  isReady(): boolean {
    return this.videoElement !== null && this.videoElement.readyState >= 1
  }

  /**
   * Helper method for sleeping/delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => {
      const timeoutId = setTimeout(resolve, ms)
      this.retryTimeouts.push(timeoutId)
    })
  }

  /**
   * Logging helper
   */
  private log(message: string, level: 'log' | 'warn' | 'error' = 'log'): void {
    if (this.options.debug) {
      const prefix = '[VideoElementManager]'
      switch (level) {
        case 'warn':
          console.warn(prefix, message)
          break
        case 'error':
          console.error(prefix, message)
          break
        default:
          console.log(prefix, message)
      }
    }
  }
}

/**
 * Simple helper function for one-off video element listener attachment
 * Use this for simple cases, or use VideoElementManager for more control
 */
export async function attachVideoListeners(
  selector: string | HTMLVideoElement,
  listeners: VideoEventListeners,
  options?: VideoListenerOptions
): Promise<HTMLVideoElement | null> {
  const manager = new VideoElementManager(options)
  const videoElement = await manager.attachListeners(selector, listeners)

  if (!videoElement) {
    console.warn(`Video element not found for attaching listeners.`)
    return null
  }

  return videoElement
}

/**
 * React hook for managing video element listeners
 * Use this in React components for automatic cleanup
 */
export function useVideoElementManager(options?: VideoListenerOptions) {
  const managerRef = { current: new VideoElementManager(options) }

  const attachListeners = async (
    selector: string | HTMLVideoElement,
    listeners: VideoEventListeners
  ) => {
    return managerRef.current.attachListeners(selector, listeners)
  }

  const cleanup = () => {
    managerRef.current.cleanup()
  }

  return {
    attachListeners,
    detachListeners: () => managerRef.current.detachListeners(),
    cleanup,
    getVideoElement: () => managerRef.current.getVideoElement(),
    isReady: () => managerRef.current.isReady(),
  }
}
