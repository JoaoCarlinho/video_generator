import { useNavigate } from 'react-router-dom'
import { Container, Header } from '@/components/layout'
import { Button } from '@/components/ui/Button'
import {
  HeroSection,
  FeaturesSection,
  Footer,
} from '@/components/PageComponents'
import { motion } from 'framer-motion'
import { Play } from 'lucide-react'

export const Landing = () => {
  const navigate = useNavigate()

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 flex flex-col">
      {/* Header */}
      <Header
        logo="GenAds"
        actions={
          <div className="flex gap-3">
            <Button variant="ghost" onClick={() => navigate('/login')}>
              Sign In
            </Button>
            <Button variant="gradient" onClick={() => navigate('/signup')}>
              Get Started
            </Button>
          </div>
        }
      />

      {/* Main Content */}
      <div className="flex-1">
        <Container size="lg">
          {/* Hero Section */}
          <HeroSection
            title="Create Professional Ad Videos In Minutes"
            subtitle="Generate AI-powered video ads with perfect product consistency. Get vertical (9:16), square (1:1), and horizontal (16:9) formats instantly."
            cta={{
              text: 'Start Creating',
              link: '/signup',
            }}
            secondaryAction={{
              text: 'View Demo',
              onClick: () => {
                // TODO: Link to demo video
                console.log('Show demo video')
              },
            }}
          />

          {/* Demo Cards Section */}
          <motion.section
            className="py-20"
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-100px' }}
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  title: 'Upload Product',
                  description: 'Upload your product image and brand info',
                  icon: '📸',
                },
                {
                  title: 'AI Generates Scenes',
                  description: 'AI plans scenes that showcase your product',
                  icon: '🎬',
                },
                {
                  title: 'Download Videos',
                  description: 'Get ready-to-post videos for every platform',
                  icon: '🚀',
                },
              ].map((item, i) => (
                <motion.div
                  key={i}
                  className="text-center"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  viewport={{ once: true }}
                >
                  <div className="text-5xl mb-4">{item.icon}</div>
                  <h3 className="text-xl font-semibold text-slate-100 mb-2">
                    {item.title}
                  </h3>
                  <p className="text-slate-400">{item.description}</p>
                </motion.div>
              ))}
            </div>
          </motion.section>

          {/* Features Section */}
          <FeaturesSection />

          {/* CTA Section */}
          <motion.section
            className="py-20 text-center"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-100px' }}
          >
            <h2 className="text-4xl font-bold text-slate-100 mb-6">
              Ready to create amazing ads?
            </h2>
            <p className="text-xl text-slate-400 mb-8">
              Join thousands of creators using GenAds to generate professional video ads
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Button
                size="lg"
                variant="gradient"
                onClick={() => navigate('/signup')}
                className="gap-2"
              >
                <Play className="w-5 h-5" />
                Get Started Free
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => navigate('/login')}
              >
                Sign In
              </Button>
            </div>
          </motion.section>
        </Container>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  )
}

