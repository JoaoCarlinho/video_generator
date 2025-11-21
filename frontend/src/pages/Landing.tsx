import { Button } from "@/components/ui/Button";
import type { ButtonVariant } from "@/components/ui/Button";
import { Link } from "react-router-dom";
import { Sparkles, Video, Zap, Target } from "lucide-react";
import { motion } from "framer-motion";

const Landing = () => {
  return (
    <div className="min-h-screen bg-olive-950 bg-gradient-hero">
      {/* Navigation */}
      <nav className="relative z-50 border-b border-olive-600/50 backdrop-blur-md bg-olive-950/30 sticky top-0">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-gold" />
            <span className="text-2xl font-bold text-gradient-gold">
              GenAds
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login">
              <Button variant="outline" size="lg" className="transition-transform duration-200 hover:scale-105">
                Login
              </Button>
            </Link>
            <Link to="/signup">
              <Button variant={"hero" as ButtonVariant} size="lg" className="transition-transform duration-200 hover:scale-105">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute inset-0 bg-gradient-to-br from-gold/10 via-transparent to-transparent" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(243,217,164,0.1),transparent_50%)]" />
        </div>
        
        <div className="container mx-auto px-4 py-32 relative z-10">
          <motion.div 
            className="max-w-4xl mx-auto text-center space-y-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-5xl md:text-7xl font-bold leading-tight text-balance">
              Create Stunning{" "}
              <span className="text-gradient-gold">
                AI-Powered
              </span>
              <br />
              Video Ads in Minutes
            </h1>
            <p className="text-xl text-muted-gray max-w-2xl mx-auto">
              Transform your brand vision into captivating video advertisements with our cutting-edge AI technology.
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Link to="/signup">
                <Button variant={"hero" as ButtonVariant} size="lg" className="text-lg transition-transform duration-200 hover:scale-105">
                  Start Creating Free
                </Button>
              </Link>
              <Link to="/login">
                <Button variant="outline" size="lg" className="text-lg transition-transform duration-200 hover:scale-105">
                  Watch Demo
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

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
