# Video Element Helpers - Usage Examples

This document provides examples of how to use the defensive video element utilities to prevent "Video element not found for attaching listeners" errors.

## Problem

When JavaScript tries to attach event listeners to video elements before they're loaded in the DOM, you get errors like:
```
Video element not found for attaching listeners.
```

This happens due to:
- Timing issues (script runs before video loads)
- Dynamically loaded content (SPAs, lazy loading)
- Async rendering frameworks (React, Vue, etc.)

## Solution

The `videoElementHelpers` utility provides three approaches:

### 1. React Hook (Recommended for React Components)

```tsx
import { useVideoElementManager } from '@/utils/videoElementHelpers'
import { useRef, useEffect } from 'react'

function VideoPlayer({ videoUrl }: { videoUrl: string }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const videoManager = useVideoElementManager({
    debug: true, // Enable console logging
    maxRetries: 10,
    retryDelay: 500,
  })

  useEffect(() => {
    if (!videoRef.current) return

    // Defensively attach listeners
    const setupListeners = async () => {
      await videoManager.attachListeners(videoRef.current!, {
        onPlay: (e) => console.log('Video playing'),
        onPause: (e) => console.log('Video paused'),
        onTimeUpdate: (e) => {
          const video = e.target as HTMLVideoElement
          console.log('Current time:', video.currentTime)
        },
        onLoadedMetadata: (e) => {
          const video = e.target as HTMLVideoElement
          console.log('Duration:', video.duration)
        },
        onEnded: (e) => console.log('Video ended'),
        onError: (e) => console.error('Video error:', e),
      })
    }

    setupListeners()

    // Cleanup on unmount
    return () => {
      videoManager.cleanup()
    }
  }, [videoUrl])

  return <video ref={videoRef} src={videoUrl} />
}
```

### 2. Simple Function (One-off Usage)

```typescript
import { attachVideoListeners } from '@/utils/videoElementHelpers'

// Find by selector
async function setupVideo() {
  const videoElement = await attachVideoListeners(
    'video.my-video-player',
    {
      onPlay: () => console.log('Playing'),
      onPause: () => console.log('Paused'),
    },
    {
      maxRetries: 5,
      retryDelay: 300,
    }
  )

  if (!videoElement) {
    console.warn('Video element was never found')
  }
}

// Or use an existing element
async function setupExistingVideo() {
  const video = document.querySelector('video') as HTMLVideoElement
  if (video) {
    await attachVideoListeners(video, {
      onTimeUpdate: (e) => {
        console.log((e.target as HTMLVideoElement).currentTime)
      },
    })
  }
}
```

### 3. Class-based Manager (Full Control)

```typescript
import { VideoElementManager } from '@/utils/videoElementHelpers'

class VideoController {
  private manager: VideoElementManager

  constructor() {
    this.manager = new VideoElementManager({
      debug: true,
      maxRetries: 15,
      retryDelay: 500,
      useMutationObserver: true, // Watch for dynamic elements
    })
  }

  async initialize(selector: string) {
    const video = await this.manager.attachListeners(selector, {
      onPlay: this.handlePlay.bind(this),
      onPause: this.handlePause.bind(this),
      onTimeUpdate: this.handleTimeUpdate.bind(this),
    })

    if (!video) {
      console.error('Failed to find video element')
      return false
    }

    console.log('Video initialized successfully')
    return true
  }

  handlePlay(e: Event) {
    console.log('Video started playing')
  }

  handlePause(e: Event) {
    console.log('Video paused')
  }

  handleTimeUpdate(e: Event) {
    const video = e.target as HTMLVideoElement
    console.log(`Time: ${video.currentTime}/${video.duration}`)
  }

  checkIfReady(): boolean {
    return this.manager.isReady()
  }

  getVideo(): HTMLVideoElement | null {
    return this.manager.getVideoElement()
  }

  destroy() {
    this.manager.cleanup()
  }
}

// Usage
const controller = new VideoController()
await controller.initialize('#my-video')

// Later...
controller.destroy()
```

## Configuration Options

```typescript
interface VideoListenerOptions {
  /**
   * Maximum retry attempts to find the video element
   * @default 10
   */
  maxRetries?: number

  /**
   * Delay in milliseconds between retries
   * @default 500
   */
  retryDelay?: number

  /**
   * Use MutationObserver to watch for dynamic elements
   * Recommended: true for SPAs, false for static pages
   * @default true
   */
  useMutationObserver?: boolean

  /**
   * Enable debug console logging
   * @default false
   */
  debug?: boolean
}
```

