(function () {
    const form = document.querySelector("#prompt-form");
    const promptInput = document.querySelector("#prompt");
    const tokenInput = document.querySelector("#access-token");
    const output = document.querySelector("#response-output");
    const statusPill = document.querySelector("#status-pill");
    const submitButton = document.querySelector("#submit-button");
    const clearButton = document.querySelector("#clear-button");
    const counter = document.querySelector("#prompt-count");

    const TOKEN_STORAGE_KEY = "air_site_access_token";

    function setStatus(label, isError) {
        statusPill.textContent = label;
        statusPill.classList.toggle("error", Boolean(isError));
    }

    function updateCounter() {
        counter.textContent = `${promptInput.value.length} / ${promptInput.maxLength}`;
    }

    function setBusy(isBusy) {
        submitButton.disabled = isBusy;
        submitButton.textContent = isBusy ? "Running..." : "Run prompt";
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
        const headers = {
            "Content-Type": "application/json",
        };

        if (accessToken) {
            headers["X-Site-Access-Token"] = accessToken;
        }

        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), 30000);

        try {
            const response = await fetch("/api/chat", {
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

    clearButton.addEventListener("click", function () {
        promptInput.value = "";
        output.textContent = "Awaiting research brief.";
        setStatus("Ready", false);
        updateCounter();
        promptInput.focus();
    });

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        const prompt = promptInput.value.trim();
        const accessToken = tokenInput.value.trim();

        if (prompt.length < 10) {
            setStatus("Prompt too short", true);
            output.textContent = "Use at least 10 characters.";
            return;
        }

        saveAccessToken(accessToken);
        setBusy(true);
        setStatus("Running", false);
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
