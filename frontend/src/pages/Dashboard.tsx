import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { ProjectCard } from '@/components/PageComponents'
import { useAuth } from '@/hooks/useAuth'
import { useProjects } from '@/hooks/useProjects'
import { Plus, TrendingUp, Video, Zap, Sparkles, LogOut, User } from 'lucide-react'
import { Link } from 'react-router-dom'

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
    const project = projects.find((p) => p.id === projectId)
    const isReady = project?.status === 'ready' || project?.status === 'COMPLETED'
    if (isReady) {
      navigate(`/projects/${projectId}/results`)
    } else {
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
      gradient: 'from-gold/20 to-gold-silky/10',
      iconBg: 'bg-gold/20',
    },
    {
      label: 'In Progress',
      value: projects.filter((p) => p.status === 'generating').length,
      icon: Zap,
      gradient: 'from-gold-silky/20 to-gold/10',
      iconBg: 'bg-gold-silky/20',
    },
    {
      label: 'Completed',
      value: projects.filter((p) => p.status === 'ready' || p.status === 'COMPLETED').length,
      icon: TrendingUp,
      gradient: 'from-gold/20 to-gold-silky/20',
      iconBg: 'bg-gold/20',
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
    <div className="min-h-screen bg-gradient-hero">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gold-silky/10 rounded-full blur-3xl"></div>
        <div className="absolute inset-0 bg-gradient-to-br from-gold/5 via-transparent to-transparent" />
      </div>

      {/* Navigation Header */}
      <nav className="relative z-10 border-b border-olive-600/50 backdrop-blur-md bg-olive-950/50 sticky top-0">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link to="/" className="flex items-center gap-2">
                <div className="p-2 bg-gold rounded-lg shadow-gold">
                  <Sparkles className="h-5 w-5 text-gold-foreground" />
                </div>
                <span className="text-xl font-bold text-gradient-gold">GenAds</span>
              </Link>
              <div className="hidden md:block ml-6 pl-6 border-l border-olive-600/50">
                <h1 className="text-sm font-semibold text-off-white">Dashboard</h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 text-sm text-muted-gray">
                <User className="w-4 h-4" />
                <span>{user?.email?.split('@')[0]}</span>
              </div>
              <button
                onClick={() => logout()}
                className="flex items-center gap-2 px-4 py-2 text-sm text-muted-gray hover:text-gold transition-colors rounded-lg hover:bg-olive-800/50"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
          <motion.div
            className="space-y-8 sm:space-y-12"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {/* Welcome Section */}
            <motion.div variants={itemVariants} className="space-y-3">
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-off-white">
                Welcome back,{' '}
                <span className="text-gradient-gold">{user?.email?.split('@')[0]}</span>
              </h1>
              <p className="text-lg sm:text-xl text-muted-gray max-w-2xl">
                Create, manage, and track your AI-generated video projects
              </p>
            </motion.div>

            {/* Stats Grid */}
            <motion.div
              variants={itemVariants}
              className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6"
            >
              {stats.map((stat, index) => {
                const Icon = stat.icon
                return (
                  <motion.div
                    key={stat.label}
                    className={`relative overflow-hidden bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-xl p-6 hover:border-gold/50 transition-all duration-300 hover:shadow-gold group`}
                    whileHover={{ y: -4, scale: 1.02 }}
                    transition={{ duration: 0.2 }}
                  >
                    {/* Gradient overlay */}
                    <div className={`absolute inset-0 bg-gradient-to-br ${stat.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`} />
                    
                    <div className="relative flex items-center gap-4">
                      <div className={`p-3 ${stat.iconBg} rounded-lg border border-gold/20 group-hover:border-gold/50 transition-colors`}>
                        <Icon className="w-6 h-6 text-gold" />
                      </div>
                      <div className="flex-1">
                        <p className="text-muted-gray text-sm font-medium mb-1">{stat.label}</p>
                        <p className="text-3xl font-bold text-off-white">
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
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-2xl sm:text-3xl font-bold text-off-white mb-2">My Projects</h2>
                  <p className="text-muted-gray text-sm">
                    {projects.length} project{projects.length !== 1 ? 's' : ''} total
                  </p>
                </div>
                <Button
                  variant="hero"
                  onClick={handleCreateProject}
                  className="gap-2 transition-transform duration-200 hover:scale-105"
                >
                  <Plus className="w-5 h-5" />
                  New Project
                </Button>
              </div>

              {/* Projects Grid */}
              {loading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="aspect-square bg-olive-800/30 rounded-xl border border-olive-600 animate-pulse" />
                  ))}
                </div>
              ) : error ? (
                <div className="p-8 bg-red-500/10 border border-red-500/30 rounded-xl text-center backdrop-blur-sm">
                  <p className="text-red-400 font-medium mb-4">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchProjects()}
                    className="gap-2"
                  >
                    Try Again
                  </Button>
                </div>
              ) : projects.length === 0 ? (
                <motion.div 
                  className="text-center py-20 px-4"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                >
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-gold/10 rounded-full mb-6">
                    <Video className="w-10 h-10 text-gold" />
                  </div>
                  <h3 className="text-2xl font-bold text-off-white mb-3">
                    No projects yet
                  </h3>
                  <p className="text-muted-gray mb-8 max-w-md mx-auto">
                    Create your first project to generate amazing video ads with AI
                  </p>
                  <Button
                    variant="hero"
                    onClick={handleCreateProject}
                    className="gap-2 transition-transform duration-200 hover:scale-105"
                  >
                    <Plus className="w-5 h-5" />
                    Create Your First Project
                  </Button>
                </motion.div>
              ) : (
                <motion.div
                  className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                >
                  {projects.map((project) => (
                    <motion.div key={project.id} variants={itemVariants} className="aspect-square">
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
        </div>
      </div>
    </div>
  )
}
