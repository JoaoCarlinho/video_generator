import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import './App.css'
import { AuthInitializer } from './components/AuthInitializer'
import { ProtectedRoute } from './components/ProtectedRoute'
import LoginPage from './pages/Login'
import SignupPage from './pages/Signup'
import { Dashboard } from './pages/Dashboard'
import { Landing } from './pages/Landing'
import { Onboarding } from './pages/Onboarding'
import { CampaignDashboard } from './pages/CampaignDashboard'
import { CreateCampaign } from './pages/CreateCampaign'
import { GenerationProgress } from './pages/GenerationProgress'
import { VideoResults } from './pages/VideoResults'
import { BrandOnboarding } from './pages/BrandOnboarding'
import { ProductManagement } from './pages/ProductManagement'
import { CampaignCreation } from './pages/CampaignCreation'
import { VideoSelection } from './pages/VideoSelection'
import { CreativesList } from './pages/CreativesList'
import { CreateCreative } from './pages/CreateCreative'

function App() {
  return (
    <Router>
      <AuthInitializer>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          {/* Onboarding Route (protected but skip onboarding check) */}
          <Route
            path="/onboarding"
            element={
              <ProtectedRoute skipOnboardingCheck>
                <Onboarding />
              </ProtectedRoute>
            }
          />

          {/* Protected Routes (require onboarding) */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          
          {/* Product Routes */}
          <Route
            path="/products/:productId"
            element={
              <ProtectedRoute>
                <CampaignDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/products/:productId/campaigns/create"
            element={
              <ProtectedRoute>
                <CreateCampaign />
              </ProtectedRoute>
            }
          />
          
          {/* Campaign Routes */}
          <Route
            path="/campaigns/:campaignId/creatives"
            element={
              <ProtectedRoute>
                <CreativesList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/:campaignId/creatives/create"
            element={
              <ProtectedRoute>
                <CreateCreative />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/:campaignId/creatives/:creativeId/progress"
            element={
              <ProtectedRoute>
                <GenerationProgress />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/:campaignId/creatives/:creativeId/results"
            element={
              <ProtectedRoute>
                <VideoResults />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/:campaignId/progress"
            element={
              <ProtectedRoute>
                <GenerationProgress />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/:campaignId/select"
            element={
              <ProtectedRoute>
                <VideoSelection />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/:campaignId/results"
            element={
              <ProtectedRoute>
                <VideoResults />
              </ProtectedRoute>
            }
          />
          
          {/* Legacy Routes (for backward compatibility during migration) */}
          <Route
            path="/create"
            element={
              <ProtectedRoute>
                <CreateCampaign />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/:campaignId/progress"
            element={
              <ProtectedRoute>
                <GenerationProgress />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/:campaignId/select"
            element={
              <ProtectedRoute>
                <VideoSelection />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/:campaignId/results"
            element={
              <ProtectedRoute>
                <VideoResults />
              </ProtectedRoute>
            }
          />

          {/* Brand Management Routes */}
          <Route
            path="/brands/new"
            element={
              <ProtectedRoute>
                <BrandOnboarding />
              </ProtectedRoute>
            }
          />
          <Route
            path="/brands/:brandId/products"
            element={
              <ProtectedRoute>
                <ProductManagement />
              </ProtectedRoute>
            }
          />

          {/* Campaign Management Routes */}
          <Route
            path="/brands/:brandId/products/:productId/campaigns/new"
            element={
              <ProtectedRoute>
                <CampaignCreation />
              </ProtectedRoute>
            }
          />
          <Route
            path="/brands/:brandId/campaigns/:campaignId/edit"
            element={
              <ProtectedRoute>
                <CampaignCreation />
              </ProtectedRoute>
            }
          />

          {/* Redirects */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthInitializer>
    </Router>
  )
}

export default App
