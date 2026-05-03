module.exports = {
    uiPort: process.env.PORT || 1880,
    userDir: '/data',
    flowFile: 'flows.json',

    // Sin autenticación — acceso libre al editor
    // En producción se recomienda agregar adminAuth
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
    ui: { path: "ui" },

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