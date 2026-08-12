const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const root = path.resolve(__dirname, "..");
const outputDir = path.join(root, "_site");

function copyRequiredFile(filePath) {
    const source = path.join(root, filePath);
    const destination = path.join(outputDir, filePath);

    if (!fs.existsSync(source)) {
        throw new Error(`Missing required file: ${filePath}`);
    }

    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
}

function removeNamedFiles(dirPath, fileName) {
    for (const entry of fs.readdirSync(dirPath, { withFileTypes: true })) {
        const fullPath = path.join(dirPath, entry.name);
        if (entry.isDirectory()) {
            removeNamedFiles(fullPath, fileName);
        } else if (entry.name === fileName) {
            fs.rmSync(fullPath);
        }
    }
}

execFileSync(process.execPath, [path.join(root, "scripts/validate-site.js")], {
    cwd: root,
    stdio: "inherit",
});

fs.rmSync(outputDir, { recursive: true, force: true });
fs.mkdirSync(outputDir, { recursive: true });

for (const file of ["index.html", "404.html", "robots.txt", "sitemap.xml"]) {
    copyRequiredFile(file);
}

fs.cpSync(path.join(root, "assets"), path.join(outputDir, "assets"), {
    recursive: true,
});
removeNamedFiles(outputDir, ".DS_Store");

fs.writeFileSync(path.join(outputDir, ".nojekyll"), "");

console.log("GitHub Pages artifact built in _site.");
