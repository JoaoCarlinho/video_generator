import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Container, Header } from '@/components/layout'
import { Button, Skeleton } from '@/components/ui'
import { ProjectCard } from '@/components/PageComponents'
import { useAuth } from '@/hooks/useAuth'
import { useProjects } from '@/hooks/useProjects'
import { Plus, TrendingUp, Video, Zap } from 'lucide-react'

export const Dashboard = () => {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { projects, loading, error, fetchProjects, deleteProject } = useProjects()

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const handleCreateProject = () => {
    navigate('/create')
  }

  const handleViewProject = (projectId: string) => {
    console.log('handleViewProject called with:', projectId)
    const project = projects.find((p) => p.id === projectId)
    console.log('Project found:', project)
    const isReady = project?.status === 'ready' || project?.status === 'COMPLETED'
    if (isReady) {
      console.log('Navigating to results page')
      navigate(`/projects/${projectId}/results`)
    } else {
      console.log('Navigating to progress page, status:', project?.status)
      navigate(`/projects/${projectId}/progress`)
    }
  }

  const handleDeleteProject = async (projectId: string) => {
    if (
      confirm(
        'Are you sure you want to delete this project? This cannot be undone.'
      )
    ) {
      try {
        await deleteProject(projectId)
      } catch (err) {
        console.error('Failed to delete project:', err)
      }
    }
  }

  const stats = [
    {
      label: 'Total Projects',
      value: projects.length,
      icon: Video,
      color: 'indigo',
    },
    {
      label: 'Generating',
      value: projects.filter((p) => p.status === 'generating').length,
      icon: Zap,
      color: 'purple',
    },
    {
      label: 'Ready',
      value: projects.filter((p) => p.status === 'ready').length,
      icon: TrendingUp,
      color: 'emerald',
    },
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 flex flex-col">
      {/* Header */}
      <Header
        logo="GenAds"
        title="Dashboard"
        actions={
          <button
            onClick={() => logout()}
            className="text-slate-400 hover:text-slate-200 text-sm transition-colors"
          >
            Sign Out
          </button>
        }
      />

      {/* Main Content */}
      <div className="flex-1">
        <Container size="lg" className="py-12">
          <motion.div
            className="space-y-12"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {/* Welcome Section */}
            <motion.div variants={itemVariants} className="space-y-2">
              <h1 className="text-4xl font-bold text-slate-100">
                Welcome back, {user?.email?.split('@')[0]}!
              </h1>
              <p className="text-lg text-slate-400">
                Create, manage, and track your AI-generated video projects
              </p>
            </motion.div>

            {/* Stats Grid */}
            <motion.div
              variants={itemVariants}
              className="grid grid-cols-1 md:grid-cols-3 gap-6"
            >
              {stats.map((stat, index) => {
                const Icon = stat.icon
                const colorClasses = {
                  indigo: 'bg-indigo-500/20 border-indigo-500/50 text-indigo-400',
                  purple: 'bg-purple-500/20 border-purple-500/50 text-purple-400',
                  emerald: 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400',
                }
                const bgClass = colorClasses[stat.color as keyof typeof colorClasses]

                return (
                  <motion.div
                    key={stat.label}
                    className={`p-6 rounded-lg border ${bgClass} backdrop-blur-sm`}
                    whileHover={{ y: -4 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-slate-800/50 rounded-lg">
                        <Icon className="w-6 h-6" />
                      </div>
                      <div>
                        <p className="text-slate-400 text-sm">{stat.label}</p>
                        <p className="text-3xl font-bold text-slate-100">
                          {stat.value}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </motion.div>

            {/* Projects Section */}
            <motion.div variants={itemVariants} className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-slate-100">My Projects</h2>
                  <p className="text-slate-400 text-sm mt-1">
                    {projects.length} project{projects.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <Button
                  variant="gradient"
                  onClick={handleCreateProject}
                  className="gap-2"
                >
                  <Plus className="w-5 h-5" />
                  New Project
                </Button>
              </div>

              {/* Projects Grid */}
              {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-64" />
                  ))}
                </div>
              ) : error ? (
                <div className="p-6 bg-red-500/10 border border-red-500/50 rounded-lg text-center">
                  <p className="text-red-400 font-medium">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchProjects()}
                    className="mt-4"
                  >
                    Try Again
                  </Button>
                </div>
              ) : projects.length === 0 ? (
                <div className="text-center py-16">
                  <div className="text-6xl mb-4">🎬</div>
                  <h3 className="text-xl font-semibold text-slate-100 mb-2">
                    No projects yet
                  </h3>
                  <p className="text-slate-400 mb-6">
                    Create your first project to generate amazing video ads
                  </p>
                  <Button
                    variant="gradient"
                    onClick={handleCreateProject}
                    className="gap-2"
                  >
                    <Plus className="w-5 h-5" />
                    Create Project
                  </Button>
                </div>
              ) : (
                <motion.div
                  className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                >
                  {projects.map((project) => (
                    <motion.div key={project.id} variants={itemVariants}>
                      <ProjectCard
                        title={project.title}
                        brief={project.brief}
                        status={project.status}
                        progress={project.status === 'generating' ? 50 : 100}
                        createdAt={project.created_at}
                        costEstimate={project.cost_estimate}
                        onView={() => handleViewProject(project.id)}
                        onDelete={() => handleDeleteProject(project.id)}
                      />
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </motion.div>
          </motion.div>
        </Container>
      </div>
    </div>
  )
}
