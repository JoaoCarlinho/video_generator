/**
 * Axios API client with JWT interceptors
 * All API requests include authentication token
 */

import axios, { type AxiosInstance, AxiosError } from 'axios'

// Get API base URL from environment or use default
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Request interceptor: Add JWT token to all requests
 */
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * Response interceptor: Handle auth errors
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      // Clear auth token
      localStorage.removeItem('authToken')
      localStorage.removeItem('user')
      
      // Redirect to login
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

// Export as 'api' for convenience
export const api = apiClient

export default apiClient

