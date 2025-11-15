import { useState, useCallback } from 'react'
import { useAuth } from './useAuth'
import { apiClient } from '@/services/api'

export interface Project {
  id: string
  title: string
  brief: string
  brand_name: string
  mood?: string
  duration: number
  status: 'draft' | 'generating' | 'ready' | 'failed' | 'COMPLETED'
  created_at: string
  updated_at: string
  cost_estimate?: number
  output_videos?: Record<string, string>
  progress?: number
}

interface CreateProjectInput {
  title: string
  brief: string
  brand_name: string
  mood: string
  duration: number
  primary_color?: string
  secondary_color?: string
  product_image_url?: string
  brand_colors?: string[]
}

export const useProjects = () => {
  const { user } = useAuth()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch all projects
  const fetchProjects = useCallback(async () => {
    if (!user) return

    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.get('/api/projects/')
      // API returns { projects: [...], total, limit, offset }
      setProjects(response.data.projects || [])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch projects'
      setError(message)
      console.error('Error fetching projects:', err)
    } finally {
      setLoading(false)
    }
  }, [user])

  // Create new project
  const createProject = useCallback(
    async (input: CreateProjectInput) => {
      if (!user) throw new Error('Not authenticated')

      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.post('/api/projects/', input)
        const newProject = response.data

        setProjects((prev) => [newProject, ...prev])
        return newProject
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create project'
        setError(message)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [user]
  )

  // Get single project
  const getProject = useCallback(async (projectId: string) => {
    if (!projectId) throw new Error('Project ID is required')
    try {
      const response = await apiClient.get(`/api/projects/${projectId}/`)
      return response.data
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch project'
      setError(message)
      throw err
    }
  }, [])

  // Update project
  const updateProject = useCallback(
    async (projectId: string, updates: Partial<CreateProjectInput>) => {
      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.put(`/api/projects/${projectId}/`, updates)
        const updated = response.data

        setProjects((prev) =>
          prev.map((p) => (p.id === projectId ? updated : p))
        )
        return updated
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update project'
        setError(message)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  // Delete project
  const deleteProject = useCallback(async (projectId: string) => {
    setLoading(true)
    setError(null)

    try {
      await apiClient.delete(`/api/projects/${projectId}/`)
      setProjects((prev) => prev.filter((p) => p.id !== projectId))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete project'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    projects,
    loading,
    error,
    fetchProjects,
    createProject,
    getProject,
    updateProject,
    deleteProject,
  }
}

