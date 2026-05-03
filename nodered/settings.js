module.exports = {
    // Puerto
    uiPort: process.env.PORT || 1880,

    // Directorio de datos
    userDir: '/data',

    // Archivo de flujos
    flowFile: 'flows.json',

    // Seguridad — admin con usuario y contraseña
    adminAuth: {
        type: "credentials",
        users: [{
            username: "admin",
            password: "$2b$08$Dj0rRBsVrkhMJC7F9E3Lm.3mGNTBs0E5K.5B5LjWmGg2T0K2F3Kly",
            permissions: "*"
        }]
    },

    // Logging
    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    },

    // Editor habilitado
    disableEditor: false,

    // HTTP
    httpAdminRoot: '/',
    httpNodeRoot: '/api',

    // Dashboard UI
    ui: { path: "ui" },

    // Contexto global persistente
    contextStorage: {
        default: {
            module: "memory"
        }
    },

    // Exportar flujos con credenciales
    exportGlobalContextKeys: false,

    editorTheme: {
        page: {
            title: "ClimaLink Station"
        }
    }
}