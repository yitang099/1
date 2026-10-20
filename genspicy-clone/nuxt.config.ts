export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  devServer: {
    host: '0.0.0.0',
    port: 3000,
  },
  css: ['~/assets/css/main.css'],
  app: {
    head: {
      title: 'Genspicy Clone (Local)',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Local feature clone — no payment in v1' },
      ],
    },
  },
  runtimeConfig: {
    public: {
      siteName: 'Genspicy Clone',
      genspicyApiBase: 'https://api.genspicy.ai',
    },
  },
})
