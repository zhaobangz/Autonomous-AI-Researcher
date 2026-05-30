const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

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

    const origin = siteOrigin();
    const preflight = await fetch(endpoint, {
        method: "OPTIONS",
        headers: {
            "origin": origin,
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    });

    if (preflight.status !== 204 || preflight.headers.get("access-control-allow-origin") !== origin) {
        throw new Error(`Live chat CORS preflight failed with ${preflight.status}.`);
    }

    const response = await fetch(endpoint, {
        method: "POST",
        headers: {
            "content-type": "application/json",
            "origin": origin,
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
        preflightStatus: preflight.status,
        status: response.status,
        model: data.model,
        outputPreview: String(data.output || "").slice(0, 240),
    }, null, 2));
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
