export default {
  plugins: {
    '@tailwindcss/postcss': {
      // Ensure proper processing in development and production
      corePlugins: {
        // Don't disable any core plugins - let Tailwind handle everything
      },
    },
    autoprefixer: {},
  },
}
