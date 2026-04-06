(function () {
    const backendBaseUrl = (window.APP_CONFIG && window.APP_CONFIG.BACKEND_BASE_URL || "").replace(/\/+$/, "");

    function buildBackendUrl(path) {
        if (!backendBaseUrl) return "#";
        return backendBaseUrl + path;
    }

    document.querySelectorAll("[data-backend-path]").forEach((element) => {
        element.setAttribute("href", buildBackendUrl(element.getAttribute("data-backend-path")));
    });

    document.querySelectorAll("[data-backend-origin]").forEach((element) => {
        element.textContent = backendBaseUrl || "your backend domain";
    });

    document.querySelectorAll("[data-hover-play]").forEach((video) => {
        const shell = video.closest(".video-shell");
        if (!shell) return;
        shell.addEventListener("mouseenter", function () {
            const playAttempt = video.play();
            if (playAttempt && typeof playAttempt.catch === "function") {
                playAttempt.catch(function () {});
            }
        });
        shell.addEventListener("mouseleave", function () {
            video.pause();
            video.currentTime = 0;
        });
    });
})();
