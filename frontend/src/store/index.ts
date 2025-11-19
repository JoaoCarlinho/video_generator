/**
 * Redux Store Configuration
 * Configures Redux Toolkit store with RTK Query middleware
 */

import { configureStore } from '@reduxjs/toolkit'
import { api } from './api'
import authReducer from './slices/authSlice'
import brandsReducer from './slices/brandsSlice'
import productsReducer from './slices/productsSlice'

export const store = configureStore({
  reducer: {
    // RTK Query API slice
    [api.reducerPath]: api.reducer,

    // Feature slices
    auth: authReducer,
    brands: brandsReducer,
    products: productsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(api.middleware),
  devTools: import.meta.env.DEV, // Enable Redux DevTools in development
})

// Export types for TypeScript
export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
