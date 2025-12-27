/**
 * CampaignMetadataSection Component
 * Form section for campaign name, seasonal event, year, and product selection
 */

import React from 'react'
import { TypeAheadDropdown } from '../ui/TypeAheadDropdown'
import { useGetProductsQuery } from '../../store/api'

interface CampaignMetadataSectionProps {
  brandId: string
  productId: string
  campaignName: string
  seasonalEvent: string
  year: number
  onProductIdChange: (productId: string) => void
  onCampaignNameChange: (name: string) => void
  onSeasonalEventChange: (event: string) => void
  onYearChange: (year: number) => void
  errors?: {
    productId?: string
    name?: string
    seasonal_event?: string
    year?: string
  }
}

// Predefined seasonal events list
const SEASONAL_EVENTS = [
  'New Year Sale',
  'Valentine\'s Day',
  'Spring Collection',
  'Easter Sale',
  'Mother\'s Day',
  'Memorial Day Sale',
  'Summer Launch',
  'Father\'s Day',
  'Independence Day Sale',
  'Back to School',
  'Labor Day Sale',
  'Fall Collection',
  'Halloween Special',
  'Black Friday',
  'Cyber Monday',
  'Holiday Season',
  'Christmas Sale',
  'Year End Clearance',
  'Product Launch',
  'Brand Anniversary',
  'Flash Sale',
  'Exclusive Drop',
]

// Generate year options (current year - 2 to current year + 5)
const YEAR_OPTIONS = Array.from(
  { length: 8 },
  (_, i) => (new Date().getFullYear() - 2 + i).toString()
)

export function CampaignMetadataSection({
  brandId,
  productId,
  campaignName,
  seasonalEvent,
  year,
  onProductIdChange,
  onCampaignNameChange,
  onSeasonalEventChange,
  onYearChange,
  errors = {},
}: CampaignMetadataSectionProps) {
  const { data: products, isLoading: isLoadingProducts } = useGetProductsQuery(brandId)

  // Generate display name preview
  const displayName = campaignName && seasonalEvent && year
    ? `${campaignName}-${seasonalEvent}-${year}`
    : ''

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Campaign Details</h2>
        <p className="text-sm text-gray-600">
          Configure your campaign metadata and select the product for this campaign.
        </p>
      </div>

      {/* Product Selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Product
          <span className="text-red-500 ml-1">*</span>
        </label>
        {isLoadingProducts ? (
          <div className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-500">
            Loading products...
          </div>
        ) : (
          <select
            value={productId}
            onChange={(e) => onProductIdChange(e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-purple-500 ${
              errors.productId ? 'border-red-500' : 'border-gray-300'
            }`}
          >
            <option value="">Select a product</option>
            {products?.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
        )}
        {errors.productId && (
          <p className="mt-1 text-sm text-red-600">{errors.productId}</p>
        )}
      </div>

      {/* Campaign Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Campaign Name
          <span className="text-red-500 ml-1">*</span>
        </label>
        <input
          type="text"
          value={campaignName}
          onChange={(e) => onCampaignNameChange(e.target.value)}
          placeholder="e.g., Spring Launch, Q4 Promo"
          maxLength={100}
          className={`w-full px-3 py-2 border rounded-lg text-gray-900 bg-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 ${
            errors.name ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
      </div>

      {/* Seasonal Event */}
      <TypeAheadDropdown
        options={SEASONAL_EVENTS}
        value={seasonalEvent}
        onChange={onSeasonalEventChange}
        placeholder="Select or type seasonal event"
        label="Seasonal Event / Marketing Initiative"
        allowCustom={true}
        error={errors.seasonal_event}
        required={true}
      />

      {/* Year */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Year
          <span className="text-red-500 ml-1">*</span>
        </label>
        <select
          value={year}
          onChange={(e) => onYearChange(parseInt(e.target.value))}
          className={`w-full px-3 py-2 border rounded-lg text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-purple-500 ${
            errors.year ? 'border-red-500' : 'border-gray-300'
          }`}
        >
          <option value="">Select year</option>
          {YEAR_OPTIONS.map((yearOption) => (
            <option key={yearOption} value={yearOption}>
              {yearOption}
            </option>
          ))}
        </select>
        {errors.year && <p className="mt-1 text-sm text-red-600">{errors.year}</p>}
      </div>

      {/* Display Name Preview */}
      {displayName && (
        <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
          <p className="text-sm font-medium text-gray-700 mb-1">Campaign Display Name:</p>
          <p className="text-lg font-semibold text-purple-900">{displayName}</p>
        </div>
      )}
    </div>
  )
}
