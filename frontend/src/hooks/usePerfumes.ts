import { useState, useCallback } from 'react'
import { useAuth } from './useAuth'
import { apiClient } from '@/services/api'

export type PerfumeGender = 'masculine' | 'feminine' | 'unisex'

export interface Perfume {
  perfume_id: string
  brand_id: string
  perfume_name: string
  perfume_gender: PerfumeGender
  front_image_url: string
  back_image_url?: string | null
  top_image_url?: string | null
  left_image_url?: string | null
  right_image_url?: string | null
  campaigns_count?: number
  created_at: string
  updated_at: string
}

export interface CreatePerfumeInput {
  perfume_name: string
  perfume_gender: PerfumeGender
  front_image: File
  back_image?: File
  top_image?: File
  left_image?: File
  right_image?: File
}

export interface PaginatedPerfumes {
  perfumes: Perfume[]
  total: number
  page: number
  limit: number
  pages: number
}

export const usePerfumes = () => {
  const { user } = useAuth()
  const [perfumes, setPerfumes] = useState<Perfume[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch all perfumes for current brand
  const fetchPerfumes = useCallback(
    async (page: number = 1, limit: number = 20) => {
      if (!user) return

      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.get<PaginatedPerfumes>('/api/perfumes', {
          params: { page, limit },
        })
        setPerfumes(response.data.perfumes || [])
        return response.data
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || 'Failed to fetch perfumes'
        setError(message)
        console.error('Error fetching perfumes:', err)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [user]
  )

  // Get single perfume
  const getPerfume = useCallback(async (perfumeId: string) => {
    if (!perfumeId) throw new Error('Perfume ID is required')
    try {
      const response = await apiClient.get<Perfume>(`/api/perfumes/${perfumeId}`)
      return response.data
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || 'Failed to fetch perfume'
      setError(message)
      throw err
    }
  }, [])

  // Create perfume
  const createPerfume = useCallback(
    async (input: CreatePerfumeInput) => {
      if (!user) throw new Error('Not authenticated')

      setLoading(true)
      setError(null)

      try {
        const formData = new FormData()
        formData.append('perfume_name', input.perfume_name)
        formData.append('perfume_gender', input.perfume_gender)
        formData.append('front_image', input.front_image)
        
        if (input.back_image) formData.append('back_image', input.back_image)
        if (input.top_image) formData.append('top_image', input.top_image)
        if (input.left_image) formData.append('left_image', input.left_image)
        if (input.right_image) formData.append('right_image', input.right_image)

        const response = await apiClient.post<Perfume>('/api/perfumes', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })

        setPerfumes((prev) => [response.data, ...prev])
        return response.data
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || 'Failed to create perfume'
        setError(message)
        console.error('Error creating perfume:', err)
        throw new Error(message)
      } finally {
        setLoading(false)
      }
    },
    [user]
  )

  // Delete perfume
  const deletePerfume = useCallback(async (perfumeId: string) => {
    setLoading(true)
    setError(null)

    try {
      await apiClient.delete(`/api/perfumes/${perfumeId}`)
      setPerfumes((prev) => prev.filter((p) => p.perfume_id !== perfumeId))
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || 'Failed to delete perfume'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    perfumes,
    loading,
    error,
    fetchPerfumes,
    getPerfume,
    createPerfume,
    deletePerfume,
  }
}

