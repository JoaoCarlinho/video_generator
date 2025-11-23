import { useState, useCallback } from 'react'
import { useAuth } from './useAuth'
import { apiClient } from '@/services/api'

export type ProductGender = 'masculine' | 'feminine' | 'unisex'

export interface Product {
  product_id: string
  brand_id: string
  product_name: string
  product_gender: ProductGender
  front_image_url: string
  back_image_url?: string | null
  top_image_url?: string | null
  left_image_url?: string | null
  right_image_url?: string | null
  campaigns_count?: number
  created_at: string
  updated_at: string
}

export interface CreateProductInput {
  product_name: string
  product_gender: ProductGender
  front_image: File
  back_image?: File
  top_image?: File
  left_image?: File
  right_image?: File
}

export interface PaginatedProducts {
  products: Product[]
  total: number
  page: number
  limit: number
  pages: number
}

export const useProducts = () => {
  const { user } = useAuth()
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch all products for current brand
  const fetchProducts = useCallback(
    async (page: number = 1, limit: number = 20) => {
      if (!user) return

      setLoading(true)
      setError(null)

      try {
        // Backend uses /api/products endpoint
        const response = await apiClient.get<any>('/api/products', {
          params: { page, limit },
        })
        // Map product_id to product_id and product_name to product_name for frontend
        const mappedProducts = (response.data.products || []).map((item: any) => ({
          product_id: item.product_id,
          brand_id: item.brand_id,
          product_name: item.product_name,
          product_gender: item.product_gender,
          front_image_url: item.front_image_url,
          back_image_url: item.back_image_url,
          top_image_url: item.top_image_url,
          left_image_url: item.left_image_url,
          right_image_url: item.right_image_url,
          campaigns_count: item.campaigns_count,
          created_at: item.created_at,
          updated_at: item.updated_at,
        }))
        setProducts(mappedProducts)
        return {
          products: mappedProducts,
          total: response.data.total,
          page: response.data.page,
          limit: response.data.limit,
          pages: response.data.pages,
        }
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || 'Failed to fetch products'
        setError(message)
        console.error('Error fetching products:', err)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [user]
  )

  // Get single product
  const getProduct = useCallback(async (productId: string) => {
    if (!productId) throw new Error('Product ID is required')
    try {
      // Backend uses /api/products endpoint
      const response = await apiClient.get<any>(`/api/products/${productId}`)
      // Map product fields to product fields
      const mappedProduct: Product = {
        product_id: response.data.product_id,
        brand_id: response.data.brand_id,
        product_name: response.data.product_name,
        product_gender: response.data.product_gender,
        front_image_url: response.data.front_image_url,
        back_image_url: response.data.back_image_url,
        top_image_url: response.data.top_image_url,
        left_image_url: response.data.left_image_url,
        right_image_url: response.data.right_image_url,
        campaigns_count: response.data.campaigns_count,
        created_at: response.data.created_at,
        updated_at: response.data.updated_at,
      }
      return mappedProduct
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || 'Failed to fetch product'
      setError(message)
      throw err
    }
  }, [])

  // Create product
  const createProduct = useCallback(
    async (input: CreateProductInput) => {
      if (!user) throw new Error('Not authenticated')

      setLoading(true)
      setError(null)

      try {
        const formData = new FormData()
        // Backend expects product_name and product_gender
        formData.append('product_name', input.product_name)
        formData.append('product_gender', input.product_gender)
        formData.append('front_image', input.front_image)

        if (input.back_image) formData.append('back_image', input.back_image)
        if (input.top_image) formData.append('top_image', input.top_image)
        if (input.left_image) formData.append('left_image', input.left_image)
        if (input.right_image) formData.append('right_image', input.right_image)

        // Backend uses /api/products endpoint
        const response = await apiClient.post<any>('/api/products', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })

        // Map response from product fields to product fields
        const mappedProduct: Product = {
          product_id: response.data.product_id,
          brand_id: response.data.brand_id,
          product_name: response.data.product_name,
          product_gender: response.data.product_gender,
          front_image_url: response.data.front_image_url,
          back_image_url: response.data.back_image_url,
          top_image_url: response.data.top_image_url,
          left_image_url: response.data.left_image_url,
          right_image_url: response.data.right_image_url,
          campaigns_count: response.data.campaigns_count,
          created_at: response.data.created_at,
          updated_at: response.data.updated_at,
        }

        setProducts((prev) => [mappedProduct, ...prev])
        return mappedProduct
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || 'Failed to create product'
        setError(message)
        console.error('Error creating product:', err)
        throw new Error(message)
      } finally {
        setLoading(false)
      }
    },
    [user]
  )

  // Delete product
  const deleteProduct = useCallback(async (productId: string) => {
    setLoading(true)
    setError(null)

    try {
      // Backend uses /api/products endpoint
      await apiClient.delete(`/api/products/${productId}`)
      setProducts((prev) => prev.filter((p) => p.product_id !== productId))
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || 'Failed to delete product'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    products,
    loading,
    error,
    fetchProducts,
    getProduct,
    createProduct,
    deleteProduct,
  }
}

