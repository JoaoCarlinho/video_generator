import { motion } from 'framer-motion'
import { Card, CardContent } from '@/components/ui/Card'
import {
  Zap,
  Palette,
  Video,
  Sparkles,
  Clock,
  DollarSign,
  type LucideIcon,
} from 'lucide-react'

interface Feature {
  icon: LucideIcon
  title: string
  description: string
  highlight?: string
}

const defaultFeatures: Feature[] = [
  {
    icon: Zap,
    title: 'Lightning Fast',
    description: 'Generate professional ads in minutes, not hours',
    highlight: 'AI-Powered',
  },
  {
    icon: Palette,
    title: 'Perfect Consistency',
    description: 'Your product looks identical across all scenes',
    highlight: 'Product-First',
  },
  {
    icon: Video,
    title: 'Multi-Aspect Export',
    description: 'Get vertical (9:16), square (1:1), and horizontal (16:9) formats',
    highlight: 'All Platforms',
  },
  {
    icon: Sparkles,
    title: 'Professional Quality',
    description: 'Cinema-grade videos with consistent styling',
    highlight: 'Studio Quality',
  },
  {
    icon: Clock,
    title: 'Real-Time Progress',
    description: 'Watch your video generate step-by-step',
    highlight: 'Live Tracking',
  },
  {
    icon: DollarSign,
    title: 'Transparent Pricing',
    description: 'Know exactly what you\'re paying for',
    highlight: 'No Surprises',
  },
]

interface FeaturesSectionProps {
  features?: Feature[]
  title?: string
  subtitle?: string
}

export const FeaturesSection = ({
  features = defaultFeatures,
  title = 'Why Choose GenAds',
  subtitle = 'Everything you need to create stunning video ads',
}: FeaturesSectionProps) => {
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
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6 },
    },
  }

  return (
    <section className="py-20">
      {/* Header */}
      <motion.div className="text-center mb-16" variants={itemVariants}>
        <h2 className="text-4xl font-bold text-slate-100 mb-4">{title}</h2>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">{subtitle}</p>
      </motion.div>

      {/* Features Grid */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-100px' }}
      >
        {features.map((feature, index) => {
          const Icon = feature.icon
          return (
            <motion.div key={index} variants={itemVariants}>
              <Card
                variant="glass"
                className="h-full hover:border-indigo-500/50 transition-all hover:shadow-lg hover:shadow-indigo-500/20"
              >
                <CardContent className="pt-8">
                  <div className="space-y-4">
                    {/* Icon */}
                    <div className="inline-flex p-3 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-lg">
                      <Icon className="w-6 h-6 text-indigo-400" />
                    </div>

                    {/* Title & Highlight */}
                    <div>
                      <h3 className="text-lg font-semibold text-slate-100">
                        {feature.title}
                      </h3>
                      {feature.highlight && (
                        <p className="text-xs font-medium text-indigo-400 mt-1">
                          {feature.highlight}
                        </p>
                      )}
                    </div>

                    {/* Description */}
                    <p className="text-slate-400 text-sm">{feature.description}</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </motion.div>
    </section>
  )
}

