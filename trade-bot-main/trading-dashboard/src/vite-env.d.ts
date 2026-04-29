/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_BASE_BACKEND_URL: string
    readonly VITE_API_BASE_FRONTEND_URL: string
    readonly VITE_ENABLE_AUTH: string
    readonly VITE_SUPABASE_URL: string
    readonly VITE_SUPABASE_ANON_KEY: string
    readonly DEV: boolean
    readonly PROD: boolean
    readonly MODE: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}
