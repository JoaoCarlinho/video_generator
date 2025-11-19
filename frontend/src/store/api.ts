/**
 * RTK Query API Slice
 * Centralized API definitions for brands, products, and other resources
 */

import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { Brand, Product, Campaign } from '../types'

// Get API base URL from environment or use default
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: API_BASE_URL,
    prepareHeaders: (headers) => {
      // Add JWT token to all requests
      const token = localStorage.getItem('authToken')
      if (token) {
        headers.set('Authorization', `Bearer ${token}`)
      }
      return headers
    },
  }),
  tagTypes: ['Brand', 'Product', 'Campaign'],
  endpoints: (builder) => ({
    // Brand endpoints
    getBrands: builder.query<Brand[], void>({
      query: () => '/api/brands',
      providesTags: ['Brand'],
    }),
    getBrandById: builder.query<Brand, string>({
      query: (brandId) => `/api/brands/${brandId}`,
      providesTags: (_result, _error, brandId) => [{ type: 'Brand', id: brandId }],
    }),
    createBrand: builder.mutation<Brand, Omit<Brand, 'id' | 'user_id' | 'created_at' | 'updated_at'>>({
      query: (brandData) => ({
        url: '/api/brands',
        method: 'POST',
        body: brandData,
      }),
      invalidatesTags: ['Brand'],
    }),
    updateBrand: builder.mutation<Brand, { brandId: string; data: Partial<Brand> }>({
      query: ({ brandId, data }) => ({
        url: `/api/brands/${brandId}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (_result, _error, { brandId }) => [{ type: 'Brand', id: brandId }, 'Brand'],
    }),
    deleteBrand: builder.mutation<void, string>({
      query: (brandId) => ({
        url: `/api/brands/${brandId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Brand'],
    }),

    // Product endpoints
    getProducts: builder.query<Product[], string>({
      query: (brandId) => `/api/brands/${brandId}/products`,
      providesTags: (result) =>
        result
          ? [
              ...result.map(({ id }) => ({ type: 'Product' as const, id })),
              { type: 'Product', id: 'LIST' },
            ]
          : [{ type: 'Product', id: 'LIST' }],
    }),
    getProductById: builder.query<Product, string>({
      query: (productId) => `/api/products/${productId}`,
      providesTags: (_result, _error, productId) => [{ type: 'Product', id: productId }],
    }),
    createProduct: builder.mutation<
      Product,
      { brandId: string; data: Omit<Product, 'id' | 'brand_id' | 'created_at' | 'updated_at'> }
    >({
      query: ({ brandId, data }) => ({
        url: `/api/brands/${brandId}/products`,
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'Product', id: 'LIST' }],
    }),
    updateProduct: builder.mutation<Product, { productId: string; data: Partial<Product> }>({
      query: ({ productId, data }) => ({
        url: `/api/products/${productId}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (_result, _error, { productId }) => [
        { type: 'Product', id: productId },
        { type: 'Product', id: 'LIST' },
      ],
    }),
    deleteProduct: builder.mutation<void, string>({
      query: (productId) => ({
        url: `/api/products/${productId}`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'Product', id: 'LIST' }],
    }),

    // Campaign endpoints
    getCampaigns: builder.query<Campaign[], string>({
      query: (productId) => `/api/products/${productId}/campaigns`,
      providesTags: (result) =>
        result
          ? [
              ...result.map(({ id }) => ({ type: 'Campaign' as const, id })),
              { type: 'Campaign', id: 'LIST' },
            ]
          : [{ type: 'Campaign', id: 'LIST' }],
    }),
    getCampaignById: builder.query<Campaign, string>({
      query: (campaignId) => `/api/campaigns/${campaignId}`,
      providesTags: (_result, _error, campaignId) => [{ type: 'Campaign', id: campaignId }],
    }),
    createCampaign: builder.mutation<
      Campaign,
      { productId: string; data: Omit<Campaign, 'id' | 'product_id' | 'display_name' | 'status' | 'created_at' | 'updated_at'> }
    >({
      query: ({ productId, data }) => ({
        url: `/api/products/${productId}/campaigns`,
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'Campaign', id: 'LIST' }],
    }),
    updateCampaign: builder.mutation<Campaign, { campaignId: string; data: Partial<Campaign> }>({
      query: ({ campaignId, data }) => ({
        url: `/api/campaigns/${campaignId}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (_result, _error, { campaignId }) => [
        { type: 'Campaign', id: campaignId },
        { type: 'Campaign', id: 'LIST' },
      ],
    }),
    deleteCampaign: builder.mutation<void, string>({
      query: (campaignId) => ({
        url: `/api/campaigns/${campaignId}`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'Campaign', id: 'LIST' }],
    }),
  }),
})

// Export hooks for usage in components
export const {
  useGetBrandsQuery,
  useGetBrandByIdQuery,
  useCreateBrandMutation,
  useUpdateBrandMutation,
  useDeleteBrandMutation,
  useGetProductsQuery,
  useGetProductByIdQuery,
  useCreateProductMutation,
  useUpdateProductMutation,
  useDeleteProductMutation,
  useGetCampaignsQuery,
  useGetCampaignByIdQuery,
  useCreateCampaignMutation,
  useUpdateCampaignMutation,
  useDeleteCampaignMutation,
} = api
