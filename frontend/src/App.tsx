import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import './App.css'
import { AuthInitializer } from './components/AuthInitializer'
import { ProtectedRoute } from './components/ProtectedRoute'
import LoginPage from './pages/Login'
import SignupPage from './pages/Signup'
import { Dashboard } from './pages/Dashboard'
import { Landing } from './pages/Landing'
import { CreateProject } from './pages/CreateProject'
import { GenerationProgress } from './pages/GenerationProgress'
import { VideoResults } from './pages/VideoResults'
import { BrandOnboarding } from './pages/BrandOnboarding'
import { ProductManagement } from './pages/ProductManagement'
import { CampaignCreation } from './pages/CampaignCreation'

function App() {
  return (
    <Router>
      <AuthInitializer>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/create"
            element={
              <ProtectedRoute>
                <CreateProject />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/:projectId/progress"
            element={
              <ProtectedRoute>
                <GenerationProgress />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/:projectId/results"
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
