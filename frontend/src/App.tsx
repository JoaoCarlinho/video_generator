import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import './App.css'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import LoginPage from './pages/Login'
import SignupPage from './pages/Signup'
import { Dashboard } from './pages/Dashboard'
import { Landing } from './pages/Landing'
import { Onboarding } from './pages/Onboarding'
import { CreateProject } from './pages/CreateProject'
import { GenerationProgress } from './pages/GenerationProgress'
import { VideoResults } from './pages/VideoResults'
import { VideoSelection } from './pages/VideoSelection'

function App() {
  return (
    <Router>
      <AuthProvider>
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
          
          {/* Perfume Routes */}
          <Route
            path="/perfumes/add"
            element={
              <ProtectedRoute>
                <div className="min-h-screen flex items-center justify-center bg-slate-900">
                  <div className="text-center">
                    <h1 className="text-2xl font-bold text-white mb-4">Add Perfume Page</h1>
                    <p className="text-gray-400">Coming soon...</p>
                  </div>
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/perfumes/:perfumeId"
            element={
              <ProtectedRoute>
                <div className="min-h-screen flex items-center justify-center bg-slate-900">
                  <div className="text-center">
                    <h1 className="text-2xl font-bold text-white mb-4">Campaign Dashboard</h1>
                    <p className="text-gray-400">Coming soon...</p>
                  </div>
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/perfumes/:perfumeId/campaigns/create"
            element={
              <ProtectedRoute>
                <div className="min-h-screen flex items-center justify-center bg-slate-900">
                  <div className="text-center">
                    <h1 className="text-2xl font-bold text-white mb-4">Create Campaign</h1>
                    <p className="text-gray-400">Coming soon...</p>
                  </div>
                </div>
              </ProtectedRoute>
            }
          />
          
          {/* Campaign Routes */}
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
            path="/projects/:projectId/select"
            element={
              <ProtectedRoute>
                <VideoSelection />
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

          {/* Redirects */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  )
}

export default App
