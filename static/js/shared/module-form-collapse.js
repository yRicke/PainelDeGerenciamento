(function () {
    var STORAGE_PREFIX = "module-form-collapsed:";

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function normalizeText(value) {
        return toText(value)
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    function toSlug(text) {
        return normalizeText(text)
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/(^-|-$)/g, "");
    }

    function readStorage(key) {
        try {
            return window.localStorage.getItem(key);
        } catch (_error) {
            return null;
        }
    }

    function writeStorage(key, value) {
        try {
            window.localStorage.setItem(key, value);
        } catch (_error) {
            // Storage can be unavailable in private browsing scenarios.
        }
    }

    function shouldEnhanceSection(section, headingText) {
        if (!section) return false;
        if (section.dataset.moduleFormCollapseOff === "1") return false;
        if (section.classList.contains("module-shell-side-panel")) return false;

        if (section.id === "sec-cadastro") return true;

        var normalizedHeading = normalizeText(headingText);
        if (!normalizedHeading) return false;

        return normalizedHeading.indexOf("cadastro") >= 0 || normalizedHeading.indexOf("novo") === 0;
    }

    function findHeading(section) {
        return section.querySelector(":scope > h2, :scope > h3");
    }

    function findPrimaryForm(section) {
        var forms = Array.from(section.querySelectorAll(":scope > form, form"));
        for (var i = 0; i < forms.length; i += 1) {
            var form = forms[i];
            if (!form) continue;
            if (form.classList.contains("upload-form") || form.classList.contains("auth-form")) continue;
            return form;
        }
        return null;
    }

    function resolveStorageKey(section, headingText) {
        var sectionToken = toText(section.id) || toSlug(headingText) || "section";
        return STORAGE_PREFIX + window.location.pathname + "::" + sectionToken;
    }

    function ensureBodyWrapper(section, headerRow) {
        var body = document.createElement("div");
        body.className = "module-form-collapsible-body";

        while (headerRow.nextSibling) {
            body.appendChild(headerRow.nextSibling);
        }

        section.appendChild(body);
        return body;
    }

    function bindSection(section) {
        if (!section || section.dataset.moduleFormCollapseBound === "1") return;

        var heading = findHeading(section);
        var form = findPrimaryForm(section);
        if (!heading || !form) return;

        var headingText = toText(heading.textContent);
        if (!shouldEnhanceSection(section, headingText)) return;

        var headerRow = document.createElement("div");
        headerRow.className = "module-form-collapse-head";
        section.insertBefore(headerRow, heading);
        headerRow.appendChild(heading);

        var toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "btn-light module-form-collapse-toggle";

        var indicator = document.createElement("span");
        indicator.className = "module-form-collapse-indicator";
        indicator.setAttribute("aria-hidden", "true");
        indicator.textContent = "▾";
        toggle.appendChild(indicator);

        var label = document.createElement("span");
        label.className = "module-form-collapse-label";
        toggle.appendChild(label);

        headerRow.appendChild(toggle);

        var body = ensureBodyWrapper(section, headerRow);
        var bodyId = "module-form-body-" + (section.id || toSlug(headingText) || String(Date.now()));
        body.id = bodyId;
        toggle.setAttribute("aria-controls", bodyId);

        var storageKey = resolveStorageKey(section, headingText);

        function setCollapsed(nextCollapsed, persist) {
            section.classList.toggle("is-form-collapsed", nextCollapsed);
            body.hidden = nextCollapsed;
            toggle.setAttribute("aria-expanded", nextCollapsed ? "false" : "true");
            label.textContent = nextCollapsed ? "Expandir cadastro" : "Minimizar cadastro";
            indicator.textContent = nextCollapsed ? "▸" : "▾";
            if (persist) {
                writeStorage(storageKey, nextCollapsed ? "1" : "0");
            }
        }

        var isInitiallyCollapsed = readStorage(storageKey) === "1";
        setCollapsed(isInitiallyCollapsed, false);

        toggle.addEventListener("click", function () {
            var collapsed = section.classList.contains("is-form-collapsed");
            setCollapsed(!collapsed, true);
        });

        section.dataset.moduleFormCollapseBound = "1";
    }

    function init() {
        var sections = document.querySelectorAll(".module-section");
        sections.forEach(bindSection);
    }

    init();
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    }
})();
