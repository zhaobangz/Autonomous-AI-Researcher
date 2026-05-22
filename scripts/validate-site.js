const fs = require("node:fs");
const path = require("node:path");

const root = process.cwd();
const requiredFiles = [
    "index.html",
    "404.html",
    "assets/css/styles.css",
    "assets/js/app.js",
    "api/chat.js",
    "vercel.json",
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
    'src="/assets/js/app.js"',
    'href="/assets/css/styles.css"',
];

for (const snippet of requiredSnippets) {
    if (!index.includes(snippet)) {
        throw new Error(`index.html is missing: ${snippet}`);
    }
}

if (index.includes("OPENAI_API_KEY")) {
    throw new Error("index.html must not reference OPENAI_API_KEY.");
}

console.log("Site validation passed.");
