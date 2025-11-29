/**
 * Editor Slice - Redux state management for video timeline editor
 * Manages timeline clips, media library, and editing state
 */

import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

// ============================================================================
// Types
// ============================================================================

export interface TimelineClip {
  id: string
  libraryId: string
  name: string
  trackType: 'video' | 'audio'
  duration: number
  trimStart: number
  trimEnd: number
  effectiveDuration: number
  position: number
  videoUrl?: string
  audioUrl?: string
  color?: string
}

export interface MediaLibraryItem {
  id: string
  name: string
  type: 'video' | 'audio'
  duration: number
  url: string
  thumbnailUrl?: string
  sceneIndex?: number
}

interface EditorState {
  // Timeline state
  timelineVideoClips: TimelineClip[]
  timelineAudioClips: TimelineClip[]
  timelineTotalDuration: number

  // Media library
  mediaLibrary: MediaLibraryItem[]

  // Playback state
  currentTime: number
  isPlaying: boolean

  // Selection state
  selectedClipId: string | null

  // Loading states
  isLoading: boolean
  isSaving: boolean
  error: string | null
}

// ============================================================================
// Initial State
// ============================================================================

const initialState: EditorState = {
  timelineVideoClips: [],
  timelineAudioClips: [],
  timelineTotalDuration: 0,
  mediaLibrary: [],
  currentTime: 0,
  isPlaying: false,
  selectedClipId: null,
  isLoading: false,
  isSaving: false,
  error: null,
}

// ============================================================================
// Slice
// ============================================================================

const editorSlice = createSlice({
  name: 'editor',
  initialState,
  reducers: {
    // Timeline clips
    setTimelineVideoClips: (state, action: PayloadAction<TimelineClip[]>) => {
      state.timelineVideoClips = action.payload
      state.timelineTotalDuration = calculateTotalDuration(action.payload, state.timelineAudioClips)
    },

    setTimelineAudioClips: (state, action: PayloadAction<TimelineClip[]>) => {
      state.timelineAudioClips = action.payload
      state.timelineTotalDuration = calculateTotalDuration(state.timelineVideoClips, action.payload)
    },

    addVideoClip: (state, action: PayloadAction<TimelineClip>) => {
      state.timelineVideoClips.push(action.payload)
      state.timelineTotalDuration = calculateTotalDuration(state.timelineVideoClips, state.timelineAudioClips)
    },

    addAudioClip: (state, action: PayloadAction<TimelineClip>) => {
      state.timelineAudioClips.push(action.payload)
      state.timelineTotalDuration = calculateTotalDuration(state.timelineVideoClips, state.timelineAudioClips)
    },

    updateClip: (state, action: PayloadAction<{ id: string; updates: Partial<TimelineClip> }>) => {
      const { id, updates } = action.payload

      const videoIndex = state.timelineVideoClips.findIndex(c => c.id === id)
      if (videoIndex !== -1) {
        state.timelineVideoClips[videoIndex] = { ...state.timelineVideoClips[videoIndex], ...updates }
      }

      const audioIndex = state.timelineAudioClips.findIndex(c => c.id === id)
      if (audioIndex !== -1) {
        state.timelineAudioClips[audioIndex] = { ...state.timelineAudioClips[audioIndex], ...updates }
      }

      state.timelineTotalDuration = calculateTotalDuration(state.timelineVideoClips, state.timelineAudioClips)
    },

    removeClip: (state, action: PayloadAction<string>) => {
      state.timelineVideoClips = state.timelineVideoClips.filter(c => c.id !== action.payload)
      state.timelineAudioClips = state.timelineAudioClips.filter(c => c.id !== action.payload)
      state.timelineTotalDuration = calculateTotalDuration(state.timelineVideoClips, state.timelineAudioClips)

      if (state.selectedClipId === action.payload) {
        state.selectedClipId = null
      }
    },

    // Media library
    setMediaLibrary: (state, action: PayloadAction<MediaLibraryItem[]>) => {
      state.mediaLibrary = action.payload
    },

    addMediaItem: (state, action: PayloadAction<MediaLibraryItem>) => {
      state.mediaLibrary.push(action.payload)
    },

    // Playback
    setCurrentTime: (state, action: PayloadAction<number>) => {
      state.currentTime = action.payload
    },

    setIsPlaying: (state, action: PayloadAction<boolean>) => {
      state.isPlaying = action.payload
    },

    togglePlayback: (state) => {
      state.isPlaying = !state.isPlaying
    },

    // Selection
    setSelectedClipId: (state, action: PayloadAction<string | null>) => {
      state.selectedClipId = action.payload
    },

    // Loading states
    setIsLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload
    },

    setIsSaving: (state, action: PayloadAction<boolean>) => {
      state.isSaving = action.payload
    },

    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload
    },

    // Reset state
    resetEditor: () => initialState,
  },
})

