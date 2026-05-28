const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

function loadEnv(filePath) {
    if (!fs.existsSync(filePath)) {
        return {};
    }

    const env = {};
    for (const rawLine of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line || line.startsWith("#")) {
            continue;
        }
        const separator = line.indexOf("=");
        if (separator === -1) {
            continue;
        }
        const key = line.slice(0, separator).trim();
        let value = line.slice(separator + 1).trim();
        if (
            (value.startsWith("\"") && value.endsWith("\"")) ||
            (value.startsWith("'") && value.endsWith("'"))
        ) {
            value = value.slice(1, -1);
        }
        env[key] = value;
    }
    return env;
}

function configuredEndpoint() {
    const configPath = path.join(root, "assets/js/config.js");
    const config = fs.readFileSync(configPath, "utf8");
    const match = config.match(/chatEndpoint:\s*["']([^"']+)["']/);
    return match ? match[1] : "";
}

function siteOrigin() {
    const cnamePath = path.join(root, "CNAME");
    if (fs.existsSync(cnamePath)) {
        const cname = fs.readFileSync(cnamePath, "utf8").trim();
        if (cname) {
            return `https://${cname}`;
        }
    }
    return "https://zhaobangz.github.io";
}

async function main() {
    const endpoint = configuredEndpoint();
    if (!endpoint) {
        throw new Error("assets/js/config.js does not define a chatEndpoint.");
    }

    const env = loadEnv(path.join(root, ".env"));
    const accessToken = env.SITE_ACCESS_TOKEN;
    if (!accessToken) {
        throw new Error("SITE_ACCESS_TOKEN is missing from local .env.");
    }

    const response = await fetch(endpoint, {
        method: "POST",
        headers: {
            "content-type": "application/json",
            "origin": siteOrigin(),
            "x-site-access-token": accessToken,
        },
        body: JSON.stringify({
            prompt: "Return a concise readiness check for the public Autonomous AI Researcher demo.",
        }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(`Live chat failed with ${response.status}: ${data.error || "unknown error"}`);
    }

    console.log(JSON.stringify({
        status: response.status,
        model: data.model,
        outputPreview: String(data.output || "").slice(0, 240),
    }, null, 2));
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
