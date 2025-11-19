/**
 * ProductList - Displays product cards with edit and delete actions
 */

import { useState } from 'react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Trash2, Edit2, Package } from 'lucide-react'
import { Modal } from '../ui/Modal'

export interface Product {
  id: string
  brand_id: string
  product_type?: string
  name: string
  icp_segment: string
  image_urls?: string[]
  created_at: string
  updated_at: string
}

export interface ProductListProps {
  products: Product[]
  onEdit: (product: Product) => void
  onDelete: (productId: string) => Promise<void>
  isDeleting?: boolean
}

export const ProductList = ({ products, onEdit, onDelete, isDeleting = false }: ProductListProps) => {
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  const handleDeleteClick = (productId: string) => {
    setDeleteConfirmId(productId)
  }

  const handleConfirmDelete = async () => {
    if (deleteConfirmId) {
      await onDelete(deleteConfirmId)
      setDeleteConfirmId(null)
    }
  }

  const handleCancelDelete = () => {
    setDeleteConfirmId(null)
  }

  if (products.length === 0) {
    return (
      <Card className="p-12 text-center">
        <Package className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No products yet</h3>
        <p className="text-gray-500">Create your first product to get started</p>
      </Card>
    )
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map((product) => (
          <Card key={product.id} className="p-6 hover:shadow-lg transition-shadow">
            {/* Product Image Preview */}
            {product.image_urls && product.image_urls.length > 0 && (
              <div className="mb-4 aspect-video bg-gray-100 rounded-lg overflow-hidden">
                <img
                  src={product.image_urls[0]}
                  alt={product.name}
                  className="w-full h-full object-cover"
                />
              </div>
            )}

            {/* Product Info */}
            <div className="space-y-2 mb-4">
              {product.product_type && (
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  {product.product_type}
                </p>
              )}
              <h3 className="text-lg font-semibold text-gray-900">{product.name}</h3>
              <p className="text-sm text-gray-600 line-clamp-2">{product.icp_segment}</p>
              {product.image_urls && product.image_urls.length > 1 && (
                <p className="text-xs text-gray-500">
                  +{product.image_urls.length - 1} more image{product.image_urls.length > 2 ? 's' : ''}
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEdit(product)}
                className="flex-1"
              >
                <Edit2 className="w-4 h-4 mr-1" />
                Edit
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDeleteClick(product.id)}
                className="text-error-600 hover:text-error-700 hover:bg-error-50"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <Modal
          isOpen={!!deleteConfirmId}
          onClose={handleCancelDelete}
          title="Delete Product"
        >
          <div className="space-y-4">
            <p className="text-gray-600">
              Are you sure you want to delete this product? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={handleCancelDelete} disabled={isDeleting}>
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Delete Product'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}
