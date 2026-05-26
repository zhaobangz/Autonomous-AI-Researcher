const fs = require("node:fs");
const path = require("node:path");

const root = process.cwd();
const requiredFiles = [
    "index.html",
    "404.html",
    "assets/css/styles.css",
    "assets/js/config.js",
    "assets/js/app.js",
    "robots.txt",
    "sitemap.xml",
];

for (const file of requiredFiles) {
    const fullPath = path.join(root, file);
    if (!fs.existsSync(fullPath)) {
        throw new Error(`Missing required file: ${file}`);
    }
}

const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const requiredSnippets = [
    '<form id="prompt-form"',
    'src="assets/js/config.js"',
    'src="assets/js/app.js"',
    'href="assets/css/styles.css"',
    'class="brand" href="./"',
];

for (const snippet of requiredSnippets) {
    if (!index.includes(snippet)) {
        throw new Error(`index.html is missing: ${snippet}`);
    }
}

if (index.includes("OPENAI_API_KEY")) {
    throw new Error("index.html must not reference OPENAI_API_KEY.");
}

const app = fs.readFileSync(path.join(root, "assets/js/app.js"), "utf8");
if (app.includes('fetch("/api/chat"') || app.includes("fetch('/api/chat'")) {
    throw new Error("GitHub Pages cannot host /api/chat; app.js must use the configured chat endpoint.");
}

console.log("Site validation passed.");
