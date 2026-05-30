const assert = require("node:assert/strict");

process.env.PUBLIC_SITE_ORIGIN = [
    "https://research.autonomous-ai.io",
    "https://zhaobangz.github.io/Autonomous-AI-Researcher",
].join(",");

const handler = require("../vercel-chat-api/api/chat.js");

function mockReq({ method, origin, headers = {}, body = "" }) {
    return {
        method,
        headers: {
            host: "autonomous-ai-researcher-chat-api.vercel.app",
            ...(origin ? { origin } : {}),
            ...headers,
        },
        socket: { remoteAddress: "127.0.0.1" },
        async *[Symbol.asyncIterator]() {
            if (body) {
                yield Buffer.from(body);
            }
        },
    };
}

function mockRes() {
    const headers = new Map();
    return {
        statusCode: 200,
        body: "",
        setHeader(key, value) {
            headers.set(key.toLowerCase(), value);
        },
        getHeader(key) {
            return headers.get(key.toLowerCase());
        },
        end(chunk = "") {
            this.body += chunk;
        },
        header(key) {
            return headers.get(key.toLowerCase());
        },
    };
}

async function call(req) {
    const res = mockRes();
    await handler(req, res);
    return res;
}

async function main() {
    const customPreflight = await call(mockReq({
        method: "OPTIONS",
        origin: "https://research.autonomous-ai.io",
        headers: {
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    }));

    assert.equal(customPreflight.statusCode, 204);
    assert.equal(customPreflight.header("access-control-allow-origin"), "https://research.autonomous-ai.io");
    assert.equal(customPreflight.header("access-control-allow-methods"), "POST, OPTIONS");
    assert.equal(customPreflight.header("access-control-allow-headers"), "Content-Type");

    const githubPreflight = await call(mockReq({
        method: "OPTIONS",
        origin: "https://zhaobangz.github.io",
    }));

    assert.equal(githubPreflight.statusCode, 204);
    assert.equal(githubPreflight.header("access-control-allow-origin"), "https://zhaobangz.github.io");

    const shortPrompt = await call(mockReq({
        method: "POST",
        origin: "https://research.autonomous-ai.io",
        headers: {
            "content-type": "application/json",
        },
        body: JSON.stringify({ prompt: "short" }),
    }));

    assert.equal(shortPrompt.statusCode, 400);
    assert.equal(shortPrompt.header("access-control-allow-origin"), "https://research.autonomous-ai.io");
    assert.equal(JSON.parse(shortPrompt.body).error, "Prompt must be 10-2000 characters.");

    const blockedOrigin = await call(mockReq({
        method: "OPTIONS",
        origin: "https://evil.example",
    }));

    assert.equal(blockedOrigin.statusCode, 403);
    assert.equal(blockedOrigin.header("access-control-allow-origin"), undefined);

    console.log("Chat CORS validation passed.");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
