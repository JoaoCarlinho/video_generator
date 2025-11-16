/**
 * IndexedDB Video Storage Service
 * Stores temporary and final video files for preview before S3 upload
 */

export interface VideoStorageEntry {
  projectId: string
  aspectRatio: '16:9'
  videoBlob: Blob
  timestamp: number
  isFinal: boolean // true = ready to upload to S3, false = temporary preview
}

const DB_NAME = 'GenAdsVideoStorage'
const STORE_NAME = 'videos'
const DB_VERSION = 1

// Initialize IndexedDB
function getDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, {
          keyPath: ['projectId', 'aspectRatio'],
        })
      }
    }
  })
}

// Store a video blob in IndexedDB
export async function storeVideo(
  projectId: string,
  aspectRatio: '16:9',
  videoBlob: Blob,
  isFinal: boolean = false
): Promise<void> {
  const db = await getDB()
  const tx = db.transaction([STORE_NAME], 'readwrite')
  const store = tx.objectStore(STORE_NAME)

  const entry: VideoStorageEntry = {
    projectId,
    aspectRatio,
    videoBlob,
    timestamp: Date.now(),
    isFinal,
  }

  return new Promise((resolve, reject) => {
    const request = store.put(entry)
    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve()
  })
}

// Retrieve a video blob from IndexedDB
export async function getVideo(
  projectId: string,
  aspectRatio: '16:9'
): Promise<Blob | null> {
  const db = await getDB()
  const tx = db.transaction([STORE_NAME], 'readonly')
  const store = tx.objectStore(STORE_NAME)

  return new Promise((resolve, reject) => {
    const request = store.get([projectId, aspectRatio])
    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const entry = request.result as VideoStorageEntry | undefined
      resolve(entry ? entry.videoBlob : null)
    }
  })
}

// Get all videos for a project
export async function getProjectVideos(
  projectId: string
): Promise<Record<'16:9', Blob | null>> {
  const db = await getDB()
  const tx = db.transaction([STORE_NAME], 'readonly')
  const store = tx.objectStore(STORE_NAME)

  return new Promise((resolve, reject) => {
    const request = store.getAll()
    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const entries = request.result as VideoStorageEntry[]
      const projectEntries = entries.filter((e) => e.projectId === projectId)

      const result: Record<'16:9', Blob | null> = {
        '16:9': null,
      }

      projectEntries.forEach((entry) => {
        result[entry.aspectRatio] = entry.videoBlob
      })

      resolve(result)
    }
  })
}

// Mark videos as finalized (ready to upload)
export async function markAsFinalized(projectId: string): Promise<void> {
  const db = await getDB()
  const tx = db.transaction([STORE_NAME], 'readwrite')
  const store = tx.objectStore(STORE_NAME)

  return new Promise((resolve, reject) => {
    const request = store.getAll()
    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const entries = request.result as VideoStorageEntry[]
      const projectEntries = entries.filter((e) => e.projectId === projectId)

      projectEntries.forEach((entry) => {
        entry.isFinal = true
        store.put(entry)
      })

      resolve()
    }
  })
}

// Delete all videos for a project from IndexedDB
export async function deleteProjectVideos(projectId: string): Promise<void> {
  const db = await getDB()
  const tx = db.transaction([STORE_NAME], 'readwrite')
  const store = tx.objectStore(STORE_NAME)

  return new Promise((resolve, reject) => {
    const request = store.getAll()
    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const entries = request.result as VideoStorageEntry[]
      const projectEntries = entries.filter((e) => e.projectId === projectId)

      projectEntries.forEach((entry) => {
        store.delete([entry.projectId, entry.aspectRatio])
      })

      resolve()
    }
  })
}

// Get video as blob URL (for preview)
export async function getVideoURL(
  projectId: string,
  aspectRatio: '16:9'
): Promise<string | null> {
  const videoBlob = await getVideo(projectId, aspectRatio)
  if (!videoBlob) return null
  return URL.createObjectURL(videoBlob)
}

// Get storage usage in bytes
export async function getStorageUsage(projectId: string): Promise<number> {
  const db = await getDB()
  const tx = db.transaction([STORE_NAME], 'readonly')
  const store = tx.objectStore(STORE_NAME)

  return new Promise((resolve, reject) => {
    const request = store.getAll()
    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const entries = request.result as VideoStorageEntry[]
      const projectEntries = entries.filter((e) => e.projectId === projectId)
      const totalSize = projectEntries.reduce((sum, entry) => sum + entry.videoBlob.size, 0)
      resolve(totalSize)
    }
  })
}

// Format bytes to human readable format
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

