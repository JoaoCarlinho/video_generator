import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import './App.css'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
        <Routes>
          <Route path="/" element={<div className="p-8 text-center"><h1 className="text-4xl font-bold text-white">AI Ad Video Generator</h1><p className="mt-4 text-gray-300">Phase 0: Infrastructure Setup Complete</p></div>} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
