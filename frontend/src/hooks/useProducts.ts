import { useState, useCallback } from 'react'
import { useAuth } from './useAuth'
import { useBrand } from './useBrand'
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
  const { brand } = useBrand()
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch all products for current brand
  const fetchProducts = useCallback(
    async (page: number = 1, limit: number = 20) => {
      if (!user || !brand) return

      setLoading(true)
      setError(null)

      try {
        // Backend expects /api/brands/{brand_id}/products with limit and offset
        const offset = (page - 1) * limit
        const response = await apiClient.get<any>(`/api/brands/${brand.id}/products`, {
          params: { limit, offset },
        })

        // Backend returns array of ProductResponse objects
        // Map backend fields (id, name, image_urls[]) to frontend fields
        const mappedProducts = (response.data || []).map((item: any) => ({
          product_id: item.id,
          brand_id: item.brand_id,
          product_name: item.name,
          product_gender: item.product_gender,
          front_image_url: item.image_urls?.[0] || '',
          back_image_url: item.image_urls?.[1] || null,
          top_image_url: item.image_urls?.[2] || null,
          left_image_url: item.image_urls?.[3] || null,
          right_image_url: item.image_urls?.[4] || null,
          campaigns_count: 0, // TODO: Add campaigns count to backend
          created_at: item.created_at,
          updated_at: item.updated_at,
        }))
        setProducts(mappedProducts)

        // Create pagination metadata
        const total = mappedProducts.length
        const pages = Math.ceil(total / limit)

        return {
          products: mappedProducts,
          total,
          page,
          limit,
          pages,
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
    [user, brand]
  )

  // Get single product
  const getProduct = useCallback(async (productId: string) => {
    if (!productId) throw new Error('Product ID is required')
    try {
      // Backend uses /api/products endpoint and returns ProductResponse
      const response = await apiClient.get<any>(`/api/products/${productId}`)
      // Map backend fields (id, name, image_urls[]) to frontend fields
      const mappedProduct: Product = {
        product_id: response.data.id,
        brand_id: response.data.brand_id,
        product_name: response.data.name,
        product_gender: response.data.product_gender,
        front_image_url: response.data.image_urls?.[0] || '',
        back_image_url: response.data.image_urls?.[1] || null,
        top_image_url: response.data.image_urls?.[2] || null,
        left_image_url: response.data.image_urls?.[3] || null,
        right_image_url: response.data.image_urls?.[4] || null,
        campaigns_count: 0, // TODO: Add campaigns count to backend
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
      if (!brand) throw new Error('No brand found')

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

        // Backend expects /api/brands/{brand_id}/products and returns ProductResponse
        // Note: Don't set Content-Type manually for FormData - let axios set it with the boundary
        const response = await apiClient.post<any>(`/api/brands/${brand.id}/products`, formData)

        // Map backend fields (id, name, image_urls[]) to frontend fields
        const mappedProduct: Product = {
          product_id: response.data.id,
          brand_id: response.data.brand_id,
          product_name: response.data.name,
          product_gender: response.data.product_gender,
          front_image_url: response.data.image_urls?.[0] || '',
          back_image_url: response.data.image_urls?.[1] || null,
          top_image_url: response.data.image_urls?.[2] || null,
          left_image_url: response.data.image_urls?.[3] || null,
          right_image_url: response.data.image_urls?.[4] || null,
          campaigns_count: 0, // TODO: Add campaigns count to backend
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
    [user, brand]
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

