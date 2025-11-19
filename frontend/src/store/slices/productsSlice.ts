/**
 * Products Slice - Manages product state with normalized structure
 * Uses entity adapter for efficient CRUD operations
 */

import { createSlice, createEntityAdapter } from '@reduxjs/toolkit'
import type { Product } from '../../types'
import type { RootState } from '../index'
import { api } from '../api'

// Entity adapter for normalized state
const productsAdapter = createEntityAdapter<Product, string>({
  selectId: (product) => product.id,
  sortComparer: (a, b) => b.created_at.localeCompare(a.created_at), // Newest first
})

const initialState = productsAdapter.getInitialState({
  isLoading: false,
  error: null as string | null,
})

// Slice
const productsSlice = createSlice({
  name: 'products',
  initialState,
  reducers: {
    clearProductsError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    // Get products
    builder
      .addMatcher(api.endpoints.getProducts.matchPending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addMatcher(api.endpoints.getProducts.matchFulfilled, (state, action) => {
        productsAdapter.setAll(state, action.payload)
        state.isLoading = false
        state.error = null
      })
      .addMatcher(api.endpoints.getProducts.matchRejected, (state, action) => {
        state.isLoading = false
        state.error = action.error.message || 'Failed to fetch products'
      })

    // Create product
    builder
      .addMatcher(api.endpoints.createProduct.matchPending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addMatcher(api.endpoints.createProduct.matchFulfilled, (state, action) => {
        productsAdapter.addOne(state, action.payload)
        state.isLoading = false
        state.error = null
      })
      .addMatcher(api.endpoints.createProduct.matchRejected, (state, action) => {
        state.isLoading = false
        state.error = action.error.message || 'Failed to create product'
      })

    // Update product
    builder
      .addMatcher(api.endpoints.updateProduct.matchPending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addMatcher(api.endpoints.updateProduct.matchFulfilled, (state, action) => {
        productsAdapter.updateOne(state, {
          id: action.payload.id,
          changes: action.payload,
        })
        state.isLoading = false
        state.error = null
      })
      .addMatcher(api.endpoints.updateProduct.matchRejected, (state, action) => {
        state.isLoading = false
        state.error = action.error.message || 'Failed to update product'
      })

    // Delete product
    builder
      .addMatcher(api.endpoints.deleteProduct.matchPending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addMatcher(api.endpoints.deleteProduct.matchFulfilled, (state, action) => {
        const productId = action.meta.arg.originalArgs
        productsAdapter.removeOne(state, productId)
        state.isLoading = false
        state.error = null
      })
      .addMatcher(api.endpoints.deleteProduct.matchRejected, (state, action) => {
        state.isLoading = false
        state.error = action.error.message || 'Failed to delete product'
      })
  },
})

export const { clearProductsError } = productsSlice.actions

// Export selectors
export const productsSelectors = productsAdapter.getSelectors<RootState>(
  (state) => state.products
)

// Custom selectors
export const selectProductsLoading = (state: RootState) => state.products.isLoading
export const selectProductsError = (state: RootState) => state.products.error
export const selectProductsByBrand = (state: RootState, brandId: string) => {
  return productsSelectors.selectAll(state).filter((product) => product.brand_id === brandId)
}

export default productsSlice.reducer
