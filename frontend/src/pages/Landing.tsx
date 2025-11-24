import { Button } from "@/components/ui/Button";
import type { ButtonVariant } from "@/components/ui/Button";
import { Link } from "react-router-dom";
import { Sparkles, Video, Zap, Target } from "lucide-react";
import { motion } from "framer-motion";

const Landing = () => {
  return (
    <div className="relative min-h-screen bg-gradient-to-b from-blue-50 via-blue-100 to-blue-50 flex flex-col">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-200/30 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-100/40 rounded-full blur-3xl"></div>
      </div>

      {/* Header */}
      <nav className="relative z-10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Link to="/" className="text-2xl font-bold text-gray-900">
            GenAds
          </Link>
          <div className="flex gap-3">
            <Link to="/login">
              <Button variant="secondary">
                Sign In
              </Button>
            </Link>
            <Link to="/signup">
              <Button variant="default">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="flex-1">
        <div className="max-w-7xl mx-auto px-6">
          {/* Hero Section */}
          <motion.section
            className="py-20 text-center"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
              Create Professional Ad Videos In Minutes
            </h1>
            <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
              Generate AI-powered video ads with perfect product consistency. Get horizontal (16:9) format instantly.
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Link to="/signup">
                <Button size="lg" variant="default">
                  Start Creating
                </Button>
              </Link>
              <Button
                size="lg"
                variant="secondary"
                onClick={() => {
                  // TODO: Link to demo video
                  console.log('Show demo video')
                }}
              >
                View Demo
              </Button>
            </div>
          </motion.section>

          {/* Demo Cards Section */}
          <motion.section
            className="py-20"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
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
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    {item.title}
                  </h3>
                  <p className="text-gray-600">{item.description}</p>
                </motion.div>
              ))}
            </div>
          </motion.section>

          {/* CTA Section */}
          <motion.section
            className="py-20 text-center"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-100px' }}
          >
            <h2 className="text-4xl font-bold text-gray-900 mb-6">
              Ready to create amazing ads?
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              Join thousands of creators using GenAds to generate professional video ads
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Link to="/signup">
                <Button
                  size="lg"
                  variant="default"
                  className="gap-2"
                >
                  <Sparkles className="w-5 h-5" />
                  Get Started Free
                </Button>
              </Link>
              <Link to="/login">
                <Button
                  size="lg"
                  variant="secondary"
                >
                  Sign In
                </Button>
              </Link>
            </div>
          </motion.section>
        </div>
      </div>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-24">
        <motion.div 
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-4xl font-bold mb-4 text-off-white">Why Choose GenAds?</h2>
          <p className="text-muted-gray text-lg">
            The most powerful AI video generation platform for marketers
          </p>
        </motion.div>
        
        <div className="grid md:grid-cols-3 gap-8">
          {[
            {
              icon: Video,
              title: "AI-Powered Creation",
              description: "Our advanced AI understands your brand and creates professional video ads that convert.",
              gradient: "from-gold/20 to-transparent",
            },
            {
              icon: Zap,
              title: "Lightning Fast",
              description: "Generate high-quality video ads in minutes, not days. Speed up your marketing workflow.",
              gradient: "from-gold/20 to-transparent",
            },
            {
              icon: Target,
              title: "Precision Targeting",
              description: "Tailor your videos for specific audiences with AI-driven insights and customization.",
              gradient: "from-gold/20 to-transparent",
            },
          ].map((feature, index) => (
            <motion.div
              key={index}
              className="bg-olive-800/50 backdrop-blur-sm border border-olive-600 rounded-xl p-8 hover:shadow-gold transition-all duration-300 hover:scale-105 hover:border-gold/50"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <div className={`bg-gradient-to-br ${feature.gradient} h-12 w-12 rounded-lg flex items-center justify-center mb-6 shadow-gold`}>
                <feature.icon className="h-6 w-6 text-gold" />
              </div>
              <h3 className="text-2xl font-semibold mb-3 text-off-white">{feature.title}</h3>
              <p className="text-muted-gray">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-24">
        <motion.div 
          className="bg-gradient-silky-gold rounded-2xl p-12 text-center shadow-gold-lg border border-gold-silkyDark/30"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-4xl font-bold mb-4 text-[#1a1a1a]">Ready to Transform Your Marketing?</h2>
          <p className="text-lg mb-8 text-[#2a2a2a]/90">
            Join thousands of brands creating stunning video ads with GenAds
          </p>
          <Link to="/signup">
            <Button variant="default" size="lg" className="text-lg bg-olive-950 text-gold hover:bg-olive-900 shadow-lg transition-transform duration-200 hover:scale-105">
              Get Started Now
            </Button>
          </Link>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-olive-600/50 py-8">
        <div className="container mx-auto px-4 text-center text-muted-gray">
          <p>&copy; 2024 GenAds. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export { Landing };
