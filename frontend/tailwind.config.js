/** @type {import('tailwindcss').Config} */
export default {
  // Content paths - these are scanned for class names
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    // Explicitly include component libraries if used
    "./node_modules/@radix-ui/**/*.{js,ts,jsx,tsx}",
  ],
  
  // Theme configuration
  theme: {
    colors: {
      white: '#ffffff',
      black: '#000000',
      transparent: 'transparent',
      slate: {
        50: '#f8fafc',
        100: '#f1f5f9',
        200: '#e2e8f0',
        300: '#cbd5e1',
        400: '#94a3b8',
        500: '#64748b',
        600: '#475569',
        700: '#334155',
        800: '#1e293b',
        900: '#0f172a',
      },
      indigo: {
        50: '#eef2ff',
        100: '#e0e7ff',
        200: '#c7d2fe',
        300: '#a5b4fc',
        400: '#818cf8',
        500: '#6366f1',
        600: '#4f46e5',
        700: '#4338ca',
        800: '#3730a3',
        900: '#312e81',
      },
      purple: {
        400: '#c084fc',
        500: '#a855f7',
        600: '#9333ea',
        700: '#7e22ce',
        800: '#6b21a8',
      },
      cyan: {
        300: '#06d6d6',
        400: '#06b6d4',
        500: '#06b6d4',
        600: '#0891b2',
        700: '#0e7490',
      },
      pink: {
        500: '#ec4899',
        600: '#db2777',
      },
      emerald: {
        500: '#10b981',
        600: '#059669',
      },
      red: {
        400: '#f87171',
        500: '#ef4444',
        600: '#dc2626',
      },
      amber: {
        500: '#f59e0b',
        600: '#d97706',
      },
      blue: {
        500: '#3b82f6',
        600: '#2563eb',
      },
    },
    
    fontSize: {
      xs: ['12px', { lineHeight: '16px' }],
      sm: ['14px', { lineHeight: '20px' }],
      base: ['16px', { lineHeight: '24px' }],
      lg: ['18px', { lineHeight: '28px' }],
      xl: ['20px', { lineHeight: '28px' }],
      '2xl': ['24px', { lineHeight: '32px' }],
      '3xl': ['30px', { lineHeight: '36px' }],
      '4xl': ['36px', { lineHeight: '40px' }],
      '5xl': ['48px', { lineHeight: '56px' }],
    },
    
    fontFamily: {
      sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      mono: ['Fira Code', 'Monaco', 'monospace'],
    },
    
    fontWeight: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
    
    spacing: {
      0: '0',
      px: '1px',
      0.5: '4px',
      1: '8px',
      2: '16px',
      3: '24px',
      4: '32px',
      5: '40px',
      6: '48px',
      8: '64px',
      10: '80px',
      12: '96px',
    },
    
    boxShadow: {
      none: 'none',
      sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
      base: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
      md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
      lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
      xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
      '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
      glow: '0 0 20px rgba(79, 70, 229, 0.3)',
      'glow-lg': '0 0 40px rgba(79, 70, 229, 0.5)',
      'inner': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.05)',
    },
    
    borderRadius: {
      none: '0',
      xs: '4px',
      sm: '6px',
      base: '8px',
      md: '12px',
      lg: '16px',
      xl: '20px',
      '2xl': '24px',
      full: '9999px',
    },
    
    backgroundColor: (theme) => ({
      ...theme('colors'),
      gradient: 'linear-gradient(135deg, #4f46e5 0%, #9333ea 100%)',
      'gradient-dark': 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    }),
    
    backgroundImage: {
      'gradient-to-br': 'linear-gradient(to bottom right, var(--tw-gradient-stops))',
      'gradient-indigo-purple': 'linear-gradient(135deg, #4f46e5 0%, #9333ea 100%)',
      'gradient-dark': 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    },
    
    animation: {
      'fade-in': 'fadeIn 0.3s ease-in-out',
      'fade-out': 'fadeOut 0.3s ease-in-out',
      'scale-in': 'scaleIn 0.3s ease-out',
      'scale-out': 'scaleOut 0.3s ease-in',
      'slide-in': 'slideIn 0.3s ease-out',
      'slide-out': 'slideOut 0.3s ease-in',
      'pulse-subtle': 'pulseSubtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      'spin-slow': 'spin 3s linear infinite',
      'bounce-soft': 'bouncesoft 2s ease-in-out infinite',
    },
    
    keyframes: {
      fadeIn: {
        '0%': { opacity: '0' },
        '100%': { opacity: '1' },
      },
      fadeOut: {
        '0%': { opacity: '1' },
        '100%': { opacity: '0' },
      },
      scaleIn: {
        '0%': { opacity: '0', transform: 'scale(0.95)' },
        '100%': { opacity: '1', transform: 'scale(1)' },
      },
      scaleOut: {
        '0%': { opacity: '1', transform: 'scale(1)' },
        '100%': { opacity: '0', transform: 'scale(0.95)' },
      },
      slideIn: {
        '0%': { opacity: '0', transform: 'translateY(-10px)' },
        '100%': { opacity: '1', transform: 'translateY(0)' },
      },
      slideOut: {
        '0%': { opacity: '1', transform: 'translateY(0)' },
        '100%': { opacity: '0', transform: 'translateY(-10px)' },
      },
      pulseSubtle: {
        '0%, 100%': { opacity: '1' },
        '50%': { opacity: '.8' },
      },
      bouncesoft: {
        '0%, 100%': { transform: 'translateY(0)' },
        '50%': { transform: 'translateY(-4px)' },
      },
    },
    
    transitionDuration: {
      0: '0ms',
      75: '75ms',
      100: '100ms',
      150: '150ms',
      200: '200ms',
      300: '300ms',
      500: '500ms',
      700: '700ms',
      1000: '1000ms',
    },
    
    transitionTimingFunction: {
      linear: 'linear',
      in: 'cubic-bezier(0.4, 0, 1, 1)',
      out: 'cubic-bezier(0, 0, 0.2, 1)',
      'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
      'ease-in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },
  
  // Plugins
  plugins: [],
  
  // Important: Ensure proper CSS specificity for Tailwind utilities
  important: false,
  
  // Respect prefers-reduced-motion
  corePlugins: {
    animation: true,
    transition: true,
  },
}
