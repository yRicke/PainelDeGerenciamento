(function () {
    var EMPTY_VALUE_TOKEN = "__moduleFilterEmptyValue__";

    function isArray(value) {
        return Array.isArray(value);
    }

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function normalizeLabel(value) {
        var text = toText(value);
        return text || "(Vazio)";
    }

    function defaultSortByLabel(a, b) {
        return String(a.label || "").localeCompare(String(b.label || ""), "pt-BR", {
            sensitivity: "base",
            numeric: true,
        });
    }

    function toToken(value) {
        if (value === null || value === undefined || value === "") {
            return EMPTY_VALUE_TOKEN;
        }
        return String(value);
    }

    function createDefinition(rawDef) {
        var def = rawDef || {};
        var key = toText(def.key);
        if (!key) {
            throw new Error("Filtro externo sem chave (key).");
        }
        var label = toText(def.label) || key;
        var extractValue = typeof def.extractValue === "function"
            ? def.extractValue
            : function (rowData) {
                return rowData ? rowData[key] : "";
            };
        var formatValue = typeof def.formatValue === "function"
            ? def.formatValue
            : function (value) {
                return normalizeLabel(value);
            };
        var sortOptions = typeof def.sortOptions === "function" ? def.sortOptions : defaultSortByLabel;
        var singleSelect = def.singleSelect === true;

        return {
            key: key,
            label: label,
            extractValue: extractValue,
            formatValue: formatValue,
            sortOptions: sortOptions,
            singleSelect: singleSelect,
        };
    }

    function buildOptions(data, definition) {
        var map = new Map();
        (isArray(data) ? data : []).forEach(function (rowData) {
            var rawValue = definition.extractValue(rowData);
            var token = toToken(rawValue);
            if (map.has(token)) return;
            map.set(token, {
                token: token,
                value: rawValue,
                label: normalizeLabel(definition.formatValue(rawValue, rowData)),
            });
        });
        var options = Array.from(map.values());
        options.sort(definition.sortOptions);
        return options;
    }

    function cloneStateSet(set) {
        return new Set(Array.from(set || []));
    }

    function ExternalFilterCore(config) {
        var cfg = config || {};
        this.data = isArray(cfg.data) ? cfg.data : [];
        this.onChange = typeof cfg.onChange === "function" ? cfg.onChange : function () {};
        this.leftColumn = cfg.leftColumn || null;
        this.rightColumn = cfg.rightColumn || null;
        this.emptyStateText = toText(cfg.emptyStateText) || "Sem opções para este filtro.";
        this.definitions = [];
        this.definitionByKey = {};
        this.optionsByKey = {};
        this.selectedTokensByKey = {};
        this.lastChangeMeta = null;

        var rawDefinitions = isArray(cfg.definitions) ? cfg.definitions : [];
        this.definitions = rawDefinitions.map(createDefinition);
        this.definitions.forEach(function (definition) {
            this.definitionByKey[definition.key] = definition;
        }, this);

        this.definitions.forEach(function (definition) {
            this.selectedTokensByKey[definition.key] = new Set();
        }, this);

        this._rebuildOptionsByCurrentSelections();
        this.render();
    }

    ExternalFilterCore.prototype._matchesRecordAgainstSelections = function (rowData, ignoreFilterKey) {
        var self = this;
        return this.definitions.every(function (definition) {
            if (definition.key === ignoreFilterKey) return true;
            var selectedTokens = self.selectedTokensByKey[definition.key];
            // Empty selection means "no constraint" for this filter.
            if (!selectedTokens || selectedTokens.size === 0) return true;
            var value = definition.extractValue(rowData);
            var token = toToken(value);
            return selectedTokens.has(token);
        });
    };

    ExternalFilterCore.prototype._rebuildOptionsByCurrentSelections = function () {
        var self = this;
        var rebuilt = {};

        this.definitions.forEach(function (definition) {
            var scopedData = self.data.filter(function (rowData) {
                return self._matchesRecordAgainstSelections(rowData, definition.key);
            });
            rebuilt[definition.key] = buildOptions(scopedData, definition);
        });

        this.optionsByKey = rebuilt;

        // Keep selections only when they are still possible with the other filters.
        this.definitions.forEach(function (definition) {
            var key = definition.key;
            var current = self.selectedTokensByKey[key] || new Set();
            var allowed = new Set((self.optionsByKey[key] || []).map(function (option) { return option.token; }));
            var next = new Set();
            current.forEach(function (token) {
                if (allowed.has(token)) next.add(token);
            });
            if (definition.singleSelect && next.size > 1) {
                var first = next.values().next();
                next = first && !first.done ? new Set([first.value]) : new Set();
            }
            self.selectedTokensByKey[key] = next;
        });
    };

    ExternalFilterCore.prototype._emitChange = function (meta) {
        this.lastChangeMeta = meta || null;
        this.onChange(this);
    };

    ExternalFilterCore.prototype._getDefinitionByKey = function (filterKey) {
        return this.definitionByKey[filterKey] || null;
    };

    ExternalFilterCore.prototype._hasOptionToken = function (filterKey, token) {
        var options = this.optionsByKey[filterKey] || [];
        return options.some(function (item) { return item.token === token; });
    };

    ExternalFilterCore.prototype.getSelectedCount = function (filterKey) {
        var set = this.selectedTokensByKey[filterKey];
        return set ? set.size : 0;
    };

    ExternalFilterCore.prototype.getTotalCount = function (filterKey) {
        var options = this.optionsByKey[filterKey];
        return isArray(options) ? options.length : 0;
    };

    ExternalFilterCore.prototype.isSelected = function (filterKey, token) {
        var set = this.selectedTokensByKey[filterKey];
        return Boolean(set && set.has(token));
    };

    ExternalFilterCore.prototype.selectAllFilter = function (filterKey, shouldEmit) {
        var definition = this._getDefinitionByKey(filterKey);
        if (definition && definition.singleSelect) {
            this.selectedTokensByKey[filterKey] = new Set();
            if (shouldEmit !== false) {
                this.render();
                this._emitChange({ type: "select-all", filterKey: filterKey });
            }
            return;
        }

        var options = this.optionsByKey[filterKey] || [];
        var nextSet = new Set(options.map(function (item) { return item.token; }));
        this.selectedTokensByKey[filterKey] = nextSet;
        if (shouldEmit !== false) {
            this.render();
            this._emitChange({ type: "select-all", filterKey: filterKey });
        }
    };

    ExternalFilterCore.prototype.clearFilter = function (filterKey, shouldEmit) {
        this.selectedTokensByKey[filterKey] = new Set();
        if (shouldEmit !== false) {
            this.render();
            this._emitChange({ type: "clear-filter", filterKey: filterKey });
        }
    };

    ExternalFilterCore.prototype.toggleOption = function (filterKey, token) {
        if (!this._hasOptionToken(filterKey, token)) return;
        var definition = this._getDefinitionByKey(filterKey);
        var set = cloneStateSet(this.selectedTokensByKey[filterKey]);
        if (definition && definition.singleSelect) {
            if (set.has(token)) {
                set = new Set();
            } else {
                set = new Set([token]);
            }
        } else {
            if (set.has(token)) {
                set.delete(token);
            } else {
                set.add(token);
            }
        }
        this.selectedTokensByKey[filterKey] = set;
        this.render();
        this._emitChange({ type: "toggle-option", filterKey: filterKey, token: token });
    };

    ExternalFilterCore.prototype.selectAllFilters = function () {
        var self = this;
        this.definitions.forEach(function (definition) {
            self.selectAllFilter(definition.key, false);
        });
        this.render();
        this._emitChange({ type: "select-all-filters" });
    };

    ExternalFilterCore.prototype.clearAllFilters = function () {
        var self = this;
        this.definitions.forEach(function (definition) {
            self.clearFilter(definition.key, false);
        });
        this.render();
        this._emitChange({ type: "clear-all-filters" });
    };

    ExternalFilterCore.prototype.matchesRecord = function (rowData) {
        return this._matchesRecordAgainstSelections(rowData, "");
    };

    ExternalFilterCore.prototype.getFilteredData = function () {
        var self = this;
        return this.data.filter(function (rowData) {
            return self.matchesRecord(rowData);
        });
    };

    ExternalFilterCore.prototype._renderCard = function (definition) {
        var self = this;
        var filterKey = definition.key;
        var options = this.optionsByKey[filterKey] || [];
        var selectedTokens = this.selectedTokensByKey[filterKey] || new Set();

        var card = document.createElement("article");
        card.className = "module-filter-card";
        card.setAttribute("data-filter-key", filterKey);

        var head = document.createElement("div");
        head.className = "module-filter-card-head";

        var title = document.createElement("h3");
        title.textContent = definition.label;
        head.appendChild(title);

        var actions = document.createElement("div");
        actions.className = "module-filter-card-actions";

        var selectAllBtn = document.createElement("button");
        selectAllBtn.type = "button";
        selectAllBtn.textContent = "Todos";
        selectAllBtn.addEventListener("click", function () {
            self.selectAllFilter(filterKey);
        });

        var clearBtn = document.createElement("button");
        clearBtn.type = "button";
        clearBtn.textContent = "Limpar";
        clearBtn.addEventListener("click", function () {
            self.clearFilter(filterKey);
        });

        actions.appendChild(selectAllBtn);
        actions.appendChild(clearBtn);
        head.appendChild(actions);
        card.appendChild(head);

        var meta = document.createElement("p");
        meta.className = "module-filter-card-meta";
        meta.textContent = selectedTokens.size + " selecionado(s) de " + options.length;
        card.appendChild(meta);

        var optionsWrap = document.createElement("div");
        optionsWrap.className = "module-filter-card-options";

        if (!options.length) {
            var empty = document.createElement("span");
            empty.className = "module-filter-card-meta";
            empty.textContent = this.emptyStateText;
            optionsWrap.appendChild(empty);
        } else {
            options.forEach(function (option) {
                var chip = document.createElement("button");
                chip.type = "button";
                chip.className = "module-filter-chip";
                if (selectedTokens.has(option.token)) {
                    chip.classList.add("is-active");
                    chip.setAttribute("aria-pressed", "true");
                } else {
                    chip.setAttribute("aria-pressed", "false");
                }
                chip.textContent = option.label;
                chip.title = option.label;
                chip.addEventListener("click", function () {
                    self.toggleOption(filterKey, option.token);
                });
                optionsWrap.appendChild(chip);
            });
        }

        card.appendChild(optionsWrap);
        return card;
    };

    ExternalFilterCore.prototype._captureOptionsScrollByFilterKey = function () {
        var positions = {};
        var roots = [this.leftColumn, this.rightColumn];

        roots.forEach(function (root) {
            if (!root || typeof root.querySelectorAll !== "function") return;
            root.querySelectorAll(".module-filter-card[data-filter-key]").forEach(function (card) {
                var filterKey = toText(card.getAttribute("data-filter-key"));
                if (!filterKey) return;
                var optionsWrap = card.querySelector(".module-filter-card-options");
                if (!optionsWrap) return;
                positions[filterKey] = Number(optionsWrap.scrollTop || 0);
            });
        });

        return positions;
    };

    ExternalFilterCore.prototype.render = function () {
        if (!this.leftColumn || !this.rightColumn) return;
        var optionsScrollByFilterKey = this._captureOptionsScrollByFilterKey();
        this._rebuildOptionsByCurrentSelections();
        this.leftColumn.innerHTML = "";
        this.rightColumn.innerHTML = "";

        var leftSize = Math.ceil(this.definitions.length / 2);
        var self = this;
        this.definitions.forEach(function (definition, index) {
            var card = self._renderCard(definition);
            if (index < leftSize) {
                self.leftColumn.appendChild(card);
            } else {
                self.rightColumn.appendChild(card);
            }

            var previousScroll = Number(optionsScrollByFilterKey[definition.key] || 0);
            if (!previousScroll) return;
            var optionsWrap = card.querySelector(".module-filter-card-options");
            if (optionsWrap) {
                optionsWrap.scrollTop = previousScroll;
            }
        });
    };

    window.ModuleFilterCore = {
        create: function (config) {
            return new ExternalFilterCore(config || {});
        },
    };
})();
