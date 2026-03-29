(function () {
    var MOBILE_TOOLBAR_QUERY = "(max-width: 1100px)";
    var toolbarSpacingBound = false;
    var toolbarSpacingScheduled = false;
    var requestAnimationFrameSafe = window.requestAnimationFrame || function (callback) {
        return window.setTimeout(callback, 16);
    };
    var toolbarResizeObserver = typeof window.ResizeObserver === "function"
        ? new window.ResizeObserver(scheduleToolbarSpacingSync)
        : null;

    var MODULE_LABELS = {
        comercial: "Modulo Comercial",
        financeiro: "Modulo Financeiro",
        operacional: "Modulo Operacional",
        administrativo: "Modulo Administrativo",
        parametros: "Modulo Parametros",
    };

    function toSlug(text) {
        return String(text || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/(^-|-$)/g, "");
    }

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

    function detectModuleToken(value) {
        var normalized = normalizeText(value).replace(/[^a-z0-9]+/g, " ").trim();
        if (!normalized) return "";

        var tokens = normalized.split(/\s+/);
        for (var i = 0; i < tokens.length; i += 1) {
            if (MODULE_LABELS[tokens[i]]) {
                return tokens[i];
            }
        }

        return "";
    }

    function listToSentence(items) {
        var valid = (Array.isArray(items) ? items : []).filter(Boolean);
        if (!valid.length) return "";
        if (valid.length === 1) return valid[0];
        if (valid.length === 2) return valid[0] + " e " + valid[1];
        return valid.slice(0, -1).join(", ") + " e " + valid[valid.length - 1];
    }

    function detectModuleLabel(backLink) {
        var path = String(window.location.pathname || "");
        var parts = path.split("/").filter(Boolean);

        for (var i = 0; i < parts.length; i += 1) {
            var pathToken = detectModuleToken(parts[i]);
            if (pathToken) return MODULE_LABELS[pathToken];
        }

        var activeNavLink = document.querySelector(".nav-links a.is-active, .nav-links a[aria-current='page']");
        var activeNavToken = detectModuleToken(activeNavLink && activeNavLink.textContent);
        if (activeNavToken) return MODULE_LABELS[activeNavToken];

        var backHrefToken = detectModuleToken(backLink && backLink.getAttribute("href"));
        if (backHrefToken) return MODULE_LABELS[backHrefToken];

        var backTextToken = detectModuleToken(backLink && backLink.textContent);
        if (backTextToken) return MODULE_LABELS[backTextToken];

        return "Modulo";
    }

    function extractCompanyFromText(text) {
        var raw = toText(text);
        if (!raw) return "";
        var match = raw.match(/^empresa\s*[:\-]\s*(.+)$/i);
        if (!match || !match[1]) return "";
        return toText(match[1]);
    }

    function buildHeroSubtitle(explicitSubtitle, heroNav) {
        if (toText(explicitSubtitle)) {
            return toText(explicitSubtitle);
        }

        var parts = [];
        if (heroNav && heroNav.querySelector('a[href="#sec-cadastro"]')) {
            parts.push("cadastro");
        }
        if (heroNav && heroNav.querySelector('a[href="#sec-importacao"]')) {
            parts.push("importacao");
        }
        parts.push("filtros");
        if (heroNav && heroNav.querySelector('a[href="#sec-dashboard"]')) {
            parts.push("dashboard");
        }
        if (heroNav && heroNav.querySelector('a[href="#sec-visualizacao"]')) {
            parts.push("tabela");
        }

        var sentenceItems = listToSentence(parts);
        if (sentenceItems) {
            return "Visualizacao central de " + sentenceItems + ".";
        }
        return "Visualizacao central do modulo.";
    }

    function ensureToolbarNav(heroNav) {
        var nav = heroNav ? heroNav.cloneNode(true) : document.createElement("nav");
        nav.classList.add("module-sections-nav");

        if (!nav.getAttribute("aria-label")) {
            nav.setAttribute("aria-label", "Navegacao de secoes do modulo");
        }

        if (!nav.querySelector('a[href="#sec-filtros"]')) {
            var filterLink = document.createElement("a");
            filterLink.href = "#sec-filtros";
            filterLink.className = "module-sections-nav-mobile-filters";
            filterLink.textContent = "Filtros";

            var dashboardLink = nav.querySelector('a[href="#sec-dashboard"]');
            if (dashboardLink && dashboardLink.parentNode === nav) {
                nav.insertBefore(filterLink, dashboardLink);
            } else {
                nav.appendChild(filterLink);
            }
        }

        return nav;
    }

    function ensureHeroGrid(hero) {
        if (!hero) return {grid: null, main: null};
        hero.classList.add("module-hero-shell");

        var grid = hero.querySelector(":scope > .module-hero-grid");
        var main = hero.querySelector(":scope > .module-hero-grid > .module-hero-main");
        if (grid && main) {
            return {grid: grid, main: main};
        }

        grid = document.createElement("div");
        grid.className = "module-hero-grid";
        grid.classList.add("module-hero-grid--single");

        main = document.createElement("div");
        main.className = "module-hero-main";

        while (hero.firstChild) {
            main.appendChild(hero.firstChild);
        }

        grid.appendChild(main);
        hero.appendChild(grid);
        return {grid: grid, main: main};
    }

    function findMainBackLink(main) {
        if (!main) return null;
        var links = Array.from(main.querySelectorAll("a[href]"));
        for (var i = 0; i < links.length; i += 1) {
            var link = links[i];
            if (link.closest(".module-sections-nav")) continue;
            return link;
        }
        return null;
    }

    function extractHeroContent(main) {
        if (!main) {
            return {
                title: "",
                subtitle: "",
                company: "",
                backLink: null,
            };
        }

        var titleEl = main.querySelector("h1");
        var title = toText(titleEl && titleEl.textContent);

        var subtitle = "";
        var company = "";
        var paragraphs = Array.from(main.querySelectorAll("p"));
        paragraphs.forEach(function (paragraph) {
            var text = toText(paragraph.textContent);
            if (!text) return;

            var extractedCompany = extractCompanyFromText(text);
            if (extractedCompany && !company) {
                company = extractedCompany;
                return;
            }

            if (!subtitle) {
                subtitle = text;
            }
        });

        return {
            title: title,
            subtitle: subtitle,
            company: company,
            backLink: findMainBackLink(main),
        };
    }

    function standardizeHeroMain(main, heroNav, hero) {
        if (!main || !hero) return;
        if (main.dataset.heroStandardized === "1") return;
        if (hero.classList.contains("vendas-hero")) return;

        var content = extractHeroContent(main);
        var moduleLabel = detectModuleLabel(content.backLink);
        var heroTitle = content.title || document.title || "Modulo";
        var subtitle = buildHeroSubtitle(content.subtitle, heroNav);

        main.innerHTML = "";

        var topLine = document.createElement("div");
        topLine.className = "module-hero-topline";

        if (content.backLink) {
            var backLink = content.backLink.cloneNode(true);
            backLink.classList.add("module-hero-back-link");
            topLine.appendChild(backLink);
        }

        var modulePill = document.createElement("span");
        modulePill.className = "module-hero-pill";
        modulePill.textContent = moduleLabel;
        topLine.appendChild(modulePill);
        main.appendChild(topLine);

        var titleEl = document.createElement("h1");
        titleEl.textContent = heroTitle;
        main.appendChild(titleEl);

        var subtitleEl = document.createElement("p");
        subtitleEl.className = "module-hero-subtitle";
        subtitleEl.textContent = subtitle;
        main.appendChild(subtitleEl);

        if (content.company) {
            var facts = document.createElement("dl");
            facts.className = "module-hero-facts";

            var companyBox = document.createElement("div");
            var companyTitle = document.createElement("dt");
            companyTitle.textContent = "Empresa";
            var companyValue = document.createElement("dd");
            companyValue.textContent = content.company;

            companyBox.appendChild(companyTitle);
            companyBox.appendChild(companyValue);
            facts.appendChild(companyBox);
            main.appendChild(facts);
        }

        main.dataset.heroStandardized = "1";
    }

    function bindSidebarToggles() {
        function applySidebarState(shell, toggle, collapse) {
            if (!shell || !toggle) return;
            shell.classList.toggle("is-sidebar-collapsed", Boolean(collapse));
            toggle.setAttribute("aria-expanded", collapse ? "false" : "true");
        }

        function initializeSidebarState(shell, toggle) {
            if (!shell || !toggle) return;
            if (shell.dataset.moduleSidebarStateInitialized === "1") {
                applySidebarState(shell, toggle, shell.classList.contains("is-sidebar-collapsed"));
                return;
            }
            // Desktop inicia com o menu de filtros fechado por padrao.
            var shouldCollapse = !window.matchMedia("(max-width: 1100px)").matches;
            applySidebarState(shell, toggle, shouldCollapse);
            shell.dataset.moduleSidebarStateInitialized = "1";
        }

        var toggles = document.querySelectorAll(".module-shell-toggle[aria-controls]");
        toggles.forEach(function (toggle) {
            if (toggle.dataset.boundModuleShellToggle === "1") return;
            toggle.dataset.boundModuleShellToggle = "1";
            initializeSidebarState(toggle.closest(".module-shell"), toggle);

            toggle.addEventListener("click", function () {
                var shell = toggle.closest(".module-shell");
                if (!shell || window.matchMedia("(max-width: 1100px)").matches) return;

                var collapse = !shell.classList.contains("is-sidebar-collapsed");
                applySidebarState(shell, toggle, collapse);
            });
        });
    }

    function findMainToolbar(main) {
        if (!main || !main.children) return null;
        for (var i = 0; i < main.children.length; i += 1) {
            var child = main.children[i];
            if (child.classList && child.classList.contains("module-shell-main-toolbar")) {
                return child;
            }
        }
        return null;
    }

    function syncModuleShellToolbarSpacing() {
        var isSmallScreen = window.matchMedia(MOBILE_TOOLBAR_QUERY).matches;
        var mains = document.querySelectorAll(".module-shell-main");

        mains.forEach(function (main) {
            var toolbar = findMainToolbar(main);
            if (!toolbar) return;

            if (!isSmallScreen) {
                main.style.removeProperty("--module-shell-main-toolbar-space");
                return;
            }

            var computedStyle = window.getComputedStyle(toolbar);
            var marginBottom = parseFloat(computedStyle.marginBottom) || 0;
            var spacing = Math.ceil(toolbar.getBoundingClientRect().height + marginBottom + 10);
            main.style.setProperty("--module-shell-main-toolbar-space", spacing + "px");
        });
    }

    function scheduleToolbarSpacingSync() {
        if (toolbarSpacingScheduled) return;
        toolbarSpacingScheduled = true;

        requestAnimationFrameSafe(function () {
            toolbarSpacingScheduled = false;
            syncModuleShellToolbarSpacing();
        });
    }

    function observeToolbarResizes() {
        if (!toolbarResizeObserver) return;

        var toolbars = document.querySelectorAll(".module-shell-main-toolbar");
        toolbars.forEach(function (toolbar) {
            if (toolbar.dataset.moduleShellToolbarObserved === "1") return;
            toolbar.dataset.moduleShellToolbarObserved = "1";
            toolbarResizeObserver.observe(toolbar);
        });
    }

    function bindModuleShellToolbarSpacing() {
        observeToolbarResizes();
        scheduleToolbarSpacingSync();

        if (toolbarSpacingBound) return;
        toolbarSpacingBound = true;

        window.addEventListener("resize", scheduleToolbarSpacingSync);
        window.addEventListener("orientationchange", scheduleToolbarSpacingSync);

        var mediaQuery = window.matchMedia(MOBILE_TOOLBAR_QUERY);
        if (typeof mediaQuery.addEventListener === "function") {
            mediaQuery.addEventListener("change", scheduleToolbarSpacingSync);
        } else if (typeof mediaQuery.addListener === "function") {
            mediaQuery.addListener(scheduleToolbarSpacingSync);
        }
    }

    function createFiltersPanel() {
        var section = document.createElement("section");
        section.id = "sec-filtros";
        section.className = "panel module-section module-shell-side-panel";

        var head = document.createElement("div");
        head.className = "module-shell-side-panel-head";

        var title = document.createElement("h2");
        title.textContent = "Filtros";
        head.appendChild(title);

        var clearButton = document.createElement("button");
        clearButton.type = "button";
        clearButton.className = "btn-light module-filters-clear-all";
        clearButton.textContent = "Limpar filtros";
        head.appendChild(clearButton);
        section.appendChild(head);

        var note = document.createElement("p");
        note.className = "form-note module-filters-placeholder";
        note.textContent = "Filtros multisselecao aplicados junto com os filtros da tabela.";
        section.appendChild(note);

        var columns = document.createElement("div");
        columns.className = "module-filter-columns";

        var leftColumn = document.createElement("div");
        leftColumn.className = "module-filter-column";
        leftColumn.setAttribute("data-module-filter-column", "left");

        var rightColumn = document.createElement("div");
        rightColumn.className = "module-filter-column";
        rightColumn.setAttribute("data-module-filter-column", "right");

        columns.appendChild(leftColumn);
        columns.appendChild(rightColumn);
        section.appendChild(columns);

        return section;
    }

    function resolveImportBadgeText(importSection) {
        if (!importSection || typeof importSection.querySelector !== "function") return ".xls";
        var fileInput = importSection.querySelector('input[type="file"][accept]');
        var accept = toText(fileInput && fileInput.getAttribute("accept"));
        if (!accept) return ".xls";

        var firstToken = "";
        accept.split(",").some(function (token) {
            var normalized = toText(token);
            if (!normalized) return false;
            firstToken = normalized;
            return true;
        });

        return firstToken || ".xls";
    }

    function sanitizeAcceptToken(token) {
        return toText(token).toLowerCase().replace(/[^a-z0-9.+-]/g, "");
    }

    function resolveImportAcceptTokens(importSection) {
        if (!importSection || typeof importSection.querySelector !== "function") return [];
        var fileInput = importSection.querySelector('input[type="file"][accept]');
        var accept = toText(fileInput && fileInput.getAttribute("accept"));
        if (!accept) return [];

        var tokens = [];
        accept.split(",").forEach(function (rawToken) {
            var token = sanitizeAcceptToken(rawToken);
            if (!token) return;
            if (tokens.indexOf(token) >= 0) return;
            tokens.push(token);
        });
        return tokens;
    }

    function buildAcceptHtml(tokens) {
        var validTokens = Array.isArray(tokens) ? tokens.filter(Boolean) : [];
        if (!validTokens.length) return "<code>arquivo</code>";
        if (validTokens.length === 1) return "<code>" + validTokens[0] + "</code>";

        var html = "";
        validTokens.forEach(function (token, index) {
            if (index > 0) {
                html += index === validTokens.length - 1 ? " e " : ", ";
            }
            html += "<code>" + token + "</code>";
        });
        return html;
    }

    function detectNestedImport(importSection, fileInput) {
        if (importSection && normalizeText(importSection.dataset.importNested) === "true") return true;
        if (fileInput && normalizeText(fileInput.dataset.importNested) === "true") return true;
        if (!importSection || typeof importSection.querySelectorAll !== "function") return false;

        var notes = importSection.querySelectorAll(":scope > p:not(.file-status)");
        for (var i = 0; i < notes.length; i += 1) {
            if (normalizeText(notes[i].textContent).indexOf("subpasta") >= 0) return true;
        }
        return false;
    }

    function buildImportNote(importSection) {
        if (!importSection || typeof importSection.querySelector !== "function") return "";
        var fileInput = importSection.querySelector('input[type="file"]');
        if (!fileInput) return "";

        var hasDirectorySelection = fileInput.hasAttribute("webkitdirectory") || fileInput.hasAttribute("directory");
        var isMultipleFiles = fileInput.hasAttribute("multiple");
        var acceptHtml = buildAcceptHtml(resolveImportAcceptTokens(importSection));
        var hasNestedFolders = detectNestedImport(importSection, fileInput);

        if (hasDirectorySelection) {
            if (hasNestedFolders) {
                return "Pasta com subpastas contendo arquivos " + acceptHtml + ".";
            }
            return "Pasta com arquivos " + acceptHtml + ".";
        }

        if (isMultipleFiles) {
            return "Selecione arquivos " + acceptHtml + ".";
        }

        return "Arquivo " + acceptHtml + ".";
    }

    function ensureImportNote(importSection) {
        if (!importSection) return;

        var noteText = buildImportNote(importSection);
        if (!noteText) return;

        var notes = Array.from(importSection.querySelectorAll(":scope > p:not(.file-status)"));
        var primaryNote = notes.length ? notes[0] : null;
        if (primaryNote && toText(primaryNote.textContent)) {
            primaryNote.classList.add("form-note");
            return;
        }

        if (!primaryNote) {
            primaryNote = document.createElement("p");
            var uploadForm = importSection.querySelector(":scope > form.upload-form");
            if (uploadForm) {
                importSection.insertBefore(primaryNote, uploadForm);
            } else {
                importSection.appendChild(primaryNote);
            }
        }

        primaryNote.classList.add("form-note");
        primaryNote.innerHTML = noteText;
    }

    function ensureImportHeader(importSection) {
        if (!importSection) return;

        var title = importSection.querySelector(":scope > h2");
        if (!title) return;

        var head = importSection.querySelector(":scope > .module-hero-import-head");

        if (!head) {
            head = document.createElement("div");
            head.className = "module-hero-import-head";
            importSection.insertBefore(head, title);
            head.appendChild(title);
        } else if (!head.classList.contains("module-hero-import-head")) {
            head.classList.add("module-hero-import-head");
        }

        var badge = head.querySelector(".module-hero-import-badge");
        if (!badge) {
            badge = document.createElement("span");
            badge.className = "module-hero-import-badge";
            badge.textContent = resolveImportBadgeText(importSection);
            head.appendChild(badge);
        } else if (!toText(badge.textContent)) {
            badge.textContent = resolveImportBadgeText(importSection);
        }
    }

    function ensureImportSummary(importSection) {
        if (!importSection) return;

        var summaries = Array.from(importSection.querySelectorAll(":scope > p.file-status"));
        if (!summaries.length) return;

        var wrapper = importSection.querySelector(":scope > .importacao-resumo");
        var uploadForm = importSection.querySelector(":scope > form.upload-form");

        if (!wrapper) {
            wrapper = document.createElement("div");
            wrapper.className = "importacao-resumo";
            if (uploadForm) {
                importSection.insertBefore(wrapper, uploadForm);
            } else {
                importSection.appendChild(wrapper);
            }
        }

        summaries.forEach(function (summary) {
            wrapper.appendChild(summary);
        });
    }

    function enhanceImportSection(importSection) {
        if (!importSection || importSection.dataset.importSectionEnhanced === "1") return;

        importSection.classList.add("module-hero-import");
        ensureImportNote(importSection);
        ensureImportHeader(importSection);
        ensureImportSummary(importSection);

        importSection.querySelectorAll("form.upload-form button[type='submit']").forEach(function (button) {
            button.classList.add("upload-button");
        });

        importSection.dataset.importSectionEnhanced = "1";
    }

    function moveImportToHero(hero, heroStructure) {
        var importSection = document.getElementById("sec-importacao");
        if (!importSection || importSection.closest(".page-hero") === hero) return;

        var structure = heroStructure || ensureHeroGrid(hero);
        if (!structure || !structure.grid) return;

        enhanceImportSection(importSection);
        importSection.classList.remove("panel");
        structure.grid.classList.remove("module-hero-grid--single");
        structure.grid.appendChild(importSection);
    }

    function ensureShellFiltersPanel(sidebar) {
        var existingFilters = document.getElementById("sec-filtros");
        if (existingFilters && !existingFilters.closest(".page-hero")) {
            existingFilters.classList.add("module-shell-side-panel");
            sidebar.appendChild(existingFilters);
            return existingFilters;
        }

        var created = createFiltersPanel();
        sidebar.appendChild(created);
        return created;
    }

    function isModuleShellUpgradeDisabled() {
        var body = document.body;
        if (body && body.hasAttribute("data-module-shell-upgrade-off")) {
            return true;
        }
        return Boolean(document.querySelector(".page-hero[data-module-shell-upgrade-off]"));
    }

    function upgradeModuleLayout() {
        if (isModuleShellUpgradeDisabled()) {
            if (document.querySelector(".module-shell")) {
                bindSidebarToggles();
                bindModuleShellToolbarSpacing();
            }
            return;
        }

        enhanceImportSection(document.getElementById("sec-importacao"));

        if (document.querySelector(".module-shell")) {
            bindSidebarToggles();
            bindModuleShellToolbarSpacing();
            return;
        }

        var hero = document.querySelector(".page-hero");
        if (!hero) return;

        var heroNav = hero.querySelector(".module-sections-nav");
        if (!heroNav) return;

        var toolbarNav = ensureToolbarNav(heroNav);
        var heroStructure = ensureHeroGrid(hero);
        standardizeHeroMain(heroStructure.main, heroNav, hero);
        moveImportToHero(hero, heroStructure);

        var sections = Array.from(document.querySelectorAll(".module-section")).filter(function (section) {
            return !section.closest(".page-hero");
        });
        if (!sections.length) return;

        var titleEl = hero.querySelector("h1");
        var shellId = (toSlug(titleEl ? titleEl.textContent : "modulo") || "modulo") + "-module-shell";
        var sidebarId = shellId + "-sidebar";

        var shell = document.createElement("div");
        shell.id = shellId;
        shell.className = "module-shell is-sidebar-collapsed";
        shell.dataset.moduleShellUpgraded = "1";

        var sidebar = document.createElement("aside");
        sidebar.id = sidebarId;
        sidebar.className = "module-shell-sidebar";
        sidebar.setAttribute("aria-label", "Painel lateral de filtros");

        var filtersPanel = ensureShellFiltersPanel(sidebar);
        sections = sections.filter(function (section) {
            return section !== filtersPanel;
        });

        var main = document.createElement("div");
        main.className = "module-shell-main";

        var toolbar = document.createElement("div");
        toolbar.className = "module-shell-main-toolbar";

        var toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "module-shell-toggle";
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-controls", sidebarId);
        toggle.innerHTML = '<span aria-hidden="true">&#9776;</span><span>Menu de filtros</span>';
        toolbar.appendChild(toggle);

        toolbar.appendChild(toolbarNav);

        var clearToolbarButton = document.createElement("button");
        clearToolbarButton.type = "button";
        clearToolbarButton.className = "btn-light module-shell-clear-filters";
        clearToolbarButton.textContent = "Limpar todos os filtros";
        toolbar.appendChild(clearToolbarButton);

        if (heroNav.parentNode) {
            heroNav.remove();
        }

        main.appendChild(toolbar);
        sections.forEach(function (section) {
            main.appendChild(section);
        });

        shell.appendChild(sidebar);
        shell.appendChild(main);
        hero.insertAdjacentElement("afterend", shell);

        bindSidebarToggles();
        bindModuleShellToolbarSpacing();
    }

    upgradeModuleLayout();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", upgradeModuleLayout);
    }
})();