## Common Use Cases

### Browser Extensions

```typescript
// content.js - Browser extension that needs to monitor videos on web pages
import { VideoElementManager } from './videoElementHelpers'

const manager = new VideoElementManager({
  debug: false,
  maxRetries: 20, // Pages may load slowly
  retryDelay: 1000,
  useMutationObserver: true, // Critical for dynamic pages
})

// Wait for video element
const video = await manager.attachListeners('video', {
  onPlay: (e) => {
    // Track video play events
    chrome.runtime.sendMessage({ type: 'VIDEO_PLAYED' })
  },
  onPause: (e) => {
    chrome.runtime.sendMessage({ type: 'VIDEO_PAUSED' })
  },
})

if (!video) {
  console.warn('No video element found on this page')
}
```

### Single Page Applications (SPAs)

```typescript
// Vue 3 example
import { onMounted, onUnmounted, ref } from 'vue'
import { VideoElementManager } from '@/utils/videoElementHelpers'

export default {
  setup() {
    const videoRef = ref(null)
    const manager = new VideoElementManager({ useMutationObserver: true })

    onMounted(async () => {
      if (videoRef.value) {
        await manager.attachListeners(videoRef.value, {
          onPlay: () => console.log('Playing'),
        })
      }
    })

    onUnmounted(() => {
      manager.cleanup()
    })

    return { videoRef }
  },
}
```

### Lazy-Loaded Videos

```typescript
// Video loads when user scrolls into view
const observer = new IntersectionObserver(async (entries) => {
  for (const entry of entries) {
    if (entry.isIntersecting) {
      const videoManager = new VideoElementManager()

      // Video element appears dynamically
      await videoManager.attachListeners('video.lazy-video', {
        onLoadedMetadata: (e) => {
          console.log('Video metadata loaded')
        },
      })

      observer.disconnect()
    }
  }
})

observer.observe(document.querySelector('.video-container'))
```

## Best Practices

### ✅ DO:

- Use `useVideoElementManager` hook in React components
- Enable `useMutationObserver` for dynamic content
- Always call `cleanup()` when done
- Set appropriate `maxRetries` based on your use case
- Enable `debug` during development

### ❌ DON'T:

- Attach listeners without checking if element exists
- Forget to cleanup on unmount/destroy
- Use very short retry delays (< 100ms)
- Disable MutationObserver for SPAs
- Ignore the return value (might be null)

## Migration Guide

### Before (Unsafe):

```typescript
// ❌ Unsafe - will error if video not found
const video = document.querySelector('video')
video.addEventListener('play', handlePlay) // TypeError if video is null
```

### After (Safe):

```typescript
// ✅ Safe - handles missing elements gracefully
import { attachVideoListeners } from '@/utils/videoElementHelpers'

const video = await attachVideoListeners('video', {
  onPlay: handlePlay,
})

if (!video) {
  console.warn('Video element not available')
}
```

## Troubleshooting

### Issue: Listeners still not attaching

**Solution:** Increase `maxRetries` and `retryDelay`:
```typescript
const manager = new VideoElementManager({
  maxRetries: 20,
  retryDelay: 1000,
})
```

### Issue: Performance problems

**Solution:** Disable MutationObserver for static pages:
```typescript
const manager = new VideoElementManager({
  useMutationObserver: false,
})
```

### Issue: Can't debug what's happening

**Solution:** Enable debug mode:
```typescript
const manager = new VideoElementManager({
  debug: true, // Logs all attempts and successes
})
```

## Testing

```typescript
import { VideoElementManager } from '@/utils/videoElementHelpers'

describe('VideoElementManager', () => {
  it('should find video element after delay', async () => {
    const manager = new VideoElementManager({ maxRetries: 5 })

    // Simulate delayed video insertion
    setTimeout(() => {
      const video = document.createElement('video')
      video.id = 'test-video'
      document.body.appendChild(video)
    }, 1000)

    const result = await manager.attachListeners('#test-video', {
      onPlay: jest.fn(),
    })

    expect(result).toBeTruthy()
    expect(result?.tagName).toBe('VIDEO')
  })
})
```
