import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import { ProductCard } from '@/components/ProductCard'
import { useAuth } from '@/hooks/useAuth'
import { useBrand } from '@/hooks/useBrand'
import { useProducts } from '@/hooks/useProducts'
import { Plus, TrendingUp, Sparkles, LogOut, User, Package } from 'lucide-react'
import { Link } from 'react-router-dom'

export const Dashboard = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const { brand, stats } = useBrand()
  const { products, loading, error, fetchProducts, deleteProduct } = useProducts()

  useEffect(() => {
    fetchProducts()
  }, [fetchProducts])

  const handleAddProduct = () => {
    navigate('/products/add')
  }

  const handleViewPerfume = (productId: string) => {
    navigate(`/products/${productId}`)
  }

  const handleDeletePerfume = async (productId: string) => {
    if (
      confirm(
        'Are you sure you want to delete this product? All campaigns for this perfume will also be deleted. This cannot be undone.'
      )
    ) {
      try {
        await deletePerfume(perfumeId)
      } catch (err) {
        console.error('Failed to delete perfume:', err)
      }
    }
  }

  const dashboardStats = [
    {
      label: 'Total Products',
      value: perfumes.length,
      icon: Package,
      gradient: 'from-gold/20 to-gold-silky/10',
      iconBg: 'bg-gold/20',
    },
    {
      label: 'Total Campaigns',
      value: stats?.total_campaigns || 0,
      icon: TrendingUp,
      gradient: 'from-gold-silky/20 to-gold/10',
      iconBg: 'bg-gold-silky/20',
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
    <div className="min-h-screen bg-gradient-to-b from-gray-50 via-white to-gray-50 flex flex-col">
      {/* Header */}
      <Header
        logo="GenAds"
        title="Dashboard"
        actions={
          <button
            onClick={() => logout()}
            className="text-gray-600 hover:text-gray-900 text-sm transition-colors"
          >
            Sign Out
          </button>
        }
      />
    <div className="min-h-screen bg-gradient-hero">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gold-silky/10 rounded-full blur-3xl"></div>
        <div className="absolute inset-0 bg-gradient-to-br from-gold/5 via-transparent to-transparent" />
      </div>

      {/* Navigation Header */}
      <nav className="relative z-50 border-b border-olive-600/50 backdrop-blur-md bg-olive-950/30 sticky top-0">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link to="/" className="flex items-center gap-2">
                <div className="p-2 bg-gold rounded-lg shadow-gold">
                  <Sparkles className="h-5 w-5 text-gold-foreground" />
                </div>
                <span className="text-xl font-bold text-gradient-gold">GenAds</span>
              </Link>
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
                Your Products
              </h1>
              <p className="text-lg sm:text-xl text-muted-gray max-w-2xl">
                {brand?.brand_name ? (
                  <>Manage your perfume collection for <span className="text-gold font-semibold">{brand.brand_name}</span></>
                ) : (
                  'Create, manage, and track your perfume collection'
                )}
              </p>
            </motion.div>

            {/* Stats Grid */}
            <motion.div
              variants={itemVariants}
              className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6"
            >
              {dashboardStats.map((stat, index) => {
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

            {/* Perfumes Section */}
            <motion.div variants={itemVariants} className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">My Projects</h2>
                  <p className="text-gray-600 text-sm mt-1">
                    {products.length} project{products.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <Button
                  variant="hero"
                  onClick={handleAddProduct}
                  className="gap-2 transition-transform duration-200 hover:scale-105"
                >
                  <Plus className="w-5 h-5" />
                  Add Product
                </Button>
              </div>

              {/* Products Grid */}
              {loading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="aspect-square bg-olive-800/30 rounded-xl border border-olive-600 animate-pulse" />
                  ))}
                </div>
              ) : error ? (
                <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-center">
                  <p className="text-red-600 font-medium">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchProducts()}
                    className="gap-2"
                  >
                    Try Again
                  </Button>
                </div>
              ) : perfumes.length === 0 ? (
                <motion.div 
                  className="text-center py-20 px-4"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                >
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-gold/10 rounded-full mb-6">
                    <Package className="w-10 h-10 text-gold" />
                  </div>
                  <h3 className="text-2xl font-bold text-off-white mb-3">
                    No perfumes yet
                  </h3>
                  <p className="text-muted-gray mb-8 max-w-md mx-auto">
                    Add your first perfume to start creating ad campaigns
                  </p>
                  <Button
                    variant="hero"
                    onClick={handleAddProduct}
                    className="gap-2 transition-transform duration-200 hover:scale-105"
                  >
                    <Plus className="w-5 h-5" />
                    Add Your First Perfume
                  </Button>
                </motion.div>
              ) : (
                <motion.div
                  className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                >
                  {perfumes.map((perfume) => (
                    <motion.div key={perfume.perfume_id} variants={itemVariants}>
                      <PerfumeCard
                        perfume={perfume}
                        onClick={() => handleViewPerfume(perfume.perfume_id)}
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
