/**
 * ProductManagement - Page for managing products associated with a brand
 * Displays product list and creation form
 * Uses Redux/RTK Query for state management
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ProductForm } from '../components/forms/ProductForm'
import { ProductList, type Product } from '../components/PageComponents/ProductList'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Plus, ArrowLeft } from 'lucide-react'
import type { ProductFormData } from '../schemas/productSchema'
import {
  useGetProductsQuery,
  useCreateProductMutation,
  useDeleteProductMutation,
} from '../store/api'
import { api } from '../services/api'
import axios from 'axios'

export const ProductManagement = () => {
  const { brandId } = useParams<{ brandId: string }>()
  const navigate = useNavigate()

  // RTK Query hooks
  const { data: products = [], isLoading } = useGetProductsQuery(brandId || '', {
    skip: !brandId,
  })
  const [createProduct, { isLoading: isSubmitting }] = useCreateProductMutation()
  const [deleteProduct, { isLoading: isDeleting }] = useDeleteProductMutation()

  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  /**
   * Upload a single file to S3 using presigned URL
   */
  const uploadFileToS3 = async (file: File): Promise<string> => {
    try {
      // Request presigned URL from backend
      const presignedResponse = await api.post('/api/storage/presigned-url', {
        filename: file.name,
        content_type: file.type,
        asset_type: 'product',  // Required field for product images
      })

      const { upload_url, file_url } = presignedResponse.data

      // Upload file directly to S3
      await axios.put(upload_url, file, {
        headers: {
          'Content-Type': file.type,
        },
      })

      // Return the public file URL for storage in database
      return file_url
    } catch (error) {
      console.error('S3 upload error:', error)
      throw new Error(`Failed to upload ${file.name}`)
    }
  }

  /**
   * Handle product creation
   */
  const handleCreateProduct = async (data: ProductFormData) => {
    if (!brandId) return

    setError(null)

    try {
      // Upload product images to S3
      console.log(`Uploading ${data.image_files.length} product images to S3...`)
      const uploadPromises = data.image_files.map((file) => uploadFileToS3(file))
      const imageUrls = await Promise.all(uploadPromises)
      console.log('Image uploads complete:', imageUrls)

      // Prepare product data for API
      const productData = {
        product_type: data.product_type || undefined,
        name: data.name,
        product_gender: data.product_gender || undefined,
        product_attributes: data.product_attributes || undefined,
        icp_segment: data.icp_segment,
        image_urls: imageUrls,
      }

      // Create product via RTK Query mutation
      console.log('Creating product:', productData)
      await createProduct({ brandId, data: productData }).unwrap()

      console.log('Product created successfully')

      // Show success toast
      if (window.showToast) {
        window.showToast('Product created successfully!', 'success')
      }

      // Hide form
      setShowForm(false)
    } catch (err: any) {
      console.error('Product creation error:', err)

      // Extract error message
      let errorMessage = 'Failed to create product. Please try again.'
      if (err.data?.detail) {
        errorMessage = err.data.detail
      } else if (err.message) {
        errorMessage = err.message
      }

      setError(errorMessage)

      // Show error toast
      if (window.showToast) {
        window.showToast(errorMessage, 'error')
      }
    }
  }

  /**
   * Handle product deletion
   */
  const handleDeleteProduct = async (productId: string) => {
    try {
      await deleteProduct(productId).unwrap()

      // Show success toast
      if (window.showToast) {
        window.showToast('Product deleted successfully', 'success')
      }
    } catch (err: any) {
      console.error('Product deletion error:', err)

      let errorMessage = 'Failed to delete product'
      if (err.data?.detail) {
        errorMessage = err.data.detail
      }

      if (window.showToast) {
        window.showToast(errorMessage, 'error')
      }
    }
  }

  /**
   * Handle product edit (placeholder for now)
   */
  const handleEditProduct = (product: Product) => {
    console.log('Edit product:', product)
    // TODO: Implement edit functionality in future story
    if (window.showToast) {
      window.showToast('Edit functionality coming soon', 'info')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="outline" size="sm" onClick={() => navigate('/dashboard')}>
                <ArrowLeft className="w-4 h-4 mr-1" />
                Back
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Product Catalog</h1>
                <p className="text-gray-600 mt-1">Manage your product line</p>
              </div>
            </div>
            <Button onClick={() => setShowForm(!showForm)}>
              <Plus className="w-4 h-4 mr-1" />
              {showForm ? 'Hide Form' : 'Add Product'}
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-error-50 border border-error-200 rounded-lg">
            <p className="text-error-700 text-sm">{error}</p>
          </div>
        )}

        {/* Product Creation Form */}
        {showForm && (
          <Card className="p-8 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Create New Product</h2>
            <ProductForm
              onSubmit={handleCreateProduct}
              onCancel={() => setShowForm(false)}
              isSubmitting={isSubmitting}
            />
          </Card>
        )}

        {/* Product List */}
        {isLoading ? (
          <Card className="p-12 text-center">
            <p className="text-gray-500">Loading products...</p>
          </Card>
        ) : (
          <ProductList
            products={products}
            onEdit={handleEditProduct}
            onDelete={handleDeleteProduct}
            isDeleting={isDeleting}
          />
        )}
      </main>
    </div>
  )
}

// Type augmentation for global toast function (if not already defined)
declare global {
  interface Window {
    showToast?: (message: string, type: 'success' | 'error' | 'info') => void
  }
}
