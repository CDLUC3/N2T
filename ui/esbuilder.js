/**
 * Implements the npm run build operation
 * 
 */
 const { build } = require("esbuild")

build({
    logLevel: "info",
    entryPoints: [
        'src/js/main.js'
    ],
    bundle: true,
    outdir: "build/js",
    splitting: true,
    format:"esm",
    platform: "browser",
}).catch(() => process.exit(1))
