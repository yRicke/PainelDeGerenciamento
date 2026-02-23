(function () {
    var DEFAULT_MAX_ROWS_PER_PAGE = 15;

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

    function isActionColumn(column) {
        var title = String(column.title || "").toLowerCase();
        var field = String(column.field || "").toLowerCase();
        return title.indexOf("acoes") >= 0
            || title.indexOf("acao") >= 0
            || field.indexOf("editar_url") >= 0
            || field.indexOf("excluir_url") >= 0
            || field.indexOf("deletar_url") >= 0;
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
        if (Array.isArray(next.columns)) {
            next.columns = next.columns.map(enhanceColumn);
        }
        next.headerFilterLiveFilter = true;

        if (next.pagination === undefined) {
            next.pagination = "local";
        }

        if (next.pagination !== false) {
            var currentSize = Number(next.paginationSize || DEFAULT_MAX_ROWS_PER_PAGE);
            if (!Number.isFinite(currentSize) || currentSize <= 0) currentSize = DEFAULT_MAX_ROWS_PER_PAGE;
            next.paginationSize = Math.min(currentSize, DEFAULT_MAX_ROWS_PER_PAGE);
        }

        return next;
    }

    function installTopHorizontalScrollbar(tabulatorInstance) {
        if (!tabulatorInstance || typeof tabulatorInstance.getElement !== "function") return;
        var tableElement = tabulatorInstance.getElement();
        if (!tableElement) return;

        var wrapper = tableElement.closest(".table-wrapper");
        if (!wrapper) return;

        var tableHolder = tableElement.querySelector(".tabulator-tableholder");
        if (!tableHolder) return;

        var topBar = wrapper.querySelector(".tabulator-top-scrollbar");
        var topBarInner = topBar ? topBar.querySelector(".tabulator-top-scrollbar-inner") : null;

        if (!topBar) {
            topBar = document.createElement("div");
            topBar.className = "tabulator-top-scrollbar";
            topBarInner = document.createElement("div");
            topBarInner.className = "tabulator-top-scrollbar-inner";
            topBar.appendChild(topBarInner);
            wrapper.insertBefore(topBar, tableElement);
        }

        function syncWidths() {
            var contentWidth = tableHolder.scrollWidth || 0;
            var viewportWidth = tableHolder.clientWidth || 0;
            topBarInner.style.width = contentWidth + "px";
            topBar.style.display = contentWidth > viewportWidth ? "block" : "none";
            topBar.scrollLeft = tableHolder.scrollLeft;
        }

        var syncingFromTop = false;
        var syncingFromTable = false;

        topBar.addEventListener("scroll", function () {
            if (syncingFromTable) return;
            syncingFromTop = true;
            tableHolder.scrollLeft = topBar.scrollLeft;
            syncingFromTop = false;
        });

        tableHolder.addEventListener("scroll", function () {
            if (syncingFromTop) return;
            syncingFromTable = true;
            topBar.scrollLeft = tableHolder.scrollLeft;
            syncingFromTable = false;
        });

        tabulatorInstance.on("tableBuilt", syncWidths);
        tabulatorInstance.on("dataLoaded", syncWidths);
        tabulatorInstance.on("renderComplete", syncWidths);
        window.addEventListener("resize", syncWidths);
        setTimeout(syncWidths, 0);
    }

    function create(target, config) {
        if (!window.Tabulator) {
            throw new Error("Tabulator nao esta carregado.");
        }
        var table = new window.Tabulator(target, enhanceConfig(config));
        installTopHorizontalScrollbar(table);
        return table;
    }

    window.TabulatorDefaults = {
        create: create,
        enhanceConfig: enhanceConfig,
    };
})();
