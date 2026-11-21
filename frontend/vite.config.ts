import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vitejs.dev/config/
export default defineConfig({
    base: '/',
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            '/api': {
                target: process.env.CATSCAN_API_PROXY_TARGET || 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
        }
    }
})
