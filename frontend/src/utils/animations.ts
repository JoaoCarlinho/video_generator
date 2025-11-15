// Framer Motion animation presets
export const animations = {
  // Container animations
  containerVariants: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  },

  // Item animations
  itemVariants: {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
        ease: 'easeOut',
      },
    },
  },

  // Fade animations
  fadeIn: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { duration: 0.3 },
    },
  },

  fadeOut: {
    hidden: { opacity: 1 },
    visible: {
      opacity: 0,
      transition: { duration: 0.3 },
    },
  },

  // Slide animations
  slideInLeft: {
    hidden: { opacity: 0, x: -50 },
    visible: {
      opacity: 1,
      x: 0,
      transition: { duration: 0.4, ease: 'easeOut' },
    },
  },

  slideInRight: {
    hidden: { opacity: 0, x: 50 },
    visible: {
      opacity: 1,
      x: 0,
      transition: { duration: 0.4, ease: 'easeOut' },
    },
  },

  slideInUp: {
    hidden: { opacity: 0, y: 50 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4, ease: 'easeOut' },
    },
  },

  slideInDown: {
    hidden: { opacity: 0, y: -50 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4, ease: 'easeOut' },
    },
  },

  // Scale animations
  scaleIn: {
    hidden: { opacity: 0, scale: 0.95 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: { duration: 0.3, ease: 'easeOut' },
    },
  },

  scaleOut: {
    hidden: { opacity: 1, scale: 1 },
    visible: {
      opacity: 0,
      scale: 0.95,
      transition: { duration: 0.3, ease: 'easeIn' },
    },
  },

  // Rotate animations
  rotateIn: {
    hidden: { opacity: 0, rotate: -10 },
    visible: {
      opacity: 1,
      rotate: 0,
      transition: { duration: 0.4, ease: 'easeOut' },
    },
  },

  // Pulse animation
  pulse: {
    animate: {
      opacity: [1, 0.8, 1],
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: 'easeInOut',
      },
    },
  },

  // Bounce animation
  bounce: {
    animate: {
      y: [0, -10, 0],
      transition: {
        duration: 0.6,
        repeat: Infinity,
        ease: 'easeInOut',
      },
    },
  },

  // Glow animation
  glow: {
    animate: {
      boxShadow: [
        '0 0 20px rgba(79, 70, 229, 0.3)',
        '0 0 40px rgba(79, 70, 229, 0.5)',
        '0 0 20px rgba(79, 70, 229, 0.3)',
      ],
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: 'easeInOut',
      },
    },
  },

  // Modal animations
  modalOverlay: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { duration: 0.2 },
    },
  },

  modalContent: {
    hidden: { opacity: 0, scale: 0.95, y: 20 },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: { duration: 0.3, ease: 'easeOut' },
    },
    exit: {
      opacity: 0,
      scale: 0.95,
      y: 20,
      transition: { duration: 0.2, ease: 'easeIn' },
    },
  },

  // Toast animations
  toastEnter: {
    hidden: { opacity: 0, y: 50, x: 100 },
    visible: {
      opacity: 1,
      y: 0,
      x: 0,
      transition: { duration: 0.3, ease: 'easeOut' },
    },
  },

  toastExit: {
    hidden: { opacity: 0, y: 50, x: 100 },
    visible: {
      opacity: 0,
      y: 0,
      x: 100,
      transition: { duration: 0.3, ease: 'easeIn' },
    },
  },

  // Page transitions
  pageEnter: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { duration: 0.4 },
    },
  },

  pageExit: {
    hidden: { opacity: 1 },
    visible: {
      opacity: 0,
      transition: { duration: 0.2 },
    },
  },

  // Hover animations
  hoverScale: {
    whileHover: { scale: 1.05 },
    whileTap: { scale: 0.95 },
  },

  hoverLift: {
    whileHover: { y: -4 },
    transition: { duration: 0.2 },
  },

  // Progress animations
  progressFill: {
    hidden: { width: 0 },
    visible: (width: number) => ({
      width: `${width}%`,
      transition: { duration: 0.5, ease: 'easeInOut' },
    }),
  },
}

// Transition presets
export const transitions = {
  fast: { duration: 0.2, ease: 'easeInOut' },
  normal: { duration: 0.3, ease: 'easeInOut' },
  slow: { duration: 0.5, ease: 'easeInOut' },
  verySlow: { duration: 1, ease: 'easeInOut' },
}

// Easing presets
export const easings = {
  easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
  easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
  easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
}

