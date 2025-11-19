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
    description: 'Get horizontal (16:9) format instantly',
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
        <h2 className="text-4xl font-bold text-gray-900 mb-4">{title}</h2>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">{subtitle}</p>
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
                variant="default"
                className="h-full hover:border-blue-300 transition-all hover:shadow-lg hover:shadow-blue-500/10"
              >
                <CardContent className="pt-8">
                  <div className="space-y-4">
                    {/* Icon */}
                    <div className="inline-flex p-3 bg-gradient-to-br from-blue-500/10 to-blue-600/10 rounded-lg">
                      <Icon className="w-6 h-6 text-blue-600" />
                    </div>

                    {/* Title & Highlight */}
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {feature.title}
                      </h3>
                      {feature.highlight && (
                        <p className="text-xs font-medium text-blue-600 mt-1">
                          {feature.highlight}
                        </p>
                      )}
                    </div>

                    {/* Description */}
                    <p className="text-gray-600 text-sm">{feature.description}</p>
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

