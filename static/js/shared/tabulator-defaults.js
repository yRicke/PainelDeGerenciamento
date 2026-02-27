(function () {
    var DEFAULT_MAX_ROWS_PER_PAGE = 100;
    var DEFAULT_FROZEN_LEADING_COLUMNS = 4;
    var AUTO_FROZEN_MARKER = "__tabulatorDefaultsAutoFrozen";
    var FREEZE_STORAGE_PREFIX = "tabulator-frozen-columns::v1::";
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
            first_title: "Primeira p\u00E1gina",
            last: "\u00DAltima",
            last_title: "\u00DAltima p\u00E1gina",
            prev: "Anterior",
            prev_title: "P\u00E1gina anterior",
            next: "Pr\u00F3xima",
            next_title: "Pr\u00F3xima p\u00E1gina",
            all: "Todas",
            counter: {
                showing: "Mostrando",
                of: "de",
                rows: "linhas",
                pages: "p\u00E1ginas",
            },
        },
        headerFilters: {
            default: "Filtrar coluna...",
        },
    };

    function normalizeForComparison(value) {
        return String(value || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    function resolveActionColumnTitle() {
        var shared = window.FrontendText
            && window.FrontendText.common
            && window.FrontendText.common.actionColumn;
        return shared || "A\u00E7\u00F5es";
    }

    function resolveFreezeMenuLabels(rawLabels) {
        var shared = window.FrontendText && window.FrontendText.common
            ? window.FrontendText.common
            : {};
        var labels = isPlainObject(rawLabels) ? rawLabels : {};
        return {
            freeze: String(
                labels.freeze
                || shared.freezeColumn
                || "Fixar coluna"
            ),
            unfreeze: String(
                labels.unfreeze
                || shared.unfreezeColumn
                || "Desfixar coluna"
            ),
            clear: String(
                labels.clear
                || shared.clearFrozenColumns
                || "Limpar colunas fixas"
            ),
        };
    }

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

    function titleContainsActionWord(title) {
        var normalizedTitle = normalizeForComparison(title);
        if (!normalizedTitle) return false;

        var tokens = normalizedTitle.split(/[^a-z0-9_]+/).filter(Boolean);
        return tokens.indexOf("acao") >= 0 || tokens.indexOf("acoes") >= 0;
    }

    function isActionColumn(column) {
        var title = String(column.title || "");
        var field = String(column.field || "").toLowerCase();
        return titleContainsActionWord(title)
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
            column[AUTO_FROZEN_MARKER] = true;
            frozenCount += 1;
        }
    }

    function clearAutoFrozenMarkers(columns) {
        var leafColumns = collectLeafColumns(columns, []);
        leafColumns.forEach(function (column) {
            if (!column) return;
            if (!Object.prototype.hasOwnProperty.call(column, AUTO_FROZEN_MARKER)) return;
            delete column[AUTO_FROZEN_MARKER];
        });
    }

    function resolveTargetId(target) {
        if (!target) return "";
        if (typeof target === "string") {
            var trimmed = target.trim();
            if (!trimmed) return "";
            if (trimmed.charAt(0) === "#") return trimmed.slice(1);
            try {
                var selected = document.querySelector(trimmed);
                if (selected && selected.id) return selected.id;
            } catch (_err) {
                return trimmed;
            }
            return trimmed;
        }
        if (target && target.id) return String(target.id);
        return "";
    }

    function normalizeFreezeOptions(target, config) {
        var raw = isPlainObject(config && config.freezeUX) ? config.freezeUX : null;
        if (!raw || raw.enabled !== true) return null;

        var persist = raw.persist !== false;
        var resolvedId = resolveTargetId(target);
        var rawStorageKey = String(raw.storageKey || resolvedId).trim();
        var storageKey = persist && rawStorageKey
            ? FREEZE_STORAGE_PREFIX + rawStorageKey
            : "";

        return {
            enabled: true,
            persist: Boolean(storageKey),
            storageKey: storageKey,
            includeClearAction: raw.includeClearAction !== false,
            labels: resolveFreezeMenuLabels(raw.labels),
        };
    }

    function readPersistedFrozenState(freezeOptions) {
        if (!freezeOptions || !freezeOptions.persist || !freezeOptions.storageKey) return null;
        if (!window.localStorage) return null;

        try {
            var rawState = window.localStorage.getItem(freezeOptions.storageKey);
            if (!rawState) return null;
            var parsed = JSON.parse(rawState);
            if (!isPlainObject(parsed)) return null;
            if (!Array.isArray(parsed.frozenFields)) return null;
            return parsed;
        } catch (_err) {
            return null;
        }
    }

    function writePersistedFrozenState(freezeOptions, frozenFields) {
        if (!freezeOptions || !freezeOptions.persist || !freezeOptions.storageKey) return;
        if (!window.localStorage) return;

        try {
            window.localStorage.setItem(
                freezeOptions.storageKey,
                JSON.stringify({
                    frozenFields: frozenFields,
                })
            );
        } catch (_err) {
            // localStorage might be unavailable; keep feature functional without persistence.
        }
    }

    function applyPersistedFrozenState(columns, freezeOptions) {
        if (!Array.isArray(columns) || !columns.length) return false;
        var persisted = readPersistedFrozenState(freezeOptions);
        if (!persisted || !Array.isArray(persisted.frozenFields)) return false;

        var persistedOrder = persisted.frozenFields
            .map(function (value) { return String(value || ""); })
            .filter(Boolean);
        if (freezeOptions) {
            freezeOptions.initialFrozenOrder = Array.from(new Set(persistedOrder));
        }
        var persistedFields = new Set(persistedOrder);

        var leafColumns = collectLeafColumns(columns, []);
        leafColumns.forEach(function (column) {
            if (!column || !column.field || isActionColumn(column)) return;
            var field = String(column.field);
            if (persistedFields.has(field)) {
                column.frozen = true;
                return;
            }
            if (column[AUTO_FROZEN_MARKER]) {
                delete column.frozen;
            }
        });

        movePersistedFrozenColumnsToLeft(columns, persistedFields);
        return true;
    }

    function movePersistedFrozenColumnsToLeft(columns, persistedFields) {
        if (!Array.isArray(columns) || !columns.length) return;
        if (!(persistedFields instanceof Set) || !persistedFields.size) return;

        var hasNested = columns.some(function (column) {
            return Boolean(column && Array.isArray(column.columns) && column.columns.length);
        });
        if (hasNested) return;

        var frozenColumns = [];
        var remainingColumns = [];

        columns.forEach(function (column) {
            if (!column || !column.field || isActionColumn(column)) {
                remainingColumns.push(column);
                return;
            }

            if (persistedFields.has(String(column.field))) {
                frozenColumns.push(column);
                return;
            }

            remainingColumns.push(column);
        });

        if (!frozenColumns.length) return;
        columns.length = 0;
        frozenColumns.concat(remainingColumns).forEach(function (column) {
            columns.push(column);
        });
    }

    function collectLeafColumnComponents(columnComponents, output) {
        if (!Array.isArray(columnComponents)) return output;

        columnComponents.forEach(function (column) {
            if (!column) return;
            if (typeof column.getSubColumns === "function") {
                var subColumns = column.getSubColumns();
                if (Array.isArray(subColumns) && subColumns.length) {
                    collectLeafColumnComponents(subColumns, output);
                    return;
                }
            }
            output.push(column);
        });

        return output;
    }

    function getTableFromColumn(column) {
        if (!column || typeof column.getTable !== "function") return null;
        return column.getTable();
    }

    function isFreezableColumnComponent(column) {
        if (!column || typeof column.getDefinition !== "function") return false;
        var definition = column.getDefinition();
        if (!definition || !definition.field) return false;
        return !isActionColumn(definition);
    }

    function setColumnFrozenState(column, shouldFreeze) {
        if (!column) return null;

        if (shouldFreeze) {
            if (typeof column.freeze === "function") {
                return column.freeze();
            }
            if (typeof column.updateDefinition === "function") {
                return column.updateDefinition({frozen: true});
            }
            return null;
        }

        if (typeof column.unfreeze === "function") {
            return column.unfreeze();
        }
        if (typeof column.updateDefinition === "function") {
            return column.updateDefinition({frozen: false});
        }
        return null;
    }

    function runAfterColumnMutation(result, onDone) {
        var callback = typeof onDone === "function" ? onDone : function () {};
        if (result && typeof result.then === "function") {
            result.then(callback).catch(callback);
            return;
        }
        callback();
    }

    function getColumnField(column) {
        if (!column || typeof column.getDefinition !== "function") return "";
        var definition = column.getDefinition();
        if (!definition || !definition.field) return "";
        return String(definition.field);
    }

    function findColumnIndex(leafColumns, targetColumn) {
        if (!Array.isArray(leafColumns) || !leafColumns.length || !targetColumn) return -1;

        var directIndex = leafColumns.indexOf(targetColumn);
        if (directIndex >= 0) return directIndex;

        var field = getColumnField(targetColumn);
        if (!field) return -1;

        for (var i = 0; i < leafColumns.length; i += 1) {
            if (getColumnField(leafColumns[i]) === field) return i;
        }

        return -1;
    }

    function findColumnComponentByField(leafColumns, field) {
        if (!Array.isArray(leafColumns) || !leafColumns.length) return null;
        var normalizedField = String(field || "");
        if (!normalizedField) return null;

        for (var i = 0; i < leafColumns.length; i += 1) {
            if (getColumnField(leafColumns[i]) === normalizedField) return leafColumns[i];
        }

        return null;
    }

    function moveColumnNearReference(column, referenceColumn, placeAfter) {
        if (!column || !referenceColumn || column === referenceColumn) return false;

        var table = getTableFromColumn(column);
        if (table && typeof table.moveColumn === "function") {
            try {
                table.moveColumn(column, referenceColumn, placeAfter === true);
                return true;
            } catch (_errMoveTable) {
                // Fallback below.
            }
        }

        try {
            if (typeof column.move === "function") {
                column.move(referenceColumn, placeAfter === true);
                return true;
            }
        } catch (_errMoveColumn) {
            // No-op.
        }

        if (!table || typeof table.moveColumn !== "function") return false;
        try {
            table.moveColumn(column, referenceColumn, placeAfter === true);
            return true;
        } catch (_errMoveTableAgain) {
            return false;
        }
    }

    function collectFrozenFieldsFromDefinitions(definitions, output) {
        if (!Array.isArray(definitions)) return output;

        definitions.forEach(function (definition) {
            if (!definition) return;
            if (Array.isArray(definition.columns) && definition.columns.length) {
                collectFrozenFieldsFromDefinitions(definition.columns, output);
                return;
            }
            if (!definition.field || isActionColumn(definition)) return;
            if (definition.frozen) output.push(String(definition.field));
        });

        return output;
    }

    function getFrozenFieldSetFromTable(table) {
        if (!table || typeof table.getColumnDefinitions !== "function") return null;
        var frozenFields = collectFrozenFieldsFromDefinitions(table.getColumnDefinitions(), []);
        return new Set(frozenFields);
    }

    function getOrderedFrozenFields(table) {
        if (!table || typeof table.getColumns !== "function") return [];

        var frozenSet = getFrozenFieldSetFromTable(table);
        var leafColumns = collectLeafColumnComponents(table.getColumns(), []);
        if (!leafColumns.length) return [];

        var orderedFields = [];
        leafColumns.forEach(function (column) {
            if (!isFreezableColumnComponent(column)) return;
            var field = getColumnField(column);
            if (!field) return;
            if (frozenSet && !frozenSet.has(field)) return;
            if (!frozenSet && !isColumnCurrentlyFrozen(column)) return;
            orderedFields.push(field);
        });

        return Array.from(new Set(orderedFields));
    }

    function normalizeFrozenOrderForTable(table, frozenOrder) {
        if (!table || typeof table.getColumns !== "function") return [];

        var desiredOrder = Array.isArray(frozenOrder)
            ? frozenOrder.map(function (item) { return String(item || ""); }).filter(Boolean)
            : [];

        var leafColumns = collectLeafColumnComponents(table.getColumns(), []);
        if (!leafColumns.length || !desiredOrder.length) return [];

        var existingFields = new Set();
        leafColumns.forEach(function (column) {
            if (!isFreezableColumnComponent(column)) return;
            var field = getColumnField(column);
            if (!field) return;
            existingFields.add(field);
        });

        return Array.from(new Set(desiredOrder)).filter(function (field) {
            return existingFields.has(field);
        });
    }

    function positionColumnsForFrozenOrder(table, frozenOrder) {
        if (!table || typeof table.getColumns !== "function") return;
        var order = normalizeFrozenOrderForTable(table, frozenOrder);
        if (!order.length) return;

        for (var i = 0; i < order.length; i += 1) {
            var leafColumns = collectLeafColumnComponents(table.getColumns(), []);
            if (!leafColumns.length) return;

            var currentColumn = findColumnComponentByField(leafColumns, order[i]);
            if (!currentColumn) continue;

            if (i === 0) {
                var leftmostColumn = leafColumns[0];
                if (leftmostColumn && leftmostColumn !== currentColumn) {
                    moveColumnNearReference(currentColumn, leftmostColumn, false);
                }
                continue;
            }

            var prevColumn = findColumnComponentByField(leafColumns, order[i - 1]);
            if (!prevColumn || prevColumn === currentColumn) continue;

            var prevIndex = findColumnIndex(leafColumns, prevColumn);
            var currIndex = findColumnIndex(leafColumns, currentColumn);
            if (prevIndex < 0 || currIndex < 0) continue;

            if (currIndex !== prevIndex + 1) {
                moveColumnNearReference(currentColumn, prevColumn, true);
            }
        }
    }

    function captureHeaderFilterState(table) {
        if (!table || typeof table.getHeaderFilters !== "function") return [];
        try {
            var filters = table.getHeaderFilters();
            if (!Array.isArray(filters)) return [];
            return filters
                .filter(function (item) {
                    return item && item.field;
                })
                .map(function (item) {
                    return {
                        field: String(item.field),
                        value: item.value,
                    };
                });
        } catch (_err) {
            return [];
        }
    }

    function restoreHeaderFilterState(table, state) {
        if (!table || typeof table.setHeaderFilterValue !== "function") return;
        if (!Array.isArray(state) || !state.length) return;

        state.forEach(function (item) {
            if (!item || !item.field) return;
            try {
                table.setHeaderFilterValue(item.field, item.value);
            } catch (_err) {
                // Ignore restoration errors for fields that may no longer exist.
            }
        });
    }

    function countExpectedHeaderFiltersFromDefinitions(definitions) {
        if (!Array.isArray(definitions) || !definitions.length) return 0;
        var count = 0;

        definitions.forEach(function (definition) {
            if (!definition) return;
            if (Array.isArray(definition.columns) && definition.columns.length) {
                count += countExpectedHeaderFiltersFromDefinitions(definition.columns);
                return;
            }

            if (!definition.field || isActionColumn(definition)) return;
            if (definition.visible === false) return;
            if (!Object.prototype.hasOwnProperty.call(definition, "headerFilter")) return;
            if (definition.headerFilter === false || definition.headerFilter === null) return;
            count += 1;
        });

        return count;
    }

    function getRenderedHeaderFilterInputCount(table) {
        if (!table || typeof table.getElement !== "function") return 0;
        var tableElement = table.getElement();
        if (!tableElement) return 0;
        return tableElement.querySelectorAll(
            ".tabulator-header .tabulator-header-filter input, .tabulator-header .tabulator-header-filter select, .tabulator-header .tabulator-header-filter textarea"
        ).length;
    }

    function recoverHeaderFiltersIfMissing(table, savedState) {
        if (!table || typeof table.getColumnDefinitions !== "function") return;
        if (typeof table.setColumns !== "function") return;

        var expectedCount = countExpectedHeaderFiltersFromDefinitions(table.getColumnDefinitions());
        if (expectedCount <= 0) return;

        var renderedCount = getRenderedHeaderFilterInputCount(table);
        if (renderedCount > 0) return;

        var definitions = table.getColumnDefinitions();
        var result = table.setColumns(definitions);
        runAfterColumnMutation(result, function () {
            restoreHeaderFilterState(table, savedState);
            if (typeof table.redraw === "function") {
                table.redraw(true);
            }
        });
    }

    function applyFrozenFlagsForOrder(table, frozenOrder, freezeOptions, savedHeaderFilters) {
        if (!table || typeof table.getColumns !== "function") {
            finalizeFrozenColumnMutation(table, freezeOptions, savedHeaderFilters);
            return;
        }

        var normalizedOrder = normalizeFrozenOrderForTable(table, frozenOrder);
        if (freezeOptions) {
            freezeOptions.runtimeFrozenOrder = normalizedOrder.slice();
        }
        var desiredSet = new Set(normalizedOrder);
        var leafColumns = collectLeafColumnComponents(table.getColumns(), []);
        var pending = 0;

        function done() {
            pending -= 1;
            if (pending <= 0) {
                finalizeFrozenColumnMutation(table, freezeOptions, savedHeaderFilters);
            }
        }

        leafColumns.forEach(function (column) {
            if (!isFreezableColumnComponent(column)) return;
            var field = getColumnField(column);
            if (!field) return;

            var shouldBeFrozen = desiredSet.has(field);
            var currentlyFrozen = isColumnCurrentlyFrozen(column);
            if (currentlyFrozen === shouldBeFrozen) return;

            pending += 1;
            var mutation = setColumnFrozenState(column, shouldBeFrozen);
            runAfterColumnMutation(mutation, done);
        });

        if (pending === 0) {
            finalizeFrozenColumnMutation(table, freezeOptions, savedHeaderFilters);
        }
    }

    function applyDeterministicFrozenLayout(table, frozenOrder, freezeOptions) {
        if (!table) return;
        var normalizedOrder = normalizeFrozenOrderForTable(table, frozenOrder);
        var savedHeaderFilters = captureHeaderFilterState(table);
        positionColumnsForFrozenOrder(table, normalizedOrder);
        applyFrozenFlagsForOrder(table, normalizedOrder, freezeOptions, savedHeaderFilters);
    }

    function resolveOrderForFreezeAction(table, targetField) {
        var currentOrder = getOrderedFrozenFields(table);
        var field = String(targetField || "");
        if (!field) return currentOrder;
        if (currentOrder.indexOf(field) >= 0) return currentOrder;

        var leafColumns = collectLeafColumnComponents(table.getColumns(), []);
        if (!leafColumns.length) return currentOrder.concat([field]);

        var targetColumn = findColumnComponentByField(leafColumns, field);
        if (!targetColumn) return currentOrder.concat([field]);

        var targetIndex = findColumnIndex(leafColumns, targetColumn);
        if (targetIndex < 0) return currentOrder.concat([field]);

        var insertAt = 0;
        for (var i = 0; i < currentOrder.length; i += 1) {
            var frozenColumn = findColumnComponentByField(leafColumns, currentOrder[i]);
            if (!frozenColumn) continue;
            var frozenIndex = findColumnIndex(leafColumns, frozenColumn);
            if (frozenIndex < targetIndex) insertAt = i + 1;
        }

        var nextOrder = currentOrder.slice();
        nextOrder.splice(insertAt, 0, field);
        return nextOrder;
    }

    function isColumnCurrentlyFrozen(column) {
        if (!column) return false;

        var table = getTableFromColumn(column);
        var field = getColumnField(column);
        if (table && field) {
            var frozenFieldSet = getFrozenFieldSetFromTable(table);
            if (frozenFieldSet) return frozenFieldSet.has(field);
        }

        var definition = typeof column.getDefinition === "function" ? column.getDefinition() : null;
        return Boolean(definition && definition.frozen);
    }

    function captureFrozenFields(table) {
        if (!table) return [];
        return getOrderedFrozenFields(table);
    }

    function persistFrozenFields(table, freezeOptions) {
        if (!freezeOptions || !freezeOptions.persist) return;
        var frozenFields = Array.isArray(freezeOptions.runtimeFrozenOrder)
            ? freezeOptions.runtimeFrozenOrder.slice()
            : captureFrozenFields(table);
        writePersistedFrozenState(freezeOptions, frozenFields);
    }

    function queuePersistFrozenFields(table, freezeOptions) {
        if (!table || !freezeOptions || !freezeOptions.persist) return;
        setTimeout(function () {
            persistFrozenFields(table, freezeOptions);
        }, 0);
    }

    function queueTableRedraw(table) {
        if (!table || typeof table.redraw !== "function") return;
        setTimeout(function () {
            table.redraw(true);
        }, 0);
    }

    function finalizeFrozenColumnMutation(table, freezeOptions, savedHeaderFilters) {
        if (!table) return;
        queuePersistFrozenFields(table, freezeOptions);
        queueTableRedraw(table);
        setTimeout(function () {
            recoverHeaderFiltersIfMissing(table, savedHeaderFilters);
        }, 0);
    }

    function installInitialFrozenLayoutNormalization(table, freezeOptions) {
        if (!table || !freezeOptions) return;
        var initialized = false;
        function runOnce() {
            if (initialized) return;
            initialized = true;
            var initialOrder = Array.isArray(freezeOptions.initialFrozenOrder)
                ? freezeOptions.initialFrozenOrder.slice()
                : getOrderedFrozenFields(table);
            applyDeterministicFrozenLayout(table, initialOrder, freezeOptions);
            setTimeout(function () {
                applyDeterministicFrozenLayout(table, initialOrder, freezeOptions);
            }, 0);
        }

        if (typeof table.on === "function") {
            table.on("tableBuilt", runOnce);
        }
        setTimeout(runOnce, 0);
    }

    function freezeColumnFromMenu(column, freezeOptions) {
        if (!isFreezableColumnComponent(column)) return;
        if (isColumnCurrentlyFrozen(column)) return;

        var table = getTableFromColumn(column);
        var field = getColumnField(column);
        if (!table || !field) return;

        var nextOrder = resolveOrderForFreezeAction(table, field);
        applyDeterministicFrozenLayout(table, nextOrder, freezeOptions);
    }

    function unfreezeColumnFromMenu(column, freezeOptions) {
        if (!isFreezableColumnComponent(column)) return;
        if (!isColumnCurrentlyFrozen(column)) return;

        var table = getTableFromColumn(column);
        var field = getColumnField(column);
        if (!table || !field) return;

        var nextOrder = getOrderedFrozenFields(table).filter(function (frozenField) {
            return frozenField !== field;
        });
        applyDeterministicFrozenLayout(table, nextOrder, freezeOptions);
    }

    function clearAllFrozenColumns(table, freezeOptions) {
        if (!table) return;
        applyDeterministicFrozenLayout(table, [], freezeOptions);
    }

    function buildFreezeMenuItems(column, freezeOptions) {
        var labels = (freezeOptions && freezeOptions.labels) || resolveFreezeMenuLabels();
        var isFrozen = isColumnCurrentlyFrozen(column);
        var items = [];

        if (isFrozen) {
            items.push({
                label: labels.unfreeze,
                action: function (_event, columnComponent) {
                    unfreezeColumnFromMenu(columnComponent, freezeOptions);
                },
            });
        } else {
            items.push({
                label: labels.freeze,
                action: function (_event, columnComponent) {
                    freezeColumnFromMenu(columnComponent, freezeOptions);
                },
            });
        }

        if (isFrozen && freezeOptions && freezeOptions.includeClearAction) {
            items.push({separator: true});
            items.push({
                label: labels.clear,
                action: function (_event, columnComponent) {
                    clearAllFrozenColumns(getTableFromColumn(columnComponent), freezeOptions);
                },
            });
        }

        return items;
    }

    function resolveExistingHeaderMenuItems(existingHeaderMenu, context, args) {
        if (typeof existingHeaderMenu === "function") {
            try {
                var resolved = existingHeaderMenu.apply(context, args || []);
                return Array.isArray(resolved) ? resolved.slice() : [];
            } catch (_errExistingMenu) {
                return [];
            }
        }

        if (Array.isArray(existingHeaderMenu)) {
            return existingHeaderMenu.slice();
        }

        return [];
    }

    function applyFreezeHeaderMenu(columns, freezeOptions) {
        if (!Array.isArray(columns) || !columns.length || !freezeOptions) return;
        var leafColumns = collectLeafColumns(columns, []);
        leafColumns.forEach(function (column) {
            if (!column || !column.field || isActionColumn(column)) return;
            var existingHeaderMenu = column.headerMenu;
            column.headerMenu = function () {
                var args = Array.prototype.slice.call(arguments);
                var columnComponent = null;

                if (this && typeof this.getDefinition === "function") {
                    columnComponent = this;
                } else {
                    for (var i = 0; i < args.length; i += 1) {
                        var candidate = args[i];
                        if (candidate && typeof candidate.getDefinition === "function") {
                            columnComponent = candidate;
                            break;
                        }
                    }
                }

                var existingItems = resolveExistingHeaderMenuItems(existingHeaderMenu, this, args);
                var freezeItems = buildFreezeMenuItems(columnComponent, freezeOptions);

                if (!existingItems.length) return freezeItems;
                if (!freezeItems.length) return existingItems;
                return existingItems.concat([{separator: true}], freezeItems);
            };
        });
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

        if (isActionColumn(next)) {
            next.title = resolveActionColumnTitle();
        }

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
            throw new Error("Tabulator n\u00E3o est\u00E1 carregado.");
        }
        var enhancedConfig = enhanceConfig(config);
        var freezeOptions = normalizeFreezeOptions(target, enhancedConfig);

        if (freezeOptions) {
            applyPersistedFrozenState(enhancedConfig.columns, freezeOptions);
            applyFreezeHeaderMenu(enhancedConfig.columns, freezeOptions);
        }
        clearAutoFrozenMarkers(enhancedConfig.columns);

        var table = new window.Tabulator(target, enhancedConfig);
        installBottomHorizontalScrollbar(table);
        hideEmptyActionColumns(table, enhancedConfig);
        if (freezeOptions) {
            installInitialFrozenLayoutNormalization(table, freezeOptions);
        }
        return table;
    }

    function toButtonLabel(value, fallback) {
        var text = String(value || "").trim();
        return text || fallback;
    }

    function toCssClass(value, fallback) {
        var text = String(value || "").trim();
        return text || fallback;
    }

    function normalizeColumnOptions(options) {
        return isPlainObject(options) ? options : {};
    }

    function resolveRowValue(rowData, valueOrFn) {
        if (typeof valueOrFn === "function") {
            return valueOrFn(rowData);
        }
        return valueOrFn;
    }

    function buildEditActionColumn(options) {
        var cfg = normalizeColumnOptions(options);
        var field = String(cfg.field || "editar_url");
        var actionLabel = toButtonLabel(cfg.label, "Editar");
        var actionClass = toCssClass(cfg.className, "btn-primary");
        var column = {
            title: resolveActionColumnTitle(),
            field: field,
            hozAlign: cfg.hozAlign || "center",
            formatter: typeof cfg.formatter === "function"
                ? cfg.formatter
                : function (cell) {
                    var url = cell.getValue();
                    if (!url) return "";
                    return '<a class="' + actionClass + '" href="' + url + '">' + actionLabel + "</a>";
                },
        };

        if (Number.isFinite(cfg.width)) {
            column.width = cfg.width;
        }

        if (typeof cfg.cellClick === "function") {
            column.cellClick = cfg.cellClick;
        }

        return column;
    }

    function addEditActionColumnIfAny(columns, data, options) {
        if (!Array.isArray(columns)) return columns;
        var cfg = normalizeColumnOptions(options);
        var field = String(cfg.field || "editar_url");
        if (!hasAnyRowAction(data, [field])) return columns;
        columns.push(buildEditActionColumn(cfg));
        return columns;
    }

    function buildSaveDeleteActionColumn(options) {
        var cfg = normalizeColumnOptions(options);
        var saveActionClass = toCssClass(cfg.saveActionClass, "js-tabulator-action-save");
        var deleteActionClass = toCssClass(cfg.deleteActionClass, "js-tabulator-action-delete");
        var saveButtonClass = toCssClass(cfg.saveButtonClass, "btn-primary");
        var deleteButtonClass = toCssClass(cfg.deleteButtonClass, "btn-danger");
        var saveLabel = toButtonLabel(cfg.saveLabel, "Salvar");
        var deleteLabel = toButtonLabel(cfg.deleteLabel, "Excluir");
        var submitPost = typeof cfg.submitPost === "function" ? cfg.submitPost : null;
        var getSaveUrl = typeof cfg.getSaveUrl === "function"
            ? cfg.getSaveUrl
            : function (rowData) { return rowData ? rowData.editar_url : ""; };
        var getDeleteUrl = typeof cfg.getDeleteUrl === "function"
            ? cfg.getDeleteUrl
            : function (rowData) { return rowData ? rowData.excluir_url : ""; };
        var getSavePayload = typeof cfg.getSavePayload === "function"
            ? cfg.getSavePayload
            : function () { return {}; };
        var getDeletePayload = typeof cfg.getDeletePayload === "function"
            ? cfg.getDeletePayload
            : function () { return {}; };
        var onSave = typeof cfg.onSave === "function" ? cfg.onSave : null;
        var onDelete = typeof cfg.onDelete === "function" ? cfg.onDelete : null;
        var getDeleteConfirm = typeof cfg.getDeleteConfirm === "function"
            ? cfg.getDeleteConfirm
            : function (rowData) {
                return resolveRowValue(rowData, cfg.deleteConfirm) || "";
            };
        var column = {
            title: resolveActionColumnTitle(),
            hozAlign: cfg.hozAlign || "center",
            formatter: function () {
                return '<button class="' + saveButtonClass + " " + saveActionClass + '" type="button">' + saveLabel + "</button>"
                    + ' <button class="' + deleteButtonClass + " " + deleteActionClass + '" type="button">' + deleteLabel + "</button>";
            },
            cellClick: function (event, cell) {
                var rowData = cell && cell.getRow ? cell.getRow().getData() : null;
                if (!rowData) return;

                var target = event && event.target;
                var saveTarget = target && target.closest ? target.closest("." + saveActionClass) : null;
                if (saveTarget) {
                    if (onSave) {
                        onSave({ event: event, cell: cell, rowData: rowData });
                        return;
                    }
                    if (!submitPost) return;
                    var saveUrl = getSaveUrl(rowData);
                    if (!saveUrl) return;
                    submitPost(saveUrl, getSavePayload(rowData));
                    return;
                }

                var deleteTarget = target && target.closest ? target.closest("." + deleteActionClass) : null;
                if (!deleteTarget) return;
                if (onDelete) {
                    onDelete({ event: event, cell: cell, rowData: rowData });
                    return;
                }
                if (!submitPost) return;
                var deleteUrl = getDeleteUrl(rowData);
                if (!deleteUrl) return;
                submitPost(deleteUrl, getDeletePayload(rowData), getDeleteConfirm(rowData));
            },
        };

        if (cfg.field) {
            column.field = String(cfg.field);
        }

        if (Number.isFinite(cfg.width)) {
            column.width = cfg.width;
        }

        return column;
    }

    function hasAnyRowAction(data, actionFields) {
        if (!Array.isArray(data) || !data.length) return false;
        var fields = Array.isArray(actionFields) && actionFields.length
            ? actionFields
            : ["editar_url", "excluir_url", "deletar_url"];

        return data.some(function (item) {
            if (!item || typeof item !== "object") return false;
            return fields.some(function (field) {
                return Boolean(item[field]);
            });
        });
    }

    function collectActionFieldsFromColumns(columns) {
        var actionFields = [];
        var leafColumns = collectLeafColumns(columns, []);
        leafColumns.forEach(function (column) {
            if (!column || !column.field) return;
            if (!isActionColumn(column)) return;
            actionFields.push(String(column.field));
        });
        return Array.from(new Set(actionFields));
    }

    function hideEmptyActionColumns(table, config) {
        if (!table || !config) return;
        if (config.keepActionColumnWhenNoRowAction === true) return;

        var data = Array.isArray(config.data) ? config.data : [];
        if (!data.length) return;

        var actionFields = collectActionFieldsFromColumns(config.columns);
        if (!actionFields.length) return;
        if (hasAnyRowAction(data, actionFields)) return;

        actionFields.forEach(function (field) {
            var column = typeof table.getColumn === "function" ? table.getColumn(field) : null;
            if (column && typeof column.hide === "function") {
                column.hide();
            }
        });
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
        hasAnyRowAction: hasAnyRowAction,
        buildEditActionColumn: buildEditActionColumn,
        addEditActionColumnIfAny: addEditActionColumnIfAny,
        buildSaveDeleteActionColumn: buildSaveDeleteActionColumn,
    };

    installGlobalDomStickyWatcher();
})();
