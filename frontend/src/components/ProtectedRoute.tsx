/**
 * Protected Route: Guards routes that require authentication
 * Redirects to login if user is not authenticated
 * Redirects to onboarding if onboarding not completed (unless skipOnboardingCheck is true)
 */

import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useBrand } from '../hooks/useBrand'

interface ProtectedRouteProps {
  children: React.ReactNode
  skipOnboardingCheck?: boolean
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  skipOnboardingCheck = false 
}) => {
  const { isAuthenticated, isLoading } = useAuth()
  // Always call hook (Rules of Hooks), but hook will skip fetching on onboarding page
  const { brand, loading: brandLoading } = useBrand()

  // Show loading state while checking auth
  if (isLoading || brandLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-charcoal-950">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-charcoal-800 border-t-gold rounded-full animate-spin"></div>
          <p className="text-muted-gray">Loading...</p>
        </div>
      </div>
    )
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Redirect to onboarding if not completed (unless skipOnboardingCheck is true)
  if (!skipOnboardingCheck && (!brand || !brand.onboarding_completed)) {
    return <Navigate to="/onboarding" replace />
  }

  // Render protected component
  return <>{children}</>
}

export default ProtectedRoute