// ============================================================================
// Helpers
// ============================================================================

function calculateTotalDuration(videoClips: TimelineClip[], audioClips: TimelineClip[]): number {
  let maxDuration = 0

  for (const clip of videoClips) {
    const clipEnd = clip.position + clip.effectiveDuration
    if (clipEnd > maxDuration) maxDuration = clipEnd
  }

  for (const clip of audioClips) {
    const clipEnd = clip.position + clip.effectiveDuration
    if (clipEnd > maxDuration) maxDuration = clipEnd
  }

  return maxDuration
}

// ============================================================================
// Selectors
// ============================================================================

export const selectTimelineVideoClips = (state: { editor: EditorState }) => state.editor.timelineVideoClips
export const selectTimelineAudioClips = (state: { editor: EditorState }) => state.editor.timelineAudioClips
export const selectTimelineTotalDuration = (state: { editor: EditorState }) => state.editor.timelineTotalDuration
export const selectMediaLibrary = (state: { editor: EditorState }) => state.editor.mediaLibrary
export const selectCurrentTime = (state: { editor: EditorState }) => state.editor.currentTime
export const selectIsPlaying = (state: { editor: EditorState }) => state.editor.isPlaying
export const selectSelectedClipId = (state: { editor: EditorState }) => state.editor.selectedClipId
export const selectIsLoading = (state: { editor: EditorState }) => state.editor.isLoading
export const selectIsSaving = (state: { editor: EditorState }) => state.editor.isSaving
export const selectError = (state: { editor: EditorState }) => state.editor.error

export const selectTimelineState = (state: { editor: EditorState }) => ({
  video_clips: state.editor.timelineVideoClips.map(clip => ({
    id: clip.id,
    library_id: clip.libraryId,
    name: clip.name,
    track_type: clip.trackType,
    duration: clip.duration,
    trim_start: clip.trimStart,
    trim_end: clip.trimEnd,
    effective_duration: clip.effectiveDuration,
    position: clip.position,
  })),
  audio_clips: state.editor.timelineAudioClips.map(clip => ({
    id: clip.id,
    library_id: clip.libraryId,
    name: clip.name,
    track_type: clip.trackType,
    duration: clip.duration,
    trim_start: clip.trimStart,
    trim_end: clip.trimEnd,
    effective_duration: clip.effectiveDuration,
    position: clip.position,
  })),
  total_duration: state.editor.timelineTotalDuration,
})

// ============================================================================
// Exports
// ============================================================================

export const {
  setTimelineVideoClips,
  setTimelineAudioClips,
  addVideoClip,
  addAudioClip,
  updateClip,
  removeClip,
  setMediaLibrary,
  addMediaItem,
  setCurrentTime,
  setIsPlaying,
  togglePlayback,
  setSelectedClipId,
  setIsLoading,
  setIsSaving,
  setError,
  resetEditor,
} = editorSlice.actions

export default editorSlice.reducer
