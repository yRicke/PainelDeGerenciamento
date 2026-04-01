(function () {
    var dataElement = document.getElementById("balanco-patrimonial-ativos-tabulator-data");
    var empresasElement = document.getElementById("balanco-patrimonial-ativos-empresas-opcoes-data");
    var categoriasElement = document.getElementById("balanco-patrimonial-ativos-categorias-opcoes-data");
    var statusElement = document.getElementById("balanco-patrimonial-ativos-status-opcoes-data");
    var cadastroForm = document.getElementById("balanco-patrimonial-ativos-cadastro-form");
    var saveStatusEl = document.getElementById("balanco-patrimonial-ativos-save-status");
    var secFiltros = document.getElementById("sec-filtros");
    var filtrosColunaEsquerda = document.getElementById("balanco-ativos-filtros-coluna-esquerda");
    var filtrosColunaDireita = document.getElementById("balanco-ativos-filtros-coluna-direita");
    var categoriaInput = document.getElementById("balanco-ativos-categoria-input");
    var placaInput = document.getElementById("balanco-ativos-placa-input");
    var localInput = document.getElementById("balanco-ativos-local-input");
    var rendaInput = document.getElementById("balanco-ativos-renda-input");
    var anoInput = document.getElementById("balanco-ativos-ano-input");
    var statusFinanciadoInput = document.getElementById("balanco-ativos-status-financiado-input");

    if (!dataElement || !window.Tabulator) return;

    var tabela = null;
    var data = [];
    var seqByRowId = {};
    var internalUpdate = false;
    var externalFilters = null;

    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});
    var empresasValues = {};
    var categoriasValues = {};
    var statusValues = {};

    var MONEY_FIELDS = [
        "renda",
        "valor_bem",
        "valor_real_atual",
        "valor_venda_forcada",
        "valor_declarado_ir",
        "valor_avaliacao",
        "quitacao",
        "alienacao",
        "valor_parcela",
        "passivo",
        "valor_liquido",
    ];
    var FINANCIADO_FIELDS = ["quitacao", "alienacao", "parcelas", "valor_parcela", "passivo"];

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function isEmptyValue(value) {
        return value === null || value === undefined || toText(value) === "";
    }

    function toNumber(value) {
        if (typeof value === "number") return Number.isFinite(value) ? value : 0;
        var text = toText(value);
        if (!text) return 0;
        text = text.replace(/\s+/g, "").replace("R$", "");
        if (text.indexOf(",") >= 0) {
            text = text.replace(/\./g, "").replace(",", ".");
        }
        var parsed = Number(text);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function formatMoney(value) {
        return formatadorMoeda.format(toNumber(value));
    }

    function formatDateIsoToBr(dateIso) {
        var text = toText(dateIso);
        if (!text) return "";
        var parts = text.split("-");
        if (parts.length !== 3) return text;
        return parts[2] + "/" + parts[1] + "/" + parts[0];
    }

    function extractDigits(value) {
        return toText(value).replace(/\D/g, "");
    }

    function digitsToCurrencyText(value) {
        var digits = extractDigits(value);
        if (!digits) return "";

        var cents = Number(digits);
        if (!Number.isFinite(cents)) return "";

        var integer = Math.floor(cents / 100);
        var decimal = String(cents % 100).padStart(2, "0");
        return "R$ " + integer.toLocaleString("pt-BR") + "," + decimal;
    }

    function normalizeCurrencyInputValue(value) {
        var digits = extractDigits(value);
        if (!digits) return "";
        var cents = Number(digits);
        if (!Number.isFinite(cents)) return "";
        return (cents / 100).toFixed(2);
    }

    function placeCaretAtEnd(input) {
        if (!input || typeof input.setSelectionRange !== "function") return;
        var length = input.value.length;
        input.setSelectionRange(length, length);
    }

    function numberToCurrencyText(value) {
        if (isEmptyValue(value)) return "";
        var number = toNumber(value);
        var cents = Math.round(number * 100);
        if (!Number.isFinite(cents)) return "";
        if (cents === 0) return "R$ 0,00";
        return digitsToCurrencyText(String(Math.abs(cents)));
    }

    function parseMoneyFromDataset(value) {
        if (isEmptyValue(value)) return "";
        return toNumber(value);
    }

    function getCookie(name) {
        var cookieValue = null;
        if (!document.cookie) return cookieValue;
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i += 1) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
        return cookieValue;
    }

    function getCsrfToken() {
        var input = document.querySelector("input[name='csrfmiddlewaretoken']");
        return (input ? input.value : "") || getCookie("csrftoken") || "";
    }

    function appendCsrfToken(formData) {
        var token = getCsrfToken();
        if (token) formData.append("csrfmiddlewaretoken", token);
    }

    function parseJsonResponse(response) {
        return response
            .json()
            .catch(function () {
                return {};
            })
            .then(function (body) {
                return {ok: response.ok, body: body};
            });
    }

    function setSaveStatus(text, tone) {
        if (!saveStatusEl) return;
        saveStatusEl.classList.remove(
            "balanco-ativos-save-status--ok",
            "balanco-ativos-save-status--error",
            "balanco-ativos-save-status--progress"
        );
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function isCategoriaVeiculos(value) {
        return toText(value) === "veiculos";
    }

    function isCategoriaImovel(value) {
        return toText(value) === "imovel";
    }

    function isStatusFinanciadoTrue(value) {
        var text = toText(value).toLowerCase();
        return value === true || text === "true" || text === "1" || text === "on" || text === "sim" || text === "verdadeiro";
    }

    function setFieldEnabled(input, enabled) {
        if (!input) return;
        input.disabled = !enabled;
        if (!enabled) input.value = "";
    }

    function toggleCategoryDependentFormFields() {
        var categoria = categoriaInput ? categoriaInput.value : "";
        var veiculos = isCategoriaVeiculos(categoria);
        var imovel = isCategoriaImovel(categoria);
        setFieldEnabled(placaInput, veiculos);
        setFieldEnabled(anoInput, veiculos);
        setFieldEnabled(localInput, imovel);
        setFieldEnabled(rendaInput, imovel);
    }

    function toggleFinanciadoDependentFormFields() {
        if (!cadastroForm || !statusFinanciadoInput) return;
        var financiado = isStatusFinanciadoTrue(statusFinanciadoInput.value);
        FINANCIADO_FIELDS.forEach(function (name) {
            var field = cadastroForm.querySelector("[name='" + name + "']");
            if (!field) return;
            field.disabled = !financiado;
            if (!financiado) {
                field.value = "";
            }
        });
    }

    function applyRulesToRowData(rowData) {
        if (!rowData) return false;

        var changed = false;
        var categoria = toText(rowData.categoria);
        var veiculos = isCategoriaVeiculos(categoria);
        var imovel = isCategoriaImovel(categoria);
        var financiado = isStatusFinanciadoTrue(rowData.status_financiado);

        if (!veiculos) {
            if (toText(rowData.placa) !== "") {
                rowData.placa = "";
                changed = true;
            }
            if (toText(rowData.ano) !== "") {
                rowData.ano = "";
                changed = true;
            }
        }

        if (!imovel) {
            if (toText(rowData.local) !== "") {
                rowData.local = "";
                changed = true;
            }
            if (!isEmptyValue(rowData.renda)) {
                rowData.renda = "";
                changed = true;
            }
        }

        if (!financiado) {
            FINANCIADO_FIELDS.forEach(function (field) {
                if (!isEmptyValue(rowData[field])) {
                    rowData[field] = "";
                    changed = true;
                }
            });
        }

        return changed;
    }

    function updateLocalLabels(rowData) {
        if (!rowData) return;
        var empresaValue = toText(rowData.empresa_bp);
        var categoriaValue = toText(rowData.categoria);
        rowData.empresa_bp_label = empresasValues[empresaValue] || rowData.empresa_bp_label || "";
        rowData.categoria_label = categoriasValues[categoriaValue] || rowData.categoria_label || "";
        rowData.data_aquisicao = formatDateIsoToBr(rowData.data_aquisicao_iso);
        rowData.status_financiado = isStatusFinanciadoTrue(rowData.status_financiado);
        rowData.status_financiado_label = rowData.status_financiado ? "VERDADEIRO" : "FALSO";

        rowData.parcelas = isEmptyValue(rowData.parcelas) ? "" : String(parseInt(rowData.parcelas, 10) || "");

        MONEY_FIELDS.forEach(function (field) {
            rowData[field] = parseMoneyFromDataset(rowData[field]);
        });
    }

    function createFilterDefinitions() {
        return [
            {
                key: "empresa_bp_label",
                label: "Empresa BP",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.empresa_bp_label : "";
                },
            },
            {
                key: "categoria_label",
                label: "Categoria",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.categoria_label : "";
                },
            },
            {
                key: "status",
                label: "Status",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.status : "";
                },
            },
        ];
    }

    function setupExternalFilters() {
        if (!window.ModuleFilterCore || !secFiltros || !filtrosColunaEsquerda || !filtrosColunaDireita) {
            externalFilters = null;
            if (tabela && typeof tabela.refreshFilter === "function") tabela.refreshFilter();
            return;
        }

        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholder = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholder) placeholder.remove();

        externalFilters = window.ModuleFilterCore.create({
            data: data.slice(),
            definitions: createFilterDefinitions(),
            leftColumn: filtrosColunaEsquerda,
            rightColumn: filtrosColunaDireita,
            onChange: function () {
                if (tabela && typeof tabela.refreshFilter === "function") tabela.refreshFilter();
            },
        });

        if (tabela && typeof tabela.refreshFilter === "function") tabela.refreshFilter();
    }

    function matchesGlobalFilters(rowData) {
        if (externalFilters && typeof externalFilters.matchesRecord === "function") {
            return externalFilters.matchesRecord(rowData);
        }
        return true;
    }

    function refreshExternalFilters() {
        setupExternalFilters();
    }

    function bindClearFilterButtons() {
        function clearAll() {
            if (externalFilters && typeof externalFilters.clearAllFilters === "function") {
                externalFilters.clearAllFilters();
            }
            if (tabela && typeof tabela.clearHeaderFilter === "function") {
                tabela.clearHeaderFilter();
            }
            if (tabela && typeof tabela.refreshFilter === "function") {
                tabela.refreshFilter();
            }
        }

        var buttons = document.querySelectorAll(".module-filters-clear-all, .module-shell-clear-filters");
        buttons.forEach(function (button) {
            button.addEventListener("click", clearAll);
        });
    }

    function buildCurrencyCentShiftEditor(cell, onRendered, success, cancel) {
        var input = document.createElement("input");
        input.type = "text";
        input.autocomplete = "off";
        input.className = "tabulator-editing";
        input.style.width = "100%";
        input.style.height = "100%";
        input.style.boxSizing = "border-box";
        input.style.textAlign = "right";
        input.value = numberToCurrencyText(cell.getValue());

        function applyMask() {
            input.value = digitsToCurrencyText(input.value);
            placeCaretAtEnd(input);
        }

        function commit() {
            var normalized = normalizeCurrencyInputValue(input.value);
            if (!normalized) {
                success("");
                return;
            }
            success(Number(normalized));
        }

        input.addEventListener("input", applyMask);
        input.addEventListener("focus", function () {
            placeCaretAtEnd(input);
        });
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                commit();
                return;
            }
            if (event.key === "Escape") {
                event.preventDefault();
                cancel();
            }
        });
        input.addEventListener("blur", commit);

        onRendered(function () {
            input.focus();
            placeCaretAtEnd(input);
        });

        return input;
    }

    function buildMoneyFormatter() {
        return function (cell) {
            var value = cell.getValue();
            if (isEmptyValue(value)) return "";
            return formatMoney(value);
        };
    }

    function moneyPayloadValue(value) {
        if (isEmptyValue(value)) return "";
        return String(toNumber(value).toFixed(2));
    }

    function buildPayloadFromRow(rowData) {
        var payload = {
            empresa_bp: toText(rowData.empresa_bp),
            categoria: toText(rowData.categoria),
            sub_categoria: toText(rowData.sub_categoria),
            secao: toText(rowData.secao),
            nivel: toText(rowData.nivel),
            data_aquisicao: toText(rowData.data_aquisicao_iso),
            patrimonio: toText(rowData.patrimonio),
            placa: toText(rowData.placa),
            local: toText(rowData.local),
            ano: toText(rowData.ano),
            parcelas: toText(rowData.parcelas),
            status_financiado: isStatusFinanciadoTrue(rowData.status_financiado) ? "true" : "false",
            status: toText(rowData.status),
        };

        MONEY_FIELDS.forEach(function (field) {
            payload[field] = moneyPayloadValue(rowData[field]);
        });

        return payload;
    }

    function refreshRowVisual(row) {
        if (!row) return;
        if (typeof row.reformat === "function") {
            row.reformat();
            return;
        }
        if (tabela && typeof tabela.redraw === "function") {
            tabela.redraw(true);
        }
    }

    function rollbackEditedField(row, rowData, field, oldValue) {
        if (!row || !rowData) return;
        var rollbackData = Object.assign({}, rowData);
        if (field) rollbackData[field] = oldValue;
        updateLocalLabels(rollbackData);
        internalUpdate = true;
        Promise.resolve(row.update(rollbackData))
            .finally(function () {
                internalUpdate = false;
                refreshRowVisual(row);
            });
    }

    function saveRowAutomatically(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;
        var rowData = row.getData() || {};
        if (!rowData.editar_url) return;

        var rowId = rowData.id;
        var editedField = typeof cell.getField === "function" ? cell.getField() : "";
        var oldValue = typeof cell.getOldValue === "function" ? cell.getOldValue() : null;
        var currentSeq = Number(seqByRowId[rowId] || 0) + 1;
        seqByRowId[rowId] = currentSeq;

        var payload = buildPayloadFromRow(rowData);
        var formData = new FormData();
        appendCsrfToken(formData);
        Object.keys(payload).forEach(function (key) {
            formData.append(key, payload[key]);
        });

        setSaveStatus("Salvando alteracao...", "balanco-ativos-save-status--progress");

        fetch(rowData.editar_url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (seqByRowId[rowId] !== currentSeq) return;
                if (!result.ok || !result.body || result.body.ok === false || !result.body.registro) {
                    rollbackEditedField(row, rowData, editedField, oldValue);
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao salvar.",
                        "balanco-ativos-save-status--error"
                    );
                    return;
                }

                internalUpdate = true;
                Promise.resolve(row.update(result.body.registro))
                    .then(function () {
                        var updatedRowData = row.getData() || {};
                        updateLocalLabels(updatedRowData);
                        refreshRowVisual(row);

                        var rowIndex = data.findIndex(function (item) {
                            return Number(item.id) === Number(updatedRowData.id);
                        });
                        if (rowIndex >= 0) data[rowIndex] = updatedRowData;

                        refreshExternalFilters();
                        setSaveStatus("Salvo automaticamente.", "balanco-ativos-save-status--ok");
                    })
                    .catch(function () {
                        rollbackEditedField(row, rowData, editedField, oldValue);
                        setSaveStatus("Falha ao aplicar retorno no front.", "balanco-ativos-save-status--error");
                    })
                    .finally(function () {
                        internalUpdate = false;
                    });
            })
            .catch(function () {
                if (seqByRowId[rowId] !== currentSeq) return;
                rollbackEditedField(row, rowData, editedField, oldValue);
                setSaveStatus("Falha ao salvar. Alteracao revertida.", "balanco-ativos-save-status--error");
            });
    }

    function onCellEdited(cell) {
        if (internalUpdate) return;
        var row = cell ? cell.getRow() : null;
        var rowData = row ? row.getData() : null;
        if (!row || !rowData) return;

        var changedByRule = applyRulesToRowData(rowData);
        if (!changedByRule) {
            saveRowAutomatically(cell);
            return;
        }

        internalUpdate = true;
        Promise.resolve(row.update(rowData))
            .then(function () {
                refreshRowVisual(row);
            })
            .finally(function () {
                internalUpdate = false;
                saveRowAutomatically(cell);
            });
    }

    function deleteRowByCell(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;
        var rowData = row.getData() || {};
        if (!rowData.excluir_url) return;
        if (!window.confirm("Excluir registro?")) return;

        var formData = new FormData();
        appendCsrfToken(formData);

        setSaveStatus("Excluindo registro...", "balanco-ativos-save-status--progress");

        fetch(rowData.excluir_url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false) {
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao excluir registro.",
                        "balanco-ativos-save-status--error"
                    );
                    return;
                }

                var idExcluido = Number(rowData.id);
                data = data.filter(function (item) {
                    return Number(item.id) !== idExcluido;
                });

                Promise.resolve(row.delete())
                    .then(function () {
                        refreshExternalFilters();
                        setSaveStatus("Registro excluido e tabela atualizada.", "balanco-ativos-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro excluido, mas houve falha ao atualizar a tabela.",
                            "balanco-ativos-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao excluir registro.", "balanco-ativos-save-status--error");
            });
    }

    function normalizeMoneyInputsInForm(formData) {
        MONEY_FIELDS.forEach(function (field) {
            var currentValue = toText(formData.get(field));
            if (!currentValue) {
                formData.set(field, "");
                return;
            }
            formData.set(field, normalizeCurrencyInputValue(currentValue));
        });
    }

    function submitCreate(event) {
        if (!event || !cadastroForm) return;
        event.preventDefault();

        var url = cadastroForm.getAttribute("action");
        if (!url) return;

        var formData = new FormData(cadastroForm);
        if (!formData.get("csrfmiddlewaretoken")) appendCsrfToken(formData);
        normalizeMoneyInputsInForm(formData);

        setSaveStatus("Criando registro...", "balanco-ativos-save-status--progress");

        fetch(url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false || !result.body.registro) {
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao criar registro.",
                        "balanco-ativos-save-status--error"
                    );
                    return;
                }

                var novoRegistro = result.body.registro;
                updateLocalLabels(novoRegistro);
                data.push(novoRegistro);

                Promise.resolve(tabela.addData([novoRegistro], true))
                    .then(function () {
                        cadastroForm.reset();
                        var moneyInputs = cadastroForm.querySelectorAll(".ativo-money-input");
                        moneyInputs.forEach(function (input) {
                            input.value = "";
                        });
                        if (statusFinanciadoInput) {
                            statusFinanciadoInput.value = "false";
                        }
                        toggleCategoryDependentFormFields();
                        toggleFinanciadoDependentFormFields();
                        refreshExternalFilters();
                        setSaveStatus("Registro criado e tabela atualizada.", "balanco-ativos-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro criado, mas houve falha ao atualizar a tabela.",
                            "balanco-ativos-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao criar registro.", "balanco-ativos-save-status--error");
            });
    }

    function bindMoneyMasks() {
        var inputs = document.querySelectorAll(".ativo-money-input");
        inputs.forEach(function (input) {
            input.addEventListener("input", function () {
                input.value = digitsToCurrencyText(input.value);
                placeCaretAtEnd(input);
            });
            input.addEventListener("blur", function () {
                if (!toText(input.value)) return;
                input.value = digitsToCurrencyText(input.value);
            });
            input.addEventListener("focus", function () {
                if (!toText(input.value)) return;
                placeCaretAtEnd(input);
            });
        });
    }

    try {
        var parsedData = JSON.parse(dataElement.textContent || "[]");
        if (Array.isArray(parsedData)) {
            data = parsedData.map(function (item) {
                var row = {
                    id: item && item.id ? item.id : "",
                    empresa_bp: toText(item && item.empresa_bp),
                    empresa_bp_label: toText(item && item.empresa_bp_label),
                    categoria: toText(item && item.categoria),
                    categoria_label: toText(item && item.categoria_label),
                    sub_categoria: toText(item && item.sub_categoria),
                    secao: toText(item && item.secao),
                    nivel: toText(item && item.nivel),
                    data_aquisicao_iso: toText(item && item.data_aquisicao_iso),
                    patrimonio: toText(item && item.patrimonio),
                    placa: toText(item && item.placa),
                    local: toText(item && item.local),
                    renda: parseMoneyFromDataset(item && item.renda),
                    ano: toText(item && item.ano),
                    valor_bem: parseMoneyFromDataset(item && item.valor_bem),
                    valor_real_atual: parseMoneyFromDataset(item && item.valor_real_atual),
                    valor_venda_forcada: parseMoneyFromDataset(item && item.valor_venda_forcada),
                    valor_declarado_ir: parseMoneyFromDataset(item && item.valor_declarado_ir),
                    valor_avaliacao: parseMoneyFromDataset(item && item.valor_avaliacao),
                    quitacao: parseMoneyFromDataset(item && item.quitacao),
                    alienacao: parseMoneyFromDataset(item && item.alienacao),
                    parcelas: isEmptyValue(item && item.parcelas) ? "" : String(item.parcelas),
                    valor_parcela: parseMoneyFromDataset(item && item.valor_parcela),
                    passivo: parseMoneyFromDataset(item && item.passivo),
                    valor_liquido: parseMoneyFromDataset(item && item.valor_liquido),
                    status_financiado: isStatusFinanciadoTrue(item && item.status_financiado),
                    status_financiado_label: toText(item && item.status_financiado_label),
                    status: toText(item && item.status),
                    editar_url: toText(item && item.editar_url),
                    excluir_url: toText(item && item.excluir_url),
                };
                applyRulesToRowData(row);
                updateLocalLabels(row);
                return row;
            });
        }
    } catch (_error) {
        data = [];
    }

    try {
        var empresasOpcoes = JSON.parse(empresasElement ? empresasElement.textContent : "[]");
        (Array.isArray(empresasOpcoes) ? empresasOpcoes : []).forEach(function (item) {
            var value = toText(item && item.value);
            var label = toText(item && item.label);
            if (!value) return;
            empresasValues[value] = label || value;
        });
    } catch (_error) {
        empresasValues = {};
    }

    try {
        var categoriasOpcoes = JSON.parse(categoriasElement ? categoriasElement.textContent : "[]");
        (Array.isArray(categoriasOpcoes) ? categoriasOpcoes : []).forEach(function (item) {
            var value = toText(item && item.value);
            var label = toText(item && item.label);
            if (!value) return;
            categoriasValues[value] = label || value;
        });
    } catch (_error) {
        categoriasValues = {};
    }

    try {
        var statusOpcoes = JSON.parse(statusElement ? statusElement.textContent : "[]");
        (Array.isArray(statusOpcoes) ? statusOpcoes : []).forEach(function (item) {
            var value = toText(item && item.value);
            var label = toText(item && item.label);
            if (!value) return;
            statusValues[value] = label || value;
        });
    } catch (_error) {
        statusValues = {};
    }

    data.forEach(function (row) {
        var status = toText(row.status);
        if (status && !statusValues[status]) {
            statusValues[status] = status;
        }
    });

    var createTable = (window.TabulatorDefaults && typeof window.TabulatorDefaults.create === "function")
        ? window.TabulatorDefaults.create
        : function (selector, options) { return new window.Tabulator(selector, options); };

    var moneyFormatter = buildMoneyFormatter();

    tabela = createTable("#balanco-patrimonial-ativos-tabulator", {
        data: data,
        columns: [
            {
                title: "Empresa BP",
                field: "empresa_bp",
                editor: "list",
                editorParams: {values: empresasValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var value = toText(row.empresa_bp);
                    return empresasValues[value] || row.empresa_bp_label || value;
                },
                cellEdited: onCellEdited,
                minWidth: 150,
            },
            {
                title: "Categoria",
                field: "categoria",
                editor: "list",
                editorParams: {values: categoriasValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var value = toText(row.categoria);
                    return categoriasValues[value] || row.categoria_label || value;
                },
                cellEdited: onCellEdited,
                minWidth: 150,
            },
            {title: "Sub-Categoria", field: "sub_categoria", editor: "input", cellEdited: onCellEdited, minWidth: 150},
            {title: "Secao", field: "secao", editor: "input", cellEdited: onCellEdited, minWidth: 130},
            {title: "Nivel", field: "nivel", editor: "input", cellEdited: onCellEdited, minWidth: 120},
            {
                title: "Data Aquisicao",
                field: "data_aquisicao_iso",
                editor: "input",
                editorParams: {elementAttributes: {type: "date"}},
                formatter: function (cell) { return formatDateIsoToBr(cell.getValue()); },
                cellEdited: onCellEdited,
                minWidth: 150,
            },
            {title: "Patrimonio", field: "patrimonio", editor: "input", cellEdited: onCellEdited, minWidth: 260},
            {
                title: "Placa",
                field: "placa",
                editor: "input",
                editable: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return isCategoriaVeiculos(row.categoria);
                },
                cellEdited: onCellEdited,
                minWidth: 120,
            },
            {
                title: "Local",
                field: "local",
                editor: "input",
                editable: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return isCategoriaImovel(row.categoria);
                },
                cellEdited: onCellEdited,
                minWidth: 180,
            },
            {
                title: "Renda (R$)",
                field: "renda",
                editor: buildCurrencyCentShiftEditor,
                editable: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return isCategoriaImovel(row.categoria);
                },
                formatter: moneyFormatter,
                hozAlign: "right",
                cellEdited: onCellEdited,
                minWidth: 150,
            },
            {
                title: "Ano",
                field: "ano",
                editor: "input",
                editable: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return isCategoriaVeiculos(row.categoria);
                },
                cellEdited: onCellEdited,
                minWidth: 110,
            },
            {title: "Valor do Bem (R$)", field: "valor_bem", editor: buildCurrencyCentShiftEditor, formatter: moneyFormatter, hozAlign: "right", cellEdited: onCellEdited, minWidth: 160},
            {title: "Valor Real Atual (R$)", field: "valor_real_atual", editor: buildCurrencyCentShiftEditor, formatter: moneyFormatter, hozAlign: "right", cellEdited: onCellEdited, minWidth: 170},
            {title: "Valor Venda Forcada (R$)", field: "valor_venda_forcada", editor: buildCurrencyCentShiftEditor, formatter: moneyFormatter, hozAlign: "right", cellEdited: onCellEdited, minWidth: 190},
            {title: "Valor Declarado IR (R$)", field: "valor_declarado_ir", editor: buildCurrencyCentShiftEditor, formatter: moneyFormatter, hozAlign: "right", cellEdited: onCellEdited, minWidth: 180},
            {title: "Valor Avaliacao (R$)", field: "valor_avaliacao", editor: buildCurrencyCentShiftEditor, formatter: moneyFormatter, hozAlign: "right", cellEdited: onCellEdited, minWidth: 170},
            {
                title: "Quitacao (R$)",
                field: "quitacao",
                editor: buildCurrencyCentShiftEditor,
                editable: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return isStatusFinanciadoTrue(row.status_financiado);
                },
                formatter: moneyFormatter,
                hozAlign: "right",
                cellEdited: onCellEdited,
                minWidth: 150,
            },
            {
                title: "Alienacao (R$)",
                field: "alienacao",
                editor: buildCurrencyCentShiftEditor,
                editable: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return isStatusFinanciadoTrue(row.status_financiado);
                },
                formatter: moneyFormatter,
                hozAlign: "right",
                cellEdited: onCellEdited,
                minWidth: 150,
            },
            {
                title: "Parcelas",
                field: "parcelas",
                editor: "input",
                editable: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return isStatusFinanciadoTrue(row.status_financiado);
                },
                formatter: function (cell) {
                    var value = toText(cell.getValue());
                    return value || "";
                },
                cellEdited: onCellEdited,
                minWidth: 110,
            },
            {
                title: "Valor da Parcela (R$)",
                field: "valor_parcela",
                editor: buildCurrencyCentShiftEditor,
                editable: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return isStatusFinanciadoTrue(row.status_financiado);
                },
                formatter: moneyFormatter,
                hozAlign: "right",
                cellEdited: onCellEdited,
                minWidth: 180,
            },
            {
                title: "Passivo (R$)",
                field: "passivo",
                editor: buildCurrencyCentShiftEditor,
                editable: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return isStatusFinanciadoTrue(row.status_financiado);
                },
                formatter: moneyFormatter,
                hozAlign: "right",
                cellEdited: onCellEdited,
                minWidth: 150,
            },
            {title: "Valor Liquido (R$)", field: "valor_liquido", editor: buildCurrencyCentShiftEditor, formatter: moneyFormatter, hozAlign: "right", cellEdited: onCellEdited, minWidth: 160},
            {
                title: "Status Financiado",
                field: "status_financiado",
                editor: "list",
                editorParams: {
                    values: {"true": "VERDADEIRO", "false": "FALSO"},
                    clearable: false,
                },
                formatter: function (cell) {
                    return isStatusFinanciadoTrue(cell.getValue()) ? "VERDADEIRO" : "FALSO";
                },
                mutatorEdit: function (value) {
                    return isStatusFinanciadoTrue(value);
                },
                cellEdited: onCellEdited,
                minWidth: 170,
            },
            {
                title: "Status",
                field: "status",
                editor: "list",
                editorParams: {
                    values: statusValues,
                    autocomplete: true,
                    listOnEmpty: true,
                    freetext: true,
                    clearable: true,
                },
                cellEdited: onCellEdited,
                minWidth: 150,
            },
            {
                title: "Acoes",
                field: "acoes",
                width: 120,
                headerSort: false,
                hozAlign: "center",
                formatter: function () {
                    return '<button type="button" class="btn-danger">Excluir</button>';
                },
                cellClick: function (event, cell) {
                    event.preventDefault();
                    deleteRowByCell(cell);
                },
            },
        ],
    });

    if (tabela && typeof tabela.setFilter === "function") {
        tabela.setFilter(matchesGlobalFilters);
    }

    if (cadastroForm) cadastroForm.addEventListener("submit", submitCreate);
    if (categoriaInput) categoriaInput.addEventListener("change", toggleCategoryDependentFormFields);
    if (statusFinanciadoInput) statusFinanciadoInput.addEventListener("change", toggleFinanciadoDependentFormFields);

    bindClearFilterButtons();
    bindMoneyMasks();
    toggleCategoryDependentFormFields();
    toggleFinanciadoDependentFormFields();
    setupExternalFilters();
    setSaveStatus("", "");
})();
