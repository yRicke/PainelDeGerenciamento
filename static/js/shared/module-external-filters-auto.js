(function () {
    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function stripHtml(value) {
        return toText(value).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    }

    function normalizeText(value) {
        return toText(value)
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    function collectLeafColumns(columns, output) {
        var target = Array.isArray(output) ? output : [];
        if (!Array.isArray(columns)) return target;

        columns.forEach(function (column) {
            if (!column) return;
            if (Array.isArray(column.columns) && column.columns.length) {
                collectLeafColumns(column.columns, target);
                return;
            }
            target.push(column);
        });

        return target;
    }

    function isActionColumn(column) {
        if (!column) return false;
        var field = toText(column.field).toLowerCase();
        var title = normalizeText(stripHtml(column.title));

        if (field.indexOf("_url") >= 0) return true;
        if (field === "acoes" || field === "acao") return true;
        if (title === "acoes" || title === "acao") return true;
        return false;
    }

    function shouldSkipField(field) {
        var normalized = toText(field).toLowerCase();
        if (!normalized) return true;
        if (/_url$/.test(normalized)) return true;
        if (/_sort$/.test(normalized)) return true;
        if (/_ts$/.test(normalized)) return true;
        return false;
    }

    function looksLikeDate(field, label) {
        var token = normalizeText(field + " " + label);
        return token.indexOf("data") >= 0 || token.indexOf("dt") >= 0;
    }

    function looksLikeCurrency(field, label) {
        var token = normalizeText(field + " " + label);
        return token.indexOf("valor") >= 0
            || token.indexOf("custo") >= 0
            || token.indexOf("vlr") >= 0
            || token.indexOf("preco") >= 0
            || token.indexOf("receita") >= 0;
    }

    function formatDateIso(value) {
        var raw = toText(value);
        if (!raw) return "(Vazio)";
        if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
        var parts = raw.split("-");
        return parts[2] + "/" + parts[1] + "/" + parts[0];
    }

    function formatOptionValue(field, label, value) {
        if (value === null || value === undefined || value === "") return "(Vazio)";
        if (typeof value === "boolean") return value ? "Sim" : "Nao";
        if (looksLikeDate(field, label)) return formatDateIso(value);

        if (typeof value === "number" && Number.isFinite(value)) {
            if (looksLikeCurrency(field, label)) {
                return value.toLocaleString("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                });
            }
            return value.toLocaleString("pt-BR", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 3,
            });
        }

        return toText(value) || "(Vazio)";
    }

    function buildDefinitions(entry) {
        var config = entry && entry.config ? entry.config : {};
        var leafColumns = collectLeafColumns(config.columns, []);
        var definitions = [];
        var seen = new Set();

        leafColumns.forEach(function (column) {
            if (!column || !column.field) return;
            if (column.visible === false && column.externalFilter !== true) return;
            if (isActionColumn(column)) return;

            var field = toText(column.field);
            if (shouldSkipField(field)) return;
            if (seen.has(field)) return;

            var label = stripHtml(column.title) || field;
            definitions.push({
                key: field,
                label: label,
                formatValue: function (value) {
                    return formatOptionValue(field, label, value);
                },
            });
            seen.add(field);
        });

        return definitions;
    }

    function findFiltersSection(entry) {
        var tableElement = entry && entry.element ? entry.element : null;
        if (tableElement) {
            var shell = tableElement.closest(".module-shell");
            if (shell) {
                var shellSection = shell.querySelector("#sec-filtros");
                if (shellSection) return shellSection;
            }
        }
        return document.getElementById("sec-filtros");
    }

    function isManualFiltersSection(section) {
        if (!section) return true;
        var manual = normalizeText(section.dataset.moduleFiltersManual);
        var auto = normalizeText(section.dataset.moduleFiltersAuto);
        return manual === "true" || auto === "off";
    }

    function ensureFilterColumns(section) {
        if (!section) return null;

        var left = section.querySelector('[data-module-filter-column="left"]')
            || section.querySelector("#vendas-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#vendas-filtros-coluna-direita");

        if (left && right) {
            return {left: left, right: right};
        }

        var wrapper = section.querySelector(".module-filter-columns");
        if (!wrapper) {
            wrapper = document.createElement("div");
            wrapper.className = "module-filter-columns";
            section.appendChild(wrapper);
        }

        if (!left) {
            left = document.createElement("div");
            left.className = "module-filter-column";
            left.setAttribute("data-module-filter-column", "left");
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    function resolveSourceData(entry) {
        if (entry && entry.sourceConfig && Array.isArray(entry.sourceConfig.data)) {
            return entry.sourceConfig.data;
        }
        if (entry && entry.config && Array.isArray(entry.config.data)) {
            return entry.config.data;
        }
        if (entry && entry.table && typeof entry.table.getData === "function") {
            var liveData = entry.table.getData();
            if (Array.isArray(liveData)) return liveData;
        }
        return [];
    }

    function clearAllFilters(filterCore, table) {
        if (filterCore && typeof filterCore.clearAllFilters === "function") {
            filterCore.clearAllFilters();
        }

        if (table && typeof table.clearHeaderFilter === "function") {
            table.clearHeaderFilter();
        }

        if (table && typeof table.refreshFilter === "function") {
            table.refreshFilter();
        }
    }

    function bindClearAction(button, datasetKey, handler) {
        if (!button || !datasetKey || typeof handler !== "function") return;
        if (button.dataset[datasetKey] === "1") return;
        button.dataset[datasetKey] = "1";
        button.addEventListener("click", handler);
    }

    function bindClearButton(section, filterCore, table) {
        if (!section || !filterCore || !table) return;

        var button = section.querySelector(".module-filters-clear-all");
        if (!button) {
            var head = section.querySelector(".module-shell-side-panel-head");
            if (head) {
                button = document.createElement("button");
                button.type = "button";
                button.className = "btn-light module-filters-clear-all";
                button.textContent = "Limpar filtros";
                head.appendChild(button);
            }
        }
        bindClearAction(button, "moduleFilterClearBound", function () {
            clearAllFilters(filterCore, table);
        });
    }

    function bindToolbarClearButton(section, filterCore, table, entry) {
        if (!filterCore || !table) return;

        var shell = null;
        if (section && typeof section.closest === "function") {
            shell = section.closest(".module-shell");
        }
        if (!shell && entry && entry.element && typeof entry.element.closest === "function") {
            shell = entry.element.closest(".module-shell");
        }
        if (!shell) return;

        var button = shell.querySelector(".module-shell-clear-filters");
        bindClearAction(button, "moduleFilterToolbarClearBound", function () {
            clearAllFilters(filterCore, table);
        });
    }

    function attachAutoFilters(entry) {
        if (!entry || !entry.table) return;
        if (entry.table.__moduleExternalFiltersAttached) return;
        if (!window.ModuleFilterCore || typeof window.ModuleFilterCore.create !== "function") return;

        var section = findFiltersSection(entry);
        if (!section || isManualFiltersSection(section)) return;
        if (section.dataset.moduleFiltersBound === "1") return;

        var columns = ensureFilterColumns(section);
        if (!columns || !columns.left || !columns.right) return;

        var definitions = buildDefinitions(entry);
        if (!definitions.length) return;

        var placeholder = section.querySelector(".module-filters-placeholder");
        if (placeholder) placeholder.remove();

        var core = window.ModuleFilterCore.create({
            data: resolveSourceData(entry),
            definitions: definitions,
            leftColumn: columns.left,
            rightColumn: columns.right,
            onChange: function () {
                if (typeof entry.table.refreshFilter === "function") {
                    entry.table.refreshFilter();
                }
            },
        });

        entry.table.addFilter(function (rowData) {
            return core.matchesRecord(rowData);
        });

        bindClearButton(section, core, entry.table);
        bindToolbarClearButton(section, core, entry.table, entry);
        section.dataset.moduleFiltersBound = "1";
        entry.table.__moduleExternalFiltersAttached = true;
    }

    function setupAutoFilters() {
        if (!window.TabulatorDefaults || typeof window.TabulatorDefaults.onTableCreated !== "function") {
            return;
        }

        window.TabulatorDefaults.onTableCreated(function (entry) {
            attachAutoFilters(entry);
        }, {emitExisting: true});
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupAutoFilters);
    } else {
        setupAutoFilters();
    }
})();
