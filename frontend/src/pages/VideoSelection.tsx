import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { VideoPlayer } from '@/components/PageComponents/VideoPlayer'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { useProjects } from '@/hooks/useProjects'
import { useCampaigns } from '@/hooks/useCampaigns'
import { useGeneration } from '@/hooks/useGeneration'
import { api } from '@/services/api'
import { ArrowLeft, CheckCircle2, Sparkles } from 'lucide-react'
import { getVideoURL } from '@/services/videoStorage'

// Get API base URL for absolute video URLs
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function VideoSelection() {
  const { projectId, campaignId } = useParams<{ projectId?: string; campaignId?: string }>()
  const navigate = useNavigate()
  const { getProject } = useProjects()
  const { getCampaign } = useCampaigns()
  const { selectVariation } = useGeneration()
  
  // Use campaignId if available, otherwise fall back to projectId (legacy)
  const id = campaignId || projectId || ''
  const isCampaign = !!campaignId

  const [project, setProject] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [selecting, setSelecting] = useState(false)
  const [videoUrls, setVideoUrls] = useState<string[]>([])
  const [campaignBlobUrls, setCampaignBlobUrls] = useState<string[]>([])

  const fetchCampaignVariationBlobs = async (
    campaignData: any,
    variationIndices: number[]
  ) => {
    if (!campaignData?.campaign_id) {
      throw new Error('Invalid campaign data')
    }
    
    if (variationIndices.length === 0) {
      throw new Error('No variations available for campaign')
    }
    
    const blobUrls: string[] = []
    try {
      for (const variationIndex of variationIndices) {
        const response = await api.get(
          `/api/generation/campaigns/${campaignData.campaign_id}/stream/9:16`,
          {
            responseType: 'blob',
            params: { variation_index: variationIndex },
          }
        )
        const blobUrl = URL.createObjectURL(response.data)
        blobUrls.push(blobUrl)
      }
      
      setCampaignBlobUrls(blobUrls)
      setVideoUrls(blobUrls)
    } catch (err) {
      blobUrls.forEach(url => URL.revokeObjectURL(url))
      throw err
    }
  }

  // Load project/campaign and videos
  useEffect(() => {
    const loadProject = async () => {
      if (!id) return

      try {
        setLoading(true)
        let data: any
        if (isCampaign) {
          data = await getCampaign(id)
        } else {
          data = await getProject(id)
        }
        setProject(data)

        // Check if project/campaign has multiple variations
        const numVariations = data.num_variations || 1

        if (numVariations === 1) {
          // Single variation - redirect to results
          if (isCampaign) {
            navigate(`/campaigns/${id}/results`)
          } else {
            navigate(`/projects/${id}/results`)
          }
          return
        }

        // Load video URLs for all variations
        let videoPaths: any = null
        
        if (isCampaign) {
          // Campaign structure: campaign_json.variationPaths
          // Backend stores as object: {"variation_0": {"aspectExports": {"9:16": "url"}}, ...}
          // Handle case where campaign_json might be a string (JSONB serialization)
          let campaignJson = data?.campaign_json || {}
          if (typeof campaignJson === 'string') {
            try {
              campaignJson = JSON.parse(campaignJson)
            } catch (e) {
              console.error('❌ Failed to parse campaign_json:', e)
              campaignJson = {}
            }
          }
          const variationPaths = campaignJson?.variationPaths || {}
          
          console.log('🔍 Campaign JSON:', campaignJson)
          console.log('🔍 Variation Paths:', variationPaths)
          console.log('🔍 Variation Paths type:', typeof variationPaths)
          console.log('🔍 Variation Paths keys:', Object.keys(variationPaths))
          
          const variationKeys = Object.keys(variationPaths || {}).sort()
          if (variationKeys.length === 0) {
            console.warn('⚠️ No variation paths found, redirecting to results')
            navigate(`/campaigns/${id}/results`)
            return
          }
          
          const variationIndices = variationKeys.map((key, idx) => {
            const parts = key.split('_')
            const parsed = parseInt(parts[parts.length - 1], 10)
            return Number.isNaN(parsed) ? idx : parsed
          })
          
          await fetchCampaignVariationBlobs(data, variationIndices)
          return
        } else {
          // Project structure: local_video_paths["9:16"] as array when num_variations > 1
        // OR in ad_project_json.local_video_paths["9:16"] 
          videoPaths = data.local_video_paths?.['9:16'] || data.ad_project_json?.local_video_paths?.['9:16']
        }

        console.log('📹 Video paths from', isCampaign ? 'campaign' : 'project', ':', videoPaths)
        console.log('📊 Number of variations:', numVariations)

        if (Array.isArray(videoPaths)) {
          // Multiple variations - videos are stored as URLs (campaigns) or file paths (projects)
          const urls: string[] = []
          for (let i = 0; i < videoPaths.length; i++) {
            const path = videoPaths[i]
            if (typeof path === 'string' && path.trim()) {
              // If path is already a URL (http/https), use it directly (campaigns)
              if (path.startsWith('http://') || path.startsWith('https://')) {
                urls.push(path)
              } else {
                // File path - use preview endpoint with variation query parameter (projects)
                // Backend endpoint: /api/local-generation/projects/{id}/preview?variation={index}
                // Use absolute URL for proper CORS and video loading
                // Add timestamp to prevent caching
                const timestamp = new Date().getTime()
                const previewUrl = `${API_BASE_URL}/api/local-generation/projects/${id}/preview?variation=${i}&t=${timestamp}`
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
            if (isCampaign) {
              navigate(`/campaigns/${id}/results`)
            } else {
              navigate(`/projects/${id}/results`)
            }
            return
          }
        } else if (videoPaths && typeof videoPaths === 'string') {
          // Single video (shouldn't happen here, but handle it)
          if (videoPaths.startsWith('http://') || videoPaths.startsWith('https://')) {
            setVideoUrls([videoPaths])
          } else {
            // File path - use preview endpoint without variation (defaults to 0)
            setVideoUrls([`${API_BASE_URL}/api/local-generation/projects/${id}/preview`])
          }
        } else {
          // Fallback: try to get from local storage (IndexedDB) - only for projects
          if (!isCampaign) {
          const urls: string[] = []
          for (let i = 0; i < numVariations; i++) {
            try {
                const url = await getVideoURL(id, '9:16')
              if (url && !urls.includes(url)) {
                urls.push(url)
              }
            } catch (err) {
              console.error(`Failed to load video ${i}:`, err)
            }
          }

          if (urls.length === 0) {
            console.warn('No videos found, redirecting to results')
              navigate(`/projects/${id}/results`)
            return
          }

          setVideoUrls(urls)
          } else {
            // Campaigns: no local storage fallback, redirect to results
            console.warn('No videos found in campaign_json, redirecting to results')
            navigate(`/campaigns/${id}/results`)
            return
          }
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : `Failed to load ${isCampaign ? 'campaign' : 'project'}`
        setError(message)
        console.error(`Error loading ${isCampaign ? 'campaign' : 'project'}:`, err)
      } finally {
        setLoading(false)
      }
    }

    loadProject()
  }, [id, isCampaign, getProject, getCampaign, navigate])

  useEffect(() => {
    return () => {
      campaignBlobUrls.forEach(url => URL.revokeObjectURL(url))
    }
  }, [campaignBlobUrls])

  const handleSelect = (index: number) => {
    setSelectedIndex(index)
  }

  const handleNext = async () => {
    if (selectedIndex === null || !id) return

    try {
      setSelecting(true)
      
      if (isCampaign) {
        // For campaigns, update selected_variation_index via generation API (auth handled by api client)
        await api.post(`/api/generation/campaigns/${id}/select-variation`, {
          variation_index: selectedIndex,
        })
      } else {
        // For projects, use the existing selectVariation hook
        await selectVariation(id, selectedIndex)
      }

      // Navigate to results page
      if (isCampaign) {
        navigate(`/campaigns/${id}/results`)
      } else {
        navigate(`/projects/${id}/results`)
      }
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
          <Button onClick={() => {
            if (isCampaign) {
              navigate(`/campaigns/${id}/results`)
            } else {
              navigate(`/projects/${id}/results`)
            }
          }}>
            Go to Results
          </Button>
        </div>
      </div>
    )
  }

  const numVariations = project?.num_variations || videoUrls.length || 1

  if (numVariations === 1 || videoUrls.length === 0) {
    // Shouldn't happen, but redirect to results
    if (isCampaign) {
      navigate(`/campaigns/${id}/results`)
    } else {
      navigate(`/projects/${id}/results`)
    }
    return null
  }

  return (
    <div className="min-h-screen bg-gradient-hero flex flex-col">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-32 -right-32 w-72 h-72 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-32 -left-32 w-72 h-72 bg-gold-silky/10 rounded-full blur-3xl"></div>
      </div>

      {/* Navigation Header */}
      <nav className="relative z-10 border-b border-charcoal-800/60 backdrop-blur-md bg-charcoal-900/70 sticky top-0">
        <div className="max-w-6xl mx-auto w-full px-4 py-4">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-charcoal-800/60 transition-colors"
            >
              <ArrowLeft className="h-5 w-5 text-muted-gray" />
              <span className="text-muted-gray">Back to Dashboard</span>
            </button>
            <div className="flex items-center gap-2">
              <div className="p-2 bg-gold rounded-lg shadow-gold">
                <Sparkles className="h-5 w-5 text-gold-foreground" />
              </div>
              <span className="text-xl font-bold text-gradient-gold">GenAds</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="relative z-10 flex-1 w-full max-w-6xl mx-auto px-4 py-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className="text-3xl font-bold text-off-white mb-2">
            Choose Your Favorite
          </h1>
          <p className="text-muted-gray">
            {numVariations} variations generated. Select the one you like best.
          </p>
        </motion.div>

        {/* Video Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mb-8 auto-rows-fr">
          {videoUrls.map((videoUrl, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card
                className={`h-full flex flex-col cursor-pointer transition-all duration-200 ${
                  selectedIndex === index
                    ? 'ring-2 ring-gold shadow-gold-lg'
                    : 'hover:ring-2 hover:ring-gold/20 hover:shadow-gold'
                }`}
                onClick={() => handleSelect(index)}
              >
                <div className="relative flex-1 flex items-center justify-center p-4">
                  <VideoPlayer
                    videoUrl={videoUrl}
                    aspect="9:16"
                    title={`Option ${index + 1}`}
                    size="compact"
                  />
                  {selectedIndex === index && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="absolute top-4 right-4 bg-gold text-gold-foreground rounded-full w-9 h-9 flex items-center justify-center shadow-gold-lg z-10"
                    >
                      <CheckCircle2 className="w-5 h-5" />
                    </motion.div>
                  )}
                </div>
                <div className="px-4 pb-4">
                  <p className="text-off-white font-semibold text-base">
                    Option {index + 1}
                  </p>
                  <p className="text-muted-gray text-sm">
                    {selectedIndex === index ? 'Selected' : 'Tap to select this version'}
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
          className="flex gap-4 justify-center flex-wrap"
        >
          <Button
            variant="outline"
            onClick={() => {
              if (isCampaign) {
                navigate(`/campaigns/${id}/results`)
              } else {
                navigate(`/projects/${id}/results`)
              }
            }}
            className="border-charcoal-700 text-muted-gray hover:text-gold hover:border-gold"
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
      </main>
    </div>
  )
}

