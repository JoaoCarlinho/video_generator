import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import './App.css'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import LoginPage from './pages/Login'
import SignupPage from './pages/Signup'
import { Dashboard } from './pages/Dashboard'
import { Landing } from './pages/Landing'
import { CreateProject } from './pages/CreateProject'
import { GenerationProgress } from './pages/GenerationProgress'
import { VideoResults } from './pages/VideoResults'

function App() {
  return (
    <Router>
      <AuthProvider>
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

          {/* Redirects */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  )
}

export default App
