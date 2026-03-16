(function () {
    var MOBILE_MENU_QUERY = "(max-width: 1600px)";
    var shell = document.querySelector(".nav-shell");
    if (!shell) return;

    var toggle = shell.querySelector(".nav-toggle");
    var panel = shell.querySelector(".nav-panel");
    var header = document.querySelector(".site-header");
    if (!toggle || !panel || !header) return;

    var mobileMenuMedia = window.matchMedia(MOBILE_MENU_QUERY);
    var frameRequested = false;

    function isMobileViewport() {
        return mobileMenuMedia.matches;
    }

    function syncPanelAccessibility() {
        if (isMobileViewport()) {
            panel.setAttribute("aria-hidden", shell.classList.contains("is-menu-open") ? "false" : "true");
            return;
        }
        panel.setAttribute("aria-hidden", "false");
    }

    function syncHeaderHeight() {
        if (frameRequested) return;
        frameRequested = true;

        window.requestAnimationFrame(function () {
            frameRequested = false;
            var headerHeight = Math.ceil(header.getBoundingClientRect().height || 0);
            if (headerHeight > 0) {
                document.documentElement.style.setProperty("--site-header-height", headerHeight + "px");
            }
        });
    }

    function openMenu() {
        shell.classList.add("is-menu-open");
        toggle.setAttribute("aria-expanded", "true");
        syncPanelAccessibility();
        syncHeaderHeight();
    }

    function closeMenu() {
        shell.classList.remove("is-menu-open");
        toggle.setAttribute("aria-expanded", "false");
        syncPanelAccessibility();
        syncHeaderHeight();
    }

    toggle.addEventListener("click", function () {
        if (shell.classList.contains("is-menu-open")) {
            closeMenu();
            return;
        }
        openMenu();
    });

    document.addEventListener("click", function (event) {
        if (!isMobileViewport()) return;
        if (!shell.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMenu();
        }
    });

    panel.querySelectorAll("a[href]").forEach(function (link) {
        link.addEventListener("click", function () {
            if (isMobileViewport()) {
                closeMenu();
            }
        });
    });

    window.addEventListener("resize", function () {
        if (!isMobileViewport()) {
            closeMenu();
        } else {
            syncPanelAccessibility();
        }
        syncHeaderHeight();
    });

    if (typeof mobileMenuMedia.addEventListener === "function") {
        mobileMenuMedia.addEventListener("change", function () {
            if (!isMobileViewport()) {
                closeMenu();
            } else {
                syncPanelAccessibility();
            }
            syncHeaderHeight();
        });
    } else if (typeof mobileMenuMedia.addListener === "function") {
        mobileMenuMedia.addListener(function () {
            if (!isMobileViewport()) {
                closeMenu();
            } else {
                syncPanelAccessibility();
            }
            syncHeaderHeight();
        });
    }

    window.addEventListener("orientationchange", syncHeaderHeight);

    closeMenu();
    syncHeaderHeight();
})();
