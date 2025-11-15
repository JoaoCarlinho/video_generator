import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { motion } from 'framer-motion'

interface HeroSectionProps {
  title: string
  subtitle: string
  cta?: {
    text: string
    onClick?: () => void
    link?: string
  }
  secondaryAction?: {
    text: string
    onClick?: () => void
  }
  gradient?: boolean
}

export const HeroSection = ({
  title,
  subtitle,
  cta,
  secondaryAction,
  gradient = true,
}: HeroSectionProps) => {
  const navigate = useNavigate()

  const handleCTA = () => {
    if (cta?.onClick) {
      cta.onClick()
    } else if (cta?.link) {
      navigate(cta.link)
    }
  }

  const handleSecondary = () => {
    if (secondaryAction?.onClick) {
      secondaryAction.onClick()
    }
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.3,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.8 },
    },
  }

  return (
    <motion.div
      className="text-center space-y-8 py-20"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Title */}
      <motion.h1
        className="text-5xl md:text-6xl font-bold leading-tight"
        variants={itemVariants}
      >
        <span className="text-slate-100">{title.split('In Minutes')[0]}</span>
        {gradient && (
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500">
            {' '}In Minutes
          </span>
        )}
      </motion.h1>

      {/* Subtitle */}
      <motion.p className="text-xl md:text-2xl text-slate-400 max-w-2xl mx-auto" variants={itemVariants}>
        {subtitle}
      </motion.p>

      {/* CTA Buttons */}
      <motion.div className="flex gap-4 justify-center pt-8 flex-wrap" variants={itemVariants}>
        {cta && (
          <Button
            size="lg"
            variant="gradient"
            onClick={handleCTA}
            className="text-lg px-8 py-3"
          >
            {cta.text}
          </Button>
        )}
        {secondaryAction && (
          <Button
            size="lg"
            variant="outline"
            onClick={handleSecondary}
            className="text-lg px-8 py-3"
          >
            {secondaryAction.text}
          </Button>
        )}
      </motion.div>
    </motion.div>
  )
}

