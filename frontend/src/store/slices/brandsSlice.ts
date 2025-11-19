/**
 * Brands Slice - Manages brand state with normalized structure
 * Uses entity adapter for efficient CRUD operations
 */

import { createSlice, createEntityAdapter, type PayloadAction } from '@reduxjs/toolkit'
import type { Brand } from '../../types'
import type { RootState } from '../index'
import { api } from '../api'

// Entity adapter for normalized state
const brandsAdapter = createEntityAdapter<Brand, string>({
  selectId: (brand) => brand.id,
  sortComparer: (a, b) => b.created_at.localeCompare(a.created_at), // Newest first
})

const initialState = brandsAdapter.getInitialState({
  selectedBrandId: null as string | null,
  isLoading: false,
  error: null as string | null,
})

// Slice
const brandsSlice = createSlice({
  name: 'brands',
  initialState,
  reducers: {
    selectBrand: (state, action: PayloadAction<string | null>) => {
      state.selectedBrandId = action.payload
    },
    clearBrandsError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    // Get brands
    builder
      .addMatcher(api.endpoints.getBrands.matchPending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addMatcher(api.endpoints.getBrands.matchFulfilled, (state, action) => {
        brandsAdapter.setAll(state, action.payload)
        state.isLoading = false
        state.error = null
      })
      .addMatcher(api.endpoints.getBrands.matchRejected, (state, action) => {
        state.isLoading = false
        state.error = action.error.message || 'Failed to fetch brands'
      })

    // Create brand
    builder
      .addMatcher(api.endpoints.createBrand.matchPending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addMatcher(api.endpoints.createBrand.matchFulfilled, (state, action) => {
        brandsAdapter.addOne(state, action.payload)
        state.selectedBrandId = action.payload.id
        state.isLoading = false
        state.error = null
      })
      .addMatcher(api.endpoints.createBrand.matchRejected, (state, action) => {
        state.isLoading = false
        state.error = action.error.message || 'Failed to create brand'
      })

    // Update brand
    builder
      .addMatcher(api.endpoints.updateBrand.matchPending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addMatcher(api.endpoints.updateBrand.matchFulfilled, (state, action) => {
        brandsAdapter.updateOne(state, {
          id: action.payload.id,
          changes: action.payload,
        })
        state.isLoading = false
        state.error = null
      })
      .addMatcher(api.endpoints.updateBrand.matchRejected, (state, action) => {
        state.isLoading = false
        state.error = action.error.message || 'Failed to update brand'
      })

    // Delete brand
    builder
      .addMatcher(api.endpoints.deleteBrand.matchPending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addMatcher(api.endpoints.deleteBrand.matchFulfilled, (state, action) => {
        const brandId = action.meta.arg.originalArgs
        brandsAdapter.removeOne(state, brandId)
        if (state.selectedBrandId === brandId) {
          state.selectedBrandId = null
        }
        state.isLoading = false
        state.error = null
      })
      .addMatcher(api.endpoints.deleteBrand.matchRejected, (state, action) => {
        state.isLoading = false
        state.error = action.error.message || 'Failed to delete brand'
      })
  },
})

export const { selectBrand, clearBrandsError } = brandsSlice.actions

// Export selectors
export const brandsSelectors = brandsAdapter.getSelectors<RootState>(
  (state) => state.brands
)

// Custom selectors
export const selectSelectedBrandId = (state: RootState) => state.brands.selectedBrandId
export const selectSelectedBrand = (state: RootState) => {
  const selectedId = state.brands.selectedBrandId
  return selectedId ? brandsSelectors.selectById(state, selectedId) : null
}
export const selectBrandsLoading = (state: RootState) => state.brands.isLoading
export const selectBrandsError = (state: RootState) => state.brands.error

export default brandsSlice.reducer
