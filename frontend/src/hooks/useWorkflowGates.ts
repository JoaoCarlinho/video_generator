/**
 * useWorkflowGates - Hook for enforcing workflow prerequisites
 *
 * Workflow gates ensure users complete required steps before proceeding:
 * - Users must create a brand before creating products
 * - Users must have products before creating campaigns (future)
 */

import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAppSelector } from '../store/hooks'
import { brandsSelectors } from '../store/slices/brandsSlice'
import { useGetBrandsQuery } from '../store/api'

interface WorkflowGatesOptions {
  requireBrand?: boolean
  requireProduct?: boolean
}

export const useWorkflowGates = (options: WorkflowGatesOptions = {}) => {
  const navigate = useNavigate()
  const location = useLocation()

  const { requireBrand = false, requireProduct = false } = options

  // Fetch brands
  const { data: brands, isLoading: brandsLoading } = useGetBrandsQuery()
  const allBrands = useAppSelector(brandsSelectors.selectAll)

  // Check if user has completed brand onboarding
  const hasBrand = (brands && brands.length > 0) || allBrands.length > 0

  useEffect(() => {
    // Skip if still loading
    if (brandsLoading) return

    // Skip if we're already on the brand creation page
    if (location.pathname === '/brands/new') return

    // Enforce brand requirement
    if (requireBrand && !hasBrand) {
      console.log('Workflow gate: Redirecting to brand onboarding (no brand found)')
      navigate('/brands/new', {
        state: { from: location.pathname },
        replace: true,
      })
    }

    // TODO: Enforce product requirement (Epic 2+)
    if (requireProduct) {
      // Future: Check if user has products
      // If not, redirect to product creation
    }
  }, [hasBrand, brandsLoading, requireBrand, requireProduct, navigate, location.pathname])

  return {
    hasBrand,
    isLoading: brandsLoading,
    canCreateProducts: hasBrand,
    canCreateCampaigns: hasBrand, // Future: && hasProducts
  }
}
