module.exports = {
    uiPort: process.env.PORT || 1880,
    userDir: '/data',
    flowFile: 'flows.json',

    // Clave para encriptar credenciales
    // Al definirla, Node-RED acepta las credenciales del flows.json
    credentialSecret: "climalink2026pesquera",

    adminAuth: null,

    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    },

    disableEditor: false,
    httpAdminRoot: '/',
    httpNodeRoot: '/api',
    ui: { path: "ui", defaultTheme: "dark" },

    contextStorage: {
        default: {
            module: "memory"
        }
    },

    editorTheme: {
        page: {
            title: "ClimaLink Station"
        }
    }
}