module.exports = {
  devServer: {
    proxy: {
      '/api': {
        target: 'http://gusto2-backend:8000',
        changeOrigin: true
      }
    }
  },
  configureWebpack: {
    optimization: {
      nodeEnv: process.env.NODE_ENV
    }
  }
}
