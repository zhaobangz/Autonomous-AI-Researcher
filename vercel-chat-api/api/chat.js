const crypto = require("node:crypto");

const OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses";
const MAX_PROMPT_LENGTH = 2000;
const MIN_PROMPT_LENGTH = 10;
const REQUEST_TIMEOUT_MS = 25000;
const RATE_LIMIT_WINDOW_MS = 60000;
const RATE_LIMIT_MAX = Number.parseInt(process.env.SITE_RATE_LIMIT_PER_MINUTE || "6", 10);

const buckets = globalThis.__airRateLimitBuckets || new Map();
globalThis.__airRateLimitBuckets = buckets;

function setSecurityHeaders(res) {
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
}

function json(res, statusCode, payload) {
    setSecurityHeaders(res);
    res.statusCode = statusCode;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(payload));
}

function clientIp(req) {
    const forwardedFor = req.headers["x-forwarded-for"];
    if (typeof forwardedFor === "string" && forwardedFor.length > 0) {
        return forwardedFor.split(",")[0].trim();
    }
    return req.socket?.remoteAddress || "unknown";
}

function isRateLimited(req) {
    const now = Date.now();
    const key = clientIp(req);
    const bucket = (buckets.get(key) || []).filter((timestamp) => now - timestamp < RATE_LIMIT_WINDOW_MS);

    if (bucket.length >= RATE_LIMIT_MAX) {
        buckets.set(key, bucket);
        return true;
    }

    bucket.push(now);
    buckets.set(key, bucket);

    if (buckets.size > 1000) {
        for (const [bucketKey, timestamps] of buckets.entries()) {
            if (!timestamps.some((timestamp) => now - timestamp < RATE_LIMIT_WINDOW_MS)) {
                buckets.delete(bucketKey);
            }
        }
    }

    return false;
}

function safeCompare(a, b) {
    const normalize = (value) => Array.isArray(value) ? value[0] || "" : value || "";
    const left = crypto.createHash("sha256").update(normalize(a), "utf8").digest();
    const right = crypto.createHash("sha256").update(normalize(b), "utf8").digest();
    return crypto.timingSafeEqual(left, right);
}

function configuredOrigins(req) {
    const origins = new Set([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]);

    const host = req.headers.host;
    const proto = req.headers["x-forwarded-proto"] || (host && host.includes("localhost") ? "http" : "https");
    if (host) {
        origins.add(`${proto}://${host}`);
    }

    if (process.env.VERCEL_URL) {
        origins.add(`https://${process.env.VERCEL_URL}`);
    }

    for (const origin of (process.env.PUBLIC_SITE_ORIGIN || "").split(",")) {
        const trimmed = origin.trim();
        if (trimmed) {
            origins.add(trimmed);
        }
    }

    return origins;
}

function hasAllowedOrigin(req) {
    const origin = req.headers.origin;
    if (!origin) {
        return true;
    }
    return configuredOrigins(req).has(origin);
}

async function readJsonBody(req) {
    if (req.body && typeof req.body === "object") {
        return req.body;
    }

    if (typeof req.body === "string") {
        return JSON.parse(req.body);
    }

    const chunks = [];
    for await (const chunk of req) {
        chunks.push(Buffer.from(chunk));
        if (Buffer.concat(chunks).length > 8192) {
            throw new Error("Request body too large.");
        }
    }

    const raw = Buffer.concat(chunks).toString("utf8");
    return raw ? JSON.parse(raw) : {};
}

function hasJsonContentType(req) {
    const contentType = req.headers["content-type"];
    if (typeof contentType !== "string") {
        return false;
    }
    return contentType.toLowerCase().split(";")[0].trim() === "application/json";
}

function extractText(data) {
    if (typeof data.output_text === "string" && data.output_text.trim()) {
        return data.output_text.trim();
    }

    const parts = [];
    for (const item of data.output || []) {
        for (const content of item.content || []) {
            if (content.type === "output_text" && content.text) {
                parts.push(content.text);
            }
        }
    }
    return parts.join("\n").trim();
}

async function callOpenAI(prompt) {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
        const error = new Error("OPENAI_API_KEY is not configured.");
        error.statusCode = 500;
        throw error;
    }

    const model = process.env.OPENAI_MODEL || process.env.LLM_MODEL || "gpt-4o-mini";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
        const response = await fetch(OPENAI_RESPONSES_URL, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${apiKey}`,
                "Content-Type": "application/json",
            },
            signal: controller.signal,
            body: JSON.stringify({
                model,
                store: false,
                max_output_tokens: 700,
                temperature: 0.2,
                instructions: [
                    "You are the public prompt endpoint for the Autonomous AI Researcher project.",
                    "Return a concise research brief with: Summary, Research Plan, Critical Risks, and Next Step.",
                    "Do not claim that live literature searches, paper downloads, code execution, or experiments were performed.",
                ].join("\n"),
                input: [
                    {
                        role: "user",
                        content: [
                            {
                                type: "input_text",
                                text: prompt,
                            },
                        ],
                    },
                ],
            }),
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const error = new Error(data.error?.message || "OpenAI request failed.");
            error.statusCode = response.status;
            throw error;
        }

        return {
            output: extractText(data),
            model,
            usage: data.usage || null,
        };
    } finally {
        clearTimeout(timeout);
    }
}

module.exports = async function handler(req, res) {
    if (req.method !== "POST") {
        res.setHeader("Allow", "POST");
        return json(res, 405, { error: "Method not allowed." });
    }

    if (!hasAllowedOrigin(req)) {
        return json(res, 403, { error: "Origin not allowed." });
    }

    if (isRateLimited(req)) {
        return json(res, 429, { error: "Rate limit exceeded. Try again shortly." });
    }

    if (!hasJsonContentType(req)) {
        return json(res, 415, { error: "Content-Type must be application/json." });
    }

    const expectedToken = process.env.SITE_ACCESS_TOKEN;
    if (expectedToken) {
        const providedToken = req.headers["x-site-access-token"];
        if (!safeCompare(providedToken, expectedToken)) {
            return json(res, 401, { error: "Access code required." });
        }
    }

    let body;
    try {
        body = await readJsonBody(req);
    } catch (_error) {
        return json(res, 400, { error: "Invalid JSON body." });
    }

    const prompt = typeof body.prompt === "string" ? body.prompt.trim() : "";
    if (prompt.length < MIN_PROMPT_LENGTH || prompt.length > MAX_PROMPT_LENGTH) {
        return json(res, 400, { error: `Prompt must be ${MIN_PROMPT_LENGTH}-${MAX_PROMPT_LENGTH} characters.` });
    }

    try {
        const result = await callOpenAI(prompt);
        return json(res, 200, result);
    } catch (error) {
        const status = error.statusCode && error.statusCode < 500 ? 502 : 500;
        console.error("OpenAI route error:", {
            statusCode: error.statusCode || 500,
            message: error.message,
        });
        return json(res, status, { error: "The AI service is unavailable right now." });
    }
};
