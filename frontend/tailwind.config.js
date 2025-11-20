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
      charcoal: {
        950: '#111A2E', // New midnight background
        900: '#162035',
        800: '#1B2742',
        700: '#233050',
      },
      olive: {
        950: '#111A2E',
        900: '#162035',
        800: '#1B2742',
        700: '#233050',
        600: '#5E6A7C', // Neutral divider
      },
      slate: {
        50: '#f8fafc',
        100: '#f1f5f9',
        200: '#e2e8f0',
        300: '#cbd5e1',
        400: '#94a3b8',
        500: '#64748b',
        600: '#475569',
        700: '#151924', // Raised surfaces
        800: '#11141B', // Cards
        900: '#0f172a',
      },
      // Luxury Gold Accents
      gold: {
        DEFAULT: '#F3D9A4', // Primary accent
        dark: '#D4B676', // Hover state
        foreground: '#1a1a1a', // Text on gold
        silky: '#C9A86A', // Silky gold - darker, more muted
        silkyLight: '#E8D4A8', // Light silky gold
        silkyDark: '#B8965A', // Dark silky gold
      },
      // Neutral Accents
      neutral: {
        DEFAULT: '#7E8A9A', // Secondary accent
        dim: '#5E6A7C', // Borders
      },
      // Text Colors
      'off-white': '#E5E7EB', // Body text
      'muted-gray': '#9CA3AF', // Secondary text
      'muted-dark': '#6B7280', // Tertiary text
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
      glow: '0 0 20px rgba(243, 217, 164, 0.2)',
      'glow-lg': '0 0 40px rgba(243, 217, 164, 0.3)',
      gold: '0 0 20px rgba(243, 217, 164, 0.3)',
      'gold-lg': '0 0 40px rgba(243, 217, 164, 0.5)',
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
      gradient: 'linear-gradient(135deg, #111a2e 0%, #1b2742 100%)',
      'gradient-dark': 'linear-gradient(135deg, #111a2e 0%, #18233d 100%)',
      'gradient-hero': 'linear-gradient(135deg, #111a2e 0%, #18233d 50%, #1f2d4a 100%)',
      'gradient-primary': 'linear-gradient(135deg, #F3D9A4 0%, #D4B676 100%)',
      'gradient-gold': 'linear-gradient(135deg, #F3D9A4 0%, #D4B676 100%)',
      'gradient-olive': 'linear-gradient(135deg, #07090c 0%, #0f141b 50%, #151b26 100%)',
      'gradient-silky-gold': 'linear-gradient(135deg, #C9A86A 0%, #B8965A 50%, #A6854A 100%)',
    }),
    
    backgroundImage: {
      'gradient-to-br': 'linear-gradient(to bottom right, var(--tw-gradient-stops))',
      'gradient-dark': 'linear-gradient(135deg, #050608 0%, #0B0D10 100%)',
      'gradient-hero': 'linear-gradient(135deg, #050608 0%, #0B0D10 45%, #11141B 100%)',
      'gradient-primary': 'linear-gradient(135deg, #F3D9A4 0%, #D4B676 100%)',
      'gradient-gold': 'linear-gradient(135deg, #F3D9A4 0%, #D4B676 100%)',
      'gradient-olive': 'linear-gradient(135deg, #1a1f1a 0%, #232823 50%, #2d332d 100%)',
      'gradient-silky-gold': 'linear-gradient(135deg, #C9A86A 0%, #B8965A 50%, #A6854A 100%)',
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
