(function () {
    window.AIR_SITE_CONFIG = {
        // GitHub Pages is static and cannot run /api/chat.
        // Set this to a separately hosted HTTPS chat endpoint to enable submissions.
        chatEndpoint: "https://autonomous-ai-researcher-chat-api.vercel.app/api/chat",
        // Set demoVideoSrc to an MP4/WebM file, or demoEmbedUrl to a hosted embed URL.
        demoVideoSrc: "assets/media/demo.mp4",
        demoPosterSrc: "",
        demoEmbedUrl: "",
    };
}());
