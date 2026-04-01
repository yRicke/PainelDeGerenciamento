(function () {
    var configElement = document.getElementById("balanco-patrimonial-config");
    var dataElement = document.getElementById("balanco-patrimonial-tabulator-data");
    var empresasElement = document.getElementById("balanco-patrimonial-empresas-opcoes-data");
    var tiposElement = document.getElementById("balanco-patrimonial-tipo-opcoes-data");
    var cadastroForm = document.getElementById("balanco-patrimonial-cadastro-form");
    var numeroRegistroInput = document.getElementById("balanco-patrimonial-numero-registro");
    var valorCadastroInput = document.getElementById("balanco-patrimonial-valor-input");
    var saveStatusEl = document.getElementById("balanco-patrimonial-save-status");
    var secFiltros = document.getElementById("sec-filtros");
    var filtrosColunaEsquerda = document.getElementById("balanco-filtros-coluna-esquerda");
    var filtrosColunaDireita = document.getElementById("balanco-filtros-coluna-direita");
    var kpiAtivoEl = document.getElementById("balanco-kpi-ativo");
    var kpiPassivoEl = document.getElementById("balanco-kpi-passivo");
    var kpiSaldoEl = document.getElementById("balanco-kpi-saldo");

    if (!dataElement || !empresasElement || !tiposElement || !window.Tabulator) return;

    var tabela = null;
    var data = [];
    var seqByRowId = {};
    var internalUpdate = false;
    var externalFilters = null;

    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});
    var empresasValues = {};
    var tiposValues = {};
    var proximoNumeroRegistro = 1;

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
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
        var number = toNumber(value);
        var cents = Math.round(number * 100);
        if (!Number.isFinite(cents)) return "";
        if (cents === 0) return "R$ 0,00";
        return digitsToCurrencyText(String(Math.abs(cents)));
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
            var value = normalized ? Number(normalized) : 0;
            success(value);
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
            "balanco-patrimonial-save-status--ok",
            "balanco-patrimonial-save-status--error",
            "balanco-patrimonial-save-status--progress"
        );
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function updateNumeroRegistroInput() {
        if (!numeroRegistroInput) return;
        numeroRegistroInput.value = String(proximoNumeroRegistro || "");
    }

    function updateLocalLabels(rowData) {
        if (!rowData) return;
        var empresaValue = toText(rowData.empresa_balanco_patrimonial);
        var tipoValue = toText(rowData.tipo_movimentacao);
        rowData.empresa_balanco_patrimonial_label = empresasValues[empresaValue] || rowData.empresa_balanco_patrimonial_label || "";
        rowData.tipo_movimentacao_label = tiposValues[tipoValue] || rowData.tipo_movimentacao_label || "";
        rowData.data_lancamento = formatDateIsoToBr(rowData.data_lancamento_iso);
        rowData.data_balanco_patrimonial = formatDateIsoToBr(rowData.data_balanco_patrimonial_iso);
        rowData.valor = toNumber(rowData.valor);
    }

    function getVisibleRowsData() {
        if (!tabela || typeof tabela.getData !== "function") return data.slice();
        return tabela.getData("active") || [];
    }

    function updateDashboard(linhas) {
        var ativo = 0;
        var passivo = 0;
        (linhas || []).forEach(function (item) {
            var tipo = toText(item.tipo_movimentacao);
            var valor = toNumber(item.valor);
            if (tipo === "ativo") {
                ativo += valor;
            } else if (tipo === "passivo") {
                passivo += valor;
            }
        });
        var saldo = ativo - passivo;
        if (kpiAtivoEl) kpiAtivoEl.textContent = formatMoney(ativo);
        if (kpiPassivoEl) kpiPassivoEl.textContent = formatMoney(passivo);
        if (kpiSaldoEl) kpiSaldoEl.textContent = formatMoney(saldo);
    }

    function createFilterDefinitions() {
        return [
            {
                key: "empresa_balanco_patrimonial_label",
                label: "Empresa BP",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.empresa_balanco_patrimonial_label : "";
                },
            },
            {
                key: "tipo_movimentacao_label",
                label: "Tipo Movimentacao",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.tipo_movimentacao_label : "";
                },
            },
            {
                key: "descricao",
                label: "Descricao BP",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.descricao : "";
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

    function refreshExternalFiltersAndDashboard() {
        setupExternalFilters();
        updateDashboard(getVisibleRowsData());
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

    function buildPayloadFromRow(rowData) {
        return {
            data_lancamento: toText(rowData.data_lancamento_iso),
            data_balanco_patrimonial: toText(rowData.data_balanco_patrimonial_iso),
            empresa_balanco_patrimonial: toText(rowData.empresa_balanco_patrimonial),
            tipo_movimentacao: toText(rowData.tipo_movimentacao),
            descricao: toText(rowData.descricao),
            valor: String(toNumber(rowData.valor).toFixed(2)),
            observacao: toText(rowData.observacao),
        };
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

        setSaveStatus("Salvando alteracao...", "balanco-patrimonial-save-status--progress");

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
                        "balanco-patrimonial-save-status--error"
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

                        refreshExternalFiltersAndDashboard();
                        setSaveStatus("Salvo automaticamente.", "balanco-patrimonial-save-status--ok");
                    })
                    .catch(function () {
                        rollbackEditedField(row, rowData, editedField, oldValue);
                        setSaveStatus("Falha ao aplicar retorno no front.", "balanco-patrimonial-save-status--error");
                    })
                    .finally(function () {
                        internalUpdate = false;
                    });
            })
            .catch(function () {
                if (seqByRowId[rowId] !== currentSeq) return;
                rollbackEditedField(row, rowData, editedField, oldValue);
                setSaveStatus("Falha ao salvar. Alteracao revertida.", "balanco-patrimonial-save-status--error");
            });
    }

    function onCellEdited(cell) {
        if (internalUpdate) return;
        saveRowAutomatically(cell);
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

        setSaveStatus("Excluindo registro...", "balanco-patrimonial-save-status--progress");

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
                        "balanco-patrimonial-save-status--error"
                    );
                    return;
                }

                var idExcluido = Number(rowData.id);
                data = data.filter(function (item) {
                    return Number(item.id) !== idExcluido;
                });

                if (result.body.proximo_numero_registro) {
                    proximoNumeroRegistro = Number(result.body.proximo_numero_registro) || proximoNumeroRegistro;
                    updateNumeroRegistroInput();
                }

                Promise.resolve(row.delete())
                    .then(function () {
                        refreshExternalFiltersAndDashboard();
                        setSaveStatus("Registro excluido e tabela atualizada.", "balanco-patrimonial-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro excluido, mas houve falha ao atualizar a tabela.",
                            "balanco-patrimonial-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao excluir registro.", "balanco-patrimonial-save-status--error");
            });
    }

    function submitCreate(event) {
        if (!event || !cadastroForm) return;
        event.preventDefault();

        var url = cadastroForm.getAttribute("action");
        if (!url) return;

        var formData = new FormData(cadastroForm);
        if (!formData.get("csrfmiddlewaretoken")) appendCsrfToken(formData);
        formData.set("valor", normalizeCurrencyInputValue(formData.get("valor")));

        setSaveStatus("Criando registro...", "balanco-patrimonial-save-status--progress");

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
                        "balanco-patrimonial-save-status--error"
                    );
                    return;
                }

                var novoRegistro = result.body.registro;
                updateLocalLabels(novoRegistro);
                data.push(novoRegistro);

                if (result.body.proximo_numero_registro) {
                    proximoNumeroRegistro = Number(result.body.proximo_numero_registro) || proximoNumeroRegistro;
                    updateNumeroRegistroInput();
                }

                Promise.resolve(tabela.addData([novoRegistro], true))
                    .then(function () {
                        cadastroForm.reset();
                        if (valorCadastroInput) valorCadastroInput.value = "";
                        refreshExternalFiltersAndDashboard();
                        setSaveStatus("Registro criado e tabela atualizada.", "balanco-patrimonial-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro criado, mas houve falha ao atualizar a tabela.",
                            "balanco-patrimonial-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao criar registro.", "balanco-patrimonial-save-status--error");
            });
    }

    function bindValorMask() {
        if (!valorCadastroInput) return;
        valorCadastroInput.addEventListener("input", function () {
            valorCadastroInput.value = digitsToCurrencyText(valorCadastroInput.value);
            placeCaretAtEnd(valorCadastroInput);
        });
        valorCadastroInput.addEventListener("blur", function () {
            if (!toText(valorCadastroInput.value)) return;
            valorCadastroInput.value = digitsToCurrencyText(valorCadastroInput.value);
        });
        valorCadastroInput.addEventListener("focus", function () {
            if (!toText(valorCadastroInput.value)) return;
            placeCaretAtEnd(valorCadastroInput);
        });
    }

    try {
        var parsedData = JSON.parse(dataElement.textContent || "[]");
        if (Array.isArray(parsedData)) {
            data = parsedData.map(function (item) {
                var row = {
                    id: item && item.id ? item.id : "",
                    numero_registro: item && item.numero_registro ? item.numero_registro : "",
                    data_lancamento_iso: toText(item && item.data_lancamento_iso),
                    data_balanco_patrimonial_iso: toText(item && item.data_balanco_patrimonial_iso),
                    empresa_balanco_patrimonial: toText(item && item.empresa_balanco_patrimonial),
                    empresa_balanco_patrimonial_label: toText(item && item.empresa_balanco_patrimonial_label),
                    tipo_movimentacao: toText(item && item.tipo_movimentacao),
                    tipo_movimentacao_label: toText(item && item.tipo_movimentacao_label),
                    descricao: toText(item && item.descricao),
                    valor: toNumber(item && item.valor),
                    observacao: toText(item && item.observacao),
                    editar_url: toText(item && item.editar_url),
                    excluir_url: toText(item && item.excluir_url),
                };
                updateLocalLabels(row);
                return row;
            });
        }
    } catch (_error) {
        data = [];
    }

    try {
        var empresasOpcoes = JSON.parse(empresasElement.textContent || "[]");
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
        var tiposOpcoes = JSON.parse(tiposElement.textContent || "[]");
        (Array.isArray(tiposOpcoes) ? tiposOpcoes : []).forEach(function (item) {
            var value = toText(item && item.value);
            var label = toText(item && item.label);
            if (!value) return;
            tiposValues[value] = label || value;
        });
    } catch (_error) {
        tiposValues = {};
    }

    proximoNumeroRegistro = Number(
        configElement ? configElement.getAttribute("data-proximo-numero-registro") : "1"
    ) || 1;
    updateNumeroRegistroInput();

    var createTable = (window.TabulatorDefaults && typeof window.TabulatorDefaults.create === "function")
        ? window.TabulatorDefaults.create
        : function (selector, options) { return new window.Tabulator(selector, options); };

    tabela = createTable("#balanco-patrimonial-tabulator", {
        data: data,
        columns: [
            {title: "Numero Registro", field: "numero_registro", width: 150, hozAlign: "center"},
            {
                title: "Data Lancamento",
                field: "data_lancamento_iso",
                editor: "input",
                editorParams: {
                    elementAttributes: {type: "date"},
                },
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
                cellEdited: onCellEdited,
                minWidth: 150,
            },
            {
                title: "Data BP",
                field: "data_balanco_patrimonial_iso",
                editor: "input",
                editorParams: {
                    elementAttributes: {type: "date"},
                },
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
                cellEdited: onCellEdited,
                minWidth: 130,
            },
            {
                title: "Empresa BP",
                field: "empresa_balanco_patrimonial",
                editor: "list",
                editorParams: {
                    values: empresasValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var value = toText(row.empresa_balanco_patrimonial);
                    return empresasValues[value] || row.empresa_balanco_patrimonial_label || value;
                },
                cellEdited: onCellEdited,
                minWidth: 210,
            },
            {
                title: "Tipo Movimentacao",
                field: "tipo_movimentacao",
                editor: "list",
                editorParams: {
                    values: tiposValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var value = toText(row.tipo_movimentacao);
                    return tiposValues[value] || row.tipo_movimentacao_label || value;
                },
                cellEdited: onCellEdited,
                minWidth: 180,
            },
            {
                title: "Descricao BP",
                field: "descricao",
                editor: "input",
                cellEdited: onCellEdited,
                minWidth: 260,
            },
            {
                title: "Valor(R$)",
                field: "valor",
                editor: buildCurrencyCentShiftEditor,
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
                },
                cellEdited: onCellEdited,
                minWidth: 150,
            },
            {
                title: "Observacao",
                field: "observacao",
                editor: "input",
                cellEdited: onCellEdited,
                minWidth: 220,
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
    if (tabela && typeof tabela.on === "function") {
        tabela.on("dataFiltered", function (_filters, rows) {
            var linhas = (rows || []).map(function (row) { return row.getData(); });
            updateDashboard(linhas);
        });
    }

    if (cadastroForm) cadastroForm.addEventListener("submit", submitCreate);
    bindClearFilterButtons();
    bindValorMask();
    setupExternalFilters();
    updateDashboard(getVisibleRowsData());
    setSaveStatus("", "");
})();
