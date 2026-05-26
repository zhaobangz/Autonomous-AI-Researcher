(function () {
    const form = document.querySelector("#prompt-form");
    const promptInput = document.querySelector("#prompt");
    const tokenInput = document.querySelector("#access-token");
    const output = document.querySelector("#response-output");
    const statusPill = document.querySelector("#status-pill");
    const submitButton = document.querySelector("#submit-button");
    const clearButton = document.querySelector("#clear-button");
    const counter = document.querySelector("#prompt-count");
    const copyButton = document.querySelector("#copy-button");
    const charBarFill = document.querySelector(".char-bar-fill");

    const TOKEN_STORAGE_KEY = "air_site_access_token";
    const siteConfig = window.AIR_SITE_CONFIG || {};
    const chatEndpoint = typeof siteConfig.chatEndpoint === "string"
        ? siteConfig.chatEndpoint.trim()
        : "";
    let copyResetId;

    function setStatus(label, isError) {
        statusPill.textContent = label;
        statusPill.classList.toggle("error", Boolean(isError));
    }

    function updateCounter() {
        const maxLength = promptInput.maxLength || 2000;
        const percentage = Math.min(100, (promptInput.value.length / maxLength) * 100);

        counter.textContent = `${promptInput.value.length} / ${promptInput.maxLength}`;
        charBarFill.style.width = `${percentage}%`;
        charBarFill.dataset.level = percentage > 95
            ? "danger"
            : percentage > 80
                ? "warn"
                : "safe";
    }

    function setBusy(isBusy) {
        submitButton.disabled = isBusy;
        submitButton.textContent = isBusy ? "Running..." : "Run prompt";
    }

    function resetCopyButton() {
        window.clearTimeout(copyResetId);
        copyButton.textContent = "Copy";
    }

    function savedAccessToken() {
        try {
            return window.localStorage.getItem(TOKEN_STORAGE_KEY) || "";
        } catch (_error) {
            return "";
        }
    }

    function saveAccessToken(value) {
        try {
            if (value) {
                window.localStorage.setItem(TOKEN_STORAGE_KEY, value);
            } else {
                window.localStorage.removeItem(TOKEN_STORAGE_KEY);
            }
        } catch (_error) {
            // Ignore private browsing or restricted storage failures.
        }
    }

    async function runPrompt(prompt, accessToken) {
        if (!chatEndpoint) {
            throw new Error("This GitHub Pages site is static. Configure assets/js/config.js with a hosted chat endpoint before accepting prompts.");
        }

        const headers = {
            "Content-Type": "application/json",
        };

        if (accessToken) {
            headers["X-Site-Access-Token"] = accessToken;
        }

        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), 30000);

        try {
            const response = await fetch(chatEndpoint, {
                method: "POST",
                headers,
                body: JSON.stringify({ prompt }),
                signal: controller.signal,
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.error || "The request failed.");
            }
            return data;
        } finally {
            window.clearTimeout(timeoutId);
        }
    }

    tokenInput.value = savedAccessToken();
    updateCounter();

    promptInput.addEventListener("input", updateCounter);

    copyButton.addEventListener("click", async function () {
        try {
            await navigator.clipboard.writeText(output.textContent || "");
            copyButton.textContent = "Copied!";
            window.clearTimeout(copyResetId);
            copyResetId = window.setTimeout(resetCopyButton, 2000);
        } catch (_error) {
            copyButton.textContent = "Copy failed";
            window.clearTimeout(copyResetId);
            copyResetId = window.setTimeout(resetCopyButton, 2000);
        }
    });

    clearButton.addEventListener("click", function () {
        promptInput.value = "";
        output.textContent = "Awaiting research brief.";
        setStatus("Ready", false);
        updateCounter();
        resetCopyButton();
        promptInput.focus();
    });

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        const prompt = promptInput.value.trim();
        const accessToken = tokenInput.value.trim();

        if (prompt.length < 10) {
            setStatus("Error", true);
            output.textContent = "Use at least 10 characters.";
            return;
        }

        saveAccessToken(accessToken);
        setBusy(true);
        setStatus("Thinking...", false);
        resetCopyButton();
        output.textContent = "Generating research brief...";

        try {
            const data = await runPrompt(prompt, accessToken);
            output.textContent = data.output || "No text was returned.";
            setStatus(data.model || "Complete", false);
        } catch (error) {
            const message = error.name === "AbortError"
                ? "The request timed out."
                : error.message;
            output.textContent = message;
            setStatus("Error", true);
        } finally {
            setBusy(false);
        }
    });
}());
