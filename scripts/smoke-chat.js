const fs = require("node:fs");
const path = require("node:path");
const { Readable } = require("node:stream");

const root = path.resolve(__dirname, "..");

function loadDotEnv(filePath) {
    if (!fs.existsSync(filePath)) {
        return;
    }

    const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) {
            continue;
        }

        const separator = trimmed.indexOf("=");
        if (separator === -1) {
            continue;
        }

        const key = trimmed.slice(0, separator).trim();
        let value = trimmed.slice(separator + 1).trim();
        if (
            (value.startsWith('"') && value.endsWith('"')) ||
            (value.startsWith("'") && value.endsWith("'"))
        ) {
            value = value.slice(1, -1);
        }

        if (!process.env[key]) {
            process.env[key] = value;
        }
    }
}

function createMockResponse() {
    return {
        statusCode: 200,
        headers: {},
        body: "",
        setHeader(key, value) {
            this.headers[key.toLowerCase()] = value;
        },
        end(chunk) {
            this.body += chunk || "";
        },
    };
}

async function main() {
    loadDotEnv(path.join(root, ".env"));

    const provider = (process.env.LLM_PROVIDER || "").toLowerCase().trim()
        || "openrouter";
    const keyNames = {
        openrouter: "OPENROUTER_API_KEY",
        openai: "OPENAI_API_KEY",
        anthropic: "ANTHROPIC_API_KEY",
    };
    const keyName = keyNames[provider];
    if (!keyName) {
        throw new Error("The public chat smoke test supports LLM_PROVIDER=openai, openrouter, or anthropic.");
    }

    if (provider === "openai") {
        process.env.OPENAI_MODEL = process.env.OPENAI_MODEL || "gpt-4o-mini";
    } else if (provider === "anthropic") {
        process.env.ANTHROPIC_MODEL = process.env.ANTHROPIC_MODEL || process.env.LLM_MODEL || "claude-sonnet-4-6";
    } else {
        process.env.OPENROUTER_MODEL = process.env.OPENROUTER_MODEL || process.env.LLM_MODEL || "openai/gpt-4o-mini";
    }

    if (!process.env[keyName] || process.env[keyName].startsWith("your_")) {
        throw new Error(`${keyName} is not configured.`);
    }
    if (provider === "openai" && process.env.OPENAI_API_KEY.startsWith("sk-or-")) {
        throw new Error("OPENAI_API_KEY looks like an OpenRouter key. Set LLM_PROVIDER=openrouter and move the key to OPENROUTER_API_KEY.");
    }

    const handler = require(path.join(root, "api/chat.js"));
    const payload = JSON.stringify({
        prompt: "In two concise sentences, describe the mission of an autonomous AI researcher.",
    });

    const req = Readable.from([payload]);
    req.method = "POST";
    req.headers = {
        "content-type": "application/json",
        "content-length": Buffer.byteLength(payload),
        "host": "localhost:3000",
        "origin": "http://localhost:3000",
        "x-forwarded-for": "127.0.0.1",
    };
    req.socket = { remoteAddress: "127.0.0.1" };

    const res = createMockResponse();
    await handler(req, res);

    const body = JSON.parse(res.body || "{}");
    if (res.statusCode !== 200 || !body.output) {
        throw new Error(`Smoke test failed with status ${res.statusCode}: ${body.error || "No output"}`);
    }

    console.log(JSON.stringify({
        statusCode: res.statusCode,
        model: body.model,
        outputPreview: body.output.slice(0, 220),
    }, null, 2));
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
