(function () {
    var DEFAULT_MAX_ROWS_PER_PAGE = 100;
    var DEFAULT_FROZEN_LEADING_COLUMNS = 4;
    var TABLE_STICKY_TOP_GAP = 10;
    var DEFAULT_MONEY_FORMATTER_PARAMS = {
        decimal: ",",
        thousand: ".",
        symbol: "R$ ",
        symbolAfter: false,
        precision: 2,
    };
    var TABULATOR_LANG_PT_BR = {
        data: {
            loading: "Carregando...",
            error: "Erro ao carregar",
        },
        groups: {
            item: "item",
            items: "itens",
        },
        pagination: {
            page_size: "Linhas",
            first: "Primeira",
            first_title: "Primeira pagina",
            last: "Ultima",
            last_title: "Ultima pagina",
            prev: "Anterior",
            prev_title: "Pagina anterior",
            next: "Proxima",
            next_title: "Proxima pagina",
            all: "Todas",
            counter: {
                showing: "Mostrando",
                of: "de",
                rows: "linhas",
                pages: "paginas",
            },
        },
        headerFilters: {
            default: "Filtrar coluna...",
        },
    };

    function isPlainObject(value) {
        return Object.prototype.toString.call(value) === "[object Object]";
    }

    function deepMergeObjects(target, source) {
        if (!isPlainObject(target)) target = {};
        if (!isPlainObject(source)) return target;

        Object.keys(source).forEach(function (key) {
            var sourceValue = source[key];
            var targetValue = target[key];

            if (isPlainObject(sourceValue)) {
                target[key] = deepMergeObjects(isPlainObject(targetValue) ? targetValue : {}, sourceValue);
                return;
            }

            target[key] = sourceValue;
        });

        return target;
    }

    function applyPortugueseLocale(config) {
        if (!config) return;

        var langs = isPlainObject(config.langs) ? config.langs : {};
        var ptBr = deepMergeObjects({}, TABULATOR_LANG_PT_BR);
        if (isPlainObject(langs["pt-br"])) {
            ptBr = deepMergeObjects(ptBr, langs["pt-br"]);
        }

        langs["pt-br"] = ptBr;
        config.langs = langs;

        if (!config.locale) {
            config.locale = "pt-br";
        }
    }

    function normalizeText(value) {
        return String(value || "").replace(/\s+/g, " ").trim();
    }

    function buildFallbackLabelFromElement(tableElement) {
        if (!tableElement || !tableElement.id) return "Tabela de dados";
        var idLabel = normalizeText(
            String(tableElement.id)
                .replace(/-tabulator$/i, "")
                .replace(/[-_]+/g, " ")
        );
        if (!idLabel) return "Tabela de dados";
        return "Tabela - " + idLabel;
    }

    function extractWrapperHeading(wrapper) {
        if (!wrapper) return "";

        var explicitLabel = normalizeText(wrapper.getAttribute("data-table-label"));
        if (explicitLabel) return explicitLabel;

        var section = wrapper.closest(".panel, section, article, main, .tabulator-cadastro-ux");
        if (section) {
            var heading = section.querySelector("h2, h1, h3");
            var headingText = normalizeText(heading && heading.textContent);
            if (headingText) return headingText;
        }

        var prev = wrapper.previousElementSibling;
        while (prev) {
            if (/^H[1-6]$/.test(prev.tagName || "")) {
                var prevText = normalizeText(prev.textContent);
                if (prevText) return prevText;
            }
            prev = prev.previousElementSibling;
        }

        return "";
    }

    function getStickyTopOffset() {
        var siteHeader = document.querySelector(".site-header");
        if (!siteHeader) return 0;
        var headerHeight = siteHeader.getBoundingClientRect().height;
        if (!Number.isFinite(headerHeight) || headerHeight <= 0) return 0;
        return Math.round(headerHeight + TABLE_STICKY_TOP_GAP);
    }

    function syncWrapperStickyOffset(wrapper) {
        if (!wrapper) return;
        wrapper.style.setProperty("--ux-table-sticky-top", String(getStickyTopOffset()) + "px");
    }

    function normalizeTableWrapper(wrapper, fallbackLabel, tableElement) {
        if (!wrapper) return;

        wrapper.classList.add("table-wrapper--standard");
        wrapper.setAttribute("role", "region");
        syncWrapperStickyOffset(wrapper);

        if (tableElement && tableElement.id) {
            wrapper.setAttribute("aria-controls", tableElement.id);
            tableElement.classList.add("table-tabulator");
        }

        if (!wrapper.hasAttribute("aria-label")) {
            var headingLabel = extractWrapperHeading(wrapper);
            if (headingLabel) {
                wrapper.setAttribute("aria-label", "Tabela - " + headingLabel);
            } else {
                wrapper.setAttribute(
                    "aria-label",
                    normalizeText(fallbackLabel) || buildFallbackLabelFromElement(tableElement)
                );
            }
        }
    }

    function normalizeAllTableWrappers() {
        document.querySelectorAll(".table-wrapper").forEach(function (wrapper) {
            var tableElement = wrapper.querySelector("div[id$='-tabulator']");
            normalizeTableWrapper(wrapper, "Tabela de dados", tableElement);
        });
    }

    function parseDateToTimestamp(rawValue) {
        if (rawValue === null || rawValue === undefined) return null;
        if (typeof rawValue === "number" && Number.isFinite(rawValue)) return rawValue;

        var value = String(rawValue).trim();
        if (!value) return null;

        if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
            var isoTs = Date.parse(value.slice(0, 10) + "T00:00:00");
            return Number.isNaN(isoTs) ? null : isoTs;
        }

        if (/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
            var brParts = value.split("/");
            var brTs = Date.parse(brParts[2] + "-" + brParts[1] + "-" + brParts[0] + "T00:00:00");
            return Number.isNaN(brTs) ? null : brTs;
        }

        if (/^\d{2}-\d{2}-\d{4}$/.test(value)) {
            var dashParts = value.split("-");
            var dashTs = Date.parse(dashParts[2] + "-" + dashParts[1] + "-" + dashParts[0] + "T00:00:00");
            return Number.isNaN(dashTs) ? null : dashTs;
        }

        var fallbackTs = Date.parse(value);
        return Number.isNaN(fallbackTs) ? null : fallbackTs;
    }

    function compareText(a, b) {
        return String(a || "").localeCompare(String(b || ""), "pt-BR", {numeric: true, sensitivity: "base"});
    }

    function looksLikeDateColumn(column) {
        var label = ((column.field || "") + " " + (column.title || "")).toLowerCase();
        return label.indexOf("data") >= 0 || label.indexOf("dt.") >= 0 || label.indexOf("dt ") >= 0;
    }

    function looksLikeBooleanIndicatorColumn(column) {
        var field = String(column.field || "").toLowerCase();
        return /(_indicador|_flag)$/.test(field)
            || /^is_/.test(field)
            || /^tem_/.test(field);
    }

    function looksLikeCurrencyColumn(column) {
        var field = String(column.field || "").toLowerCase();
        var title = String(column.title || "").toLowerCase().trim();

        if (
            field.indexOf("valor_") === 0
            || field.indexOf("vlr_") === 0
            || field.indexOf("custo_") === 0
            || field === "venda_minima"
        ) {
            return true;
        }

        return title.indexOf("valor ") === 0 || title.indexOf("vlr") === 0;
    }

    function isActionColumn(column) {
        var title = String(column.title || "").toLowerCase();
        var field = String(column.field || "").toLowerCase();
        return title.indexOf("acoes") >= 0
            || title.indexOf("acao") >= 0
            || field.indexOf("editar_url") >= 0
            || field.indexOf("excluir_url") >= 0
            || field.indexOf("deletar_url") >= 0;
    }

    function collectLeafColumns(columns, output) {
        if (!Array.isArray(columns)) return output;

        columns.forEach(function (column) {
            if (!column) return;
            if (Array.isArray(column.columns) && column.columns.length) {
                collectLeafColumns(column.columns, output);
                return;
            }
            output.push(column);
        });

        return output;
    }

    function applyAutoFrozenColumns(columns, config) {
        if (!Array.isArray(columns) || !columns.length) return;
        if (config && config.autoFreezeColumns === false) return;

        var leafColumns = collectLeafColumns(columns, []);
        if (!leafColumns.length) return;

        var frozenCount = 0;
        for (var i = 0; i < leafColumns.length && frozenCount < DEFAULT_FROZEN_LEADING_COLUMNS; i += 1) {
            var column = leafColumns[i];
            if (isActionColumn(column)) continue;

            if (Object.prototype.hasOwnProperty.call(column, "frozen")) {
                if (column.frozen) frozenCount += 1;
                continue;
            }

            column.frozen = true;
            frozenCount += 1;
        }
    }


    function resolveDefaultInitialSort(columns) {
        if (!Array.isArray(columns) || !columns.length) return null;

        var leafColumns = collectLeafColumns(columns, []);
        for (var i = 0; i < leafColumns.length; i += 1) {
            var column = leafColumns[i];
            if (!column || !column.field) continue;
            if (isActionColumn(column)) continue;
            if (!looksLikeDateColumn(column)) continue;
            return [{column: column.field, dir: "desc"}];
        }

        var idPriority = ["id", "nro_unico", "numero_unico"];
        for (var j = 0; j < idPriority.length; j += 1) {
            var fieldName = idPriority[j];
            for (var k = 0; k < leafColumns.length; k += 1) {
                var candidate = leafColumns[k];
                if (!candidate || !candidate.field) continue;
                if (String(candidate.field).toLowerCase() !== fieldName) continue;
                return [{column: candidate.field, dir: "desc"}];
            }
        }

        return null;
    }

    function getSortableDateSource(cellValue, rowData, field) {
        if (rowData && field) {
            var isoField = field + "_iso";
            if (rowData[isoField] !== null && rowData[isoField] !== undefined && rowData[isoField] !== "") return rowData[isoField];

            var sortField = field + "_sort";
            if (rowData[sortField] !== null && rowData[sortField] !== undefined && rowData[sortField] !== "") return rowData[sortField];

            var tsField = field + "_ts";
            if (rowData[tsField] !== null && rowData[tsField] !== undefined && rowData[tsField] !== "") return rowData[tsField];
        }
        return cellValue;
    }

    function buildDateSorter(field) {
        return function (a, b, aRow, bRow) {
            var dataA = aRow ? aRow.getData() : null;
            var dataB = bRow ? bRow.getData() : null;
            var sourceA = getSortableDateSource(a, dataA, field);
            var sourceB = getSortableDateSource(b, dataB, field);
            var tsA = parseDateToTimestamp(sourceA);
            var tsB = parseDateToTimestamp(sourceB);

            if (tsA !== null && tsB !== null) return tsA - tsB;
            if (tsA !== null) return -1;
            if (tsB !== null) return 1;
            return compareText(a, b);
        };
    }

    function enhanceColumn(column) {
        var next = Object.assign({}, column);
        if (Array.isArray(next.columns)) {
            next.columns = next.columns.map(enhanceColumn);
            return next;
        }

        if (!next.field) return next;

        if (!Object.prototype.hasOwnProperty.call(next, "formatter") && looksLikeBooleanIndicatorColumn(next)) {
            next.formatter = "tickCross";
        }

        if (
            !Object.prototype.hasOwnProperty.call(next, "headerFilter")
            && looksLikeBooleanIndicatorColumn(next)
        ) {
            next.headerFilter = "tickCross";
        }

        if (!Object.prototype.hasOwnProperty.call(next, "hozAlign") && looksLikeBooleanIndicatorColumn(next)) {
            next.hozAlign = "center";
        }

        if (!Object.prototype.hasOwnProperty.call(next, "formatter") && looksLikeCurrencyColumn(next)) {
            next.formatter = "money";
        }

        if (
            next.formatter === "money"
            && !Object.prototype.hasOwnProperty.call(next, "formatterParams")
        ) {
            next.formatterParams = Object.assign({}, DEFAULT_MONEY_FORMATTER_PARAMS);
        }

        if (!Object.prototype.hasOwnProperty.call(next, "hozAlign") && looksLikeCurrencyColumn(next)) {
            next.hozAlign = "right";
        }

        if (!Object.prototype.hasOwnProperty.call(next, "headerFilter") && !isActionColumn(next)) {
            next.headerFilter = "input";
        }

        if (!next.sorter && looksLikeDateColumn(next)) {
            next.sorter = buildDateSorter(next.field);
        }

        return next;
    }

    function enhanceConfig(config) {
        var next = Object.assign({}, config || {});
        applyPortugueseLocale(next);

        if (Array.isArray(next.columns)) {
            next.columns = next.columns.map(enhanceColumn);
            applyAutoFrozenColumns(next.columns, next);
            if (!Object.prototype.hasOwnProperty.call(next, "initialSort")) {
                var defaultInitialSort = resolveDefaultInitialSort(next.columns);
                if (defaultInitialSort) {
                    next.initialSort = defaultInitialSort;
                }
            }
        }
        if (!next.placeholder) {
            next.placeholder = "Nenhum registro encontrado para os filtros atuais.";
        }
        if (!next.layout) {
            next.layout = "fitDataStretch";
        }
        if (!next.height && !next.maxHeight) {
            next.maxHeight = "62vh";
        }
        if (next.movableColumns === undefined) {
            next.movableColumns = true;
        }
        next.headerFilterLiveFilter = true;

        if (next.pagination === undefined) {
            next.pagination = "local";
        }

        if (next.pagination !== false) {
            var currentSize = Number(next.paginationSize || DEFAULT_MAX_ROWS_PER_PAGE);
            if (!Number.isFinite(currentSize) || currentSize <= 0) currentSize = DEFAULT_MAX_ROWS_PER_PAGE;
            next.paginationSize = Math.min(currentSize, DEFAULT_MAX_ROWS_PER_PAGE);
            if (!next.paginationSizeSelector) {
                next.paginationSizeSelector = false;
            }
            if (!next.paginationCounter) {
                next.paginationCounter = "rows";
            }
        }

        return next;
    }

    function installBottomHorizontalScrollbar(tabulatorInstance) {
        if (!tabulatorInstance || typeof tabulatorInstance.getElement !== "function") return;
        var tableElement = tabulatorInstance.getElement();
        if (!tableElement) return;

        var wrapper = tableElement.closest(".table-wrapper");
        if (!wrapper) return;
        normalizeTableWrapper(wrapper, buildFallbackLabelFromElement(tableElement), tableElement);
        wrapper.classList.add("table-wrapper--tabulator");

        var tableHolder = tableElement.querySelector(".tabulator-tableholder");
        if (!tableHolder) return;

        var bottomBar = wrapper.querySelector(".tabulator-bottom-scrollbar");
        var bottomBarInner = bottomBar ? bottomBar.querySelector(".tabulator-bottom-scrollbar-inner") : null;

        if (!bottomBar) {
            bottomBar = document.createElement("div");
            bottomBar.className = "tabulator-bottom-scrollbar";
            bottomBarInner = document.createElement("div");
            bottomBarInner.className = "tabulator-bottom-scrollbar-inner";
            bottomBar.appendChild(bottomBarInner);
            tableElement.insertAdjacentElement("afterend", bottomBar);
        }

        function syncWidths() {
            var contentWidth = tableHolder.scrollWidth || 0;
            var viewportWidth = tableHolder.clientWidth || 0;
            var hasHorizontalOverflow = contentWidth > viewportWidth;
            bottomBarInner.style.width = contentWidth + "px";
            bottomBar.style.display = hasHorizontalOverflow ? "block" : "none";
            wrapper.classList.toggle("table-wrapper--has-bottom-scrollbar", hasHorizontalOverflow);
            bottomBar.scrollLeft = tableHolder.scrollLeft;
        }

        var syncingFromBottom = false;
        var syncingFromTable = false;

        bottomBar.addEventListener("scroll", function () {
            if (syncingFromTable) return;
            syncingFromBottom = true;
            tableHolder.scrollLeft = bottomBar.scrollLeft;
            syncingFromBottom = false;
        });

        tableHolder.addEventListener("scroll", function () {
            if (syncingFromBottom) return;
            syncingFromTable = true;
            bottomBar.scrollLeft = tableHolder.scrollLeft;
            syncingFromTable = false;
        });

        tabulatorInstance.on("tableBuilt", syncWidths);
        tabulatorInstance.on("dataLoaded", syncWidths);
        tabulatorInstance.on("renderComplete", syncWidths);
        tabulatorInstance.on("columnResized", syncWidths);
        tabulatorInstance.on("columnMoved", syncWidths);
        tabulatorInstance.on("columnVisibilityChanged", syncWidths);
        window.addEventListener("resize", syncWidths);

        if (window.ResizeObserver) {
            var observer = new ResizeObserver(syncWidths);
            observer.observe(tableHolder);
        }

        setTimeout(syncWidths, 0);
    }

    function create(target, config) {
        if (!window.Tabulator) {
            throw new Error("Tabulator nao esta carregado.");
        }
        var enhancedConfig = enhanceConfig(config);
        var table = new window.Tabulator(target, enhancedConfig);
        installBottomHorizontalScrollbar(table);
        return table;
    }

    function installGlobalDomStickyWatcher() {
        if (window.__tabulatorGlobalStickyWatcherInstalled) return;
        window.__tabulatorGlobalStickyWatcherInstalled = true;

        function attachToTableElement(tableElement) {
            if (!tableElement || tableElement.dataset.globalStickyWatcherReady === "1") return;

            var wrapper = tableElement.closest(".table-wrapper");
            if (wrapper) {
                normalizeTableWrapper(wrapper, buildFallbackLabelFromElement(tableElement), tableElement);
                wrapper.classList.add("table-wrapper--tabulator");
            }

            tableElement.dataset.globalStickyWatcherReady = "1";
        }

        function scanAndAttach() {
            normalizeAllTableWrappers();
            var tables = document.querySelectorAll(".table-wrapper .tabulator");
            tables.forEach(attachToTableElement);
        }

        function installStickyTopSync() {
            if (window.__tableWrapperStickyTopSyncInstalled) return;
            window.__tableWrapperStickyTopSyncInstalled = true;

            var sync = function () {
                document.querySelectorAll(".table-wrapper").forEach(syncWrapperStickyOffset);
            };

            window.addEventListener("resize", sync);
            window.addEventListener("orientationchange", sync);
            if (document.readyState === "loading") {
                document.addEventListener("DOMContentLoaded", sync);
            } else {
                sync();
            }
        }

        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", scanAndAttach);
        } else {
            scanAndAttach();
        }
        installStickyTopSync();

        var pageObserver = new MutationObserver(scanAndAttach);
        pageObserver.observe(document.documentElement, {childList: true, subtree: true});
    }

    window.TabulatorDefaults = {
        create: create,
        enhanceConfig: enhanceConfig,
    };

    installGlobalDomStickyWatcher();
})();
