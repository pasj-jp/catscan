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
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/conferences': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/word': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            }
        }
    }
})
