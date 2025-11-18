import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { VideoPlayer } from '@/components/PageComponents/VideoPlayer'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { useProjects } from '@/hooks/useProjects'
import { useGeneration } from '@/hooks/useGeneration'
import { ArrowLeft, CheckCircle2, Sparkles } from 'lucide-react'
import { getVideoURL } from '@/services/videoStorage'

// Get API base URL for absolute video URLs
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function VideoSelection() {
  const { projectId = '' } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { getProject } = useProjects()
  const { selectVariation } = useGeneration()

  const [project, setProject] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [selecting, setSelecting] = useState(false)
  const [videoUrls, setVideoUrls] = useState<string[]>([])

  // Load project and videos
  useEffect(() => {
    const loadProject = async () => {
      if (!projectId) return

      try {
        setLoading(true)
        const data = await getProject(projectId)
        setProject(data)

        // Check if project has multiple variations
        const numVariations = data.num_variations || 1

        if (numVariations === 1) {
          // Single variation - redirect to results
          navigate(`/projects/${projectId}/results`)
          return
        }

        // Load video URLs for all variations
        // Videos are stored in local_video_paths["9:16"] as array when num_variations > 1
        // OR in ad_project_json.local_video_paths["9:16"] 
        const videoPaths = data.local_video_paths?.['9:16'] || data.ad_project_json?.local_video_paths?.['9:16']

        console.log('📹 Video paths from project:', videoPaths)
        console.log('📊 Number of variations:', numVariations)

        if (Array.isArray(videoPaths)) {
          // Multiple variations - videos are stored as file paths
          // Convert file paths to URLs using the preview endpoint with variation query parameter
          const urls: string[] = []
          for (let i = 0; i < videoPaths.length; i++) {
            const path = videoPaths[i]
            if (typeof path === 'string' && path.trim()) {
              // If path is already a URL (http/https), use it directly
              if (path.startsWith('http://') || path.startsWith('https://')) {
                urls.push(path)
              } else {
                // File path - use preview endpoint with variation query parameter
                // Backend endpoint: /api/local-generation/projects/{id}/preview?variation={index}
                // Use absolute URL for proper CORS and video loading
                // Add timestamp to prevent caching
                const timestamp = new Date().getTime()
                const previewUrl = `${API_BASE_URL}/api/local-generation/projects/${projectId}/preview?variation=${i}&t=${timestamp}`
                urls.push(previewUrl)
                console.log(`✅ Created preview URL for variation ${i}: ${previewUrl}`)
              }
            }
          }

          if (urls.length > 0) {
            console.log(`✅ Setting ${urls.length} video URLs:`, urls)
            setVideoUrls(urls)
          } else {
            console.warn('⚠️ No valid video paths found in array')
            navigate(`/projects/${projectId}/results`)
            return
          }
        } else if (videoPaths && typeof videoPaths === 'string') {
          // Single video (shouldn't happen here, but handle it)
          if (videoPaths.startsWith('http://') || videoPaths.startsWith('https://')) {
            setVideoUrls([videoPaths])
          } else {
            // File path - use preview endpoint without variation (defaults to 0)
            setVideoUrls([`${API_BASE_URL}/api/local-generation/projects/${projectId}/preview`])
          }
        } else {
          // Fallback: try to get from local storage (IndexedDB)
          const urls: string[] = []
          for (let i = 0; i < numVariations; i++) {
            try {
              const url = await getVideoURL(projectId, '9:16')
              if (url && !urls.includes(url)) {
                urls.push(url)
              }
            } catch (err) {
              console.error(`Failed to load video ${i}:`, err)
            }
          }

          if (urls.length === 0) {
            console.warn('No videos found, redirecting to results')
            navigate(`/projects/${projectId}/results`)
            return
          }

          setVideoUrls(urls)
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load project'
        setError(message)
        console.error('Error loading project:', err)
      } finally {
        setLoading(false)
      }
    }

    loadProject()
  }, [projectId, getProject, navigate])

  const handleSelect = (index: number) => {
    setSelectedIndex(index)
  }

  const handleNext = async () => {
    if (selectedIndex === null || !projectId) return

    try {
      setSelecting(true)
      await selectVariation(projectId, selectedIndex)

      // Navigate to results page
      navigate(`/projects/${projectId}/results`)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to select variation'
      setError(message)
      console.error('Error selecting variation:', err)
    } finally {
      setSelecting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-hero flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-3 border-olive-600 border-t-gold rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-gray">Loading videos...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-hero flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <Button onClick={() => navigate(`/projects/${projectId}/results`)}>
            Go to Results
          </Button>
        </div>
      </div>
    )
  }

  const numVariations = project?.num_variations || videoUrls.length || 1

  if (numVariations === 1 || videoUrls.length === 0) {
    // Shouldn't happen, but redirect to results
    navigate(`/projects/${projectId}/results`)
    return null
  }

  return (
    <div className="min-h-screen bg-gradient-hero">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gold-silky/10 rounded-full blur-3xl"></div>
      </div>

      {/* Navigation Header */}
      <nav className="relative z-10 border-b border-olive-600/50 backdrop-blur-md bg-olive-950/50 sticky top-0">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate(`/projects/${projectId}/results`)}
                className="p-2 hover:bg-olive-800/50 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-muted-gray hover:text-gold" />
              </button>
              <div className="flex items-center gap-2">
                <div className="p-2 bg-gold rounded-lg shadow-gold">
                  <Sparkles className="h-5 w-5 text-gold-foreground" />
                </div>
                <span className="text-xl font-bold text-gradient-gold">GenAds</span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 max-w-7xl">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-12 text-center"
          >
            <h1 className="text-4xl font-bold text-white mb-2">
              Choose Your Favorite
            </h1>
            <p className="text-muted-gray">
              {numVariations} variations generated. Select the one you like best.
            </p>
          </motion.div>

          {/* Video Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {videoUrls.map((videoUrl, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card
                  className={`cursor-pointer transition-all duration-200 ${selectedIndex === index
                      ? 'ring-2 ring-gold shadow-gold-lg'
                      : 'hover:ring-2 hover:ring-accent-neutral hover:shadow-lg'
                    }`}
                  onClick={() => handleSelect(index)}
                >
                  <div className="relative aspect-[9/16] bg-black rounded-lg overflow-hidden mb-4">
                    {/* Video Preview */}
                    <VideoPlayer
                      videoUrl={videoUrl}
                      aspect="9:16"
                      title={`Option ${index + 1}`}
                    />

                    {/* Selection Indicator */}
                    {selectedIndex === index && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="absolute top-3 right-3 bg-gold text-gold-foreground rounded-full w-10 h-10 flex items-center justify-center shadow-gold-lg z-10"
                      >
                        <CheckCircle2 className="w-6 h-6" />
                      </motion.div>
                    )}
                  </div>

                  {/* Option Label */}
                  <div className="p-4 pt-0">
                    <p className="text-white font-semibold text-lg mb-1">
                      Option {index + 1}
                    </p>
                    <p className="text-muted-gray text-sm">
                      {selectedIndex === index ? 'Selected' : 'Click to select this version'}
                    </p>
                  </div>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* Action Buttons */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="flex gap-4 justify-center"
          >
            <Button
              variant="outline"
              onClick={() => navigate(`/projects/${projectId}/results`)}
              className="border-olive-600 text-muted-gray hover:text-gold hover:border-gold"
            >
              Cancel
            </Button>
            <Button
              variant="default"
              disabled={selectedIndex === null || selecting}
              onClick={handleNext}
              className="bg-gold text-gold-foreground hover:bg-accent-gold-dark disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {selecting ? 'Selecting...' : 'Next: Review Selected Video'}
            </Button>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

