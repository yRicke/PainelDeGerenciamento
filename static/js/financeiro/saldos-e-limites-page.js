(function () {
    var dataElement = document.getElementById("saldos-limites-tabulator-data");
    var empresasElement = document.getElementById("saldos-limites-empresas-opcoes-data");
    var contasElement = document.getElementById("saldos-limites-contas-opcoes-data");
    var tiposElement = document.getElementById("saldos-limites-tipos-opcoes-data");
    var ultimaDataElement = document.getElementById("saldos-limites-ultima-data-iso");
    var cadastroForm = document.getElementById("saldos-limites-cadastro-form");
    var cadastroTitularSelect = cadastroForm
        ? cadastroForm.querySelector('select[name="empresa_titular_id"]')
        : null;
    var cadastroContaSelect = cadastroForm
        ? cadastroForm.querySelector('select[name="conta_bancaria_id"]')
        : null;
    var saveStatusEl = document.getElementById("saldos-limites-save-status");

    if (
        !dataElement ||
        !empresasElement ||
        !contasElement ||
        !tiposElement ||
        !cadastroForm ||
        !window.Tabulator ||
        !window.TabulatorDefaults
    ) {
        return;
    }

    var tabela = null;
    var seqByRowId = {};
    var internalUpdate = false;
    var externalFilters = null;
    var selectedDateIso = "";

    var data = JSON.parse(dataElement.textContent || "[]");
    var empresasOpcoes = JSON.parse(empresasElement.textContent || "[]");
    var contasOpcoes = JSON.parse(contasElement.textContent || "[]");
    var tiposOpcoes = JSON.parse(tiposElement.textContent || "[]");
    var ultimaDataIso = "";
    try {
        ultimaDataIso = JSON.parse(ultimaDataElement ? (ultimaDataElement.textContent || "\"\"") : "\"\"");
    } catch (_error) {
        ultimaDataIso = "";
    }

    var filtroDataInput = document.getElementById("saldos-limites-data-filtro");
    var btnUltimaData = document.getElementById("saldos-limites-btn-ultima-data");
    var btnLimparData = document.getElementById("saldos-limites-btn-limpar-data");
    var secFiltros = document.getElementById("sec-filtros");
    var filtrosColunaEsquerda = document.getElementById("saldos-filtros-coluna-esquerda");
    var filtrosColunaDireita = document.getElementById("saldos-filtros-coluna-direita");
    var kpiLimiteInicialEl = document.getElementById("saldos-kpi-limite-inicial");
    var kpiLimiteFinalEl = document.getElementById("saldos-kpi-limite-final");
    var kpiLimitesTotalEl = document.getElementById("saldos-kpi-limites-total");
    var kpiSaldoInicialEl = document.getElementById("saldos-kpi-saldo-inicial");
    var kpiSaldoFinalEl = document.getElementById("saldos-kpi-saldo-final");
    var kpiSaldosTotalEl = document.getElementById("saldos-kpi-saldos-total");
    var kpiAntecipacoesEl = document.getElementById("saldos-kpi-antecipacoes");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});

    var empresasValues = {};
    var empresasLabelById = {};
    var contasValues = {};
    var contasById = {};
    var tiposValues = {};

    empresasOpcoes.forEach(function (item) {
        var id = String(item.id || "");
        var label = String(item.label || "").trim();
        if (!id) return;
        empresasValues[id] = label;
        empresasLabelById[id] = label;
    });

    contasOpcoes.forEach(function (item) {
        var id = String(item.id || "");
        var label = String(item.label || "").trim();
        var banco = String(item.banco || "").trim();
        var titularId = String(item.empresa_titular_id || "");
        if (!id) return;
        contasValues[id] = banco ? (banco + " | " + label) : label;
        contasById[id] = {
            empresa_titular_id: titularId,
            label: label,
            banco: banco,
        };
    });

    tiposOpcoes.forEach(function (item) {
        var value = String(item.value || "").trim();
        var label = String(item.label || "").trim();
        if (!value) return;
        tiposValues[value] = label || value;
    });

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function toNumber(value) {
        if (typeof value === "number") {
            return Number.isFinite(value) ? value : 0;
        }
        var text = toText(value);
        if (!text) return 0;
        text = text.replace(/\s+/g, "").replace("R$", "");
        if (text.indexOf(",") >= 0) {
            text = text.replace(/\./g, "").replace(",", ".");
        }
        var parsed = Number(text);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function formatDateIsoToBr(dateIso) {
        var text = toText(dateIso);
        if (!text) return "";
        var parts = text.split("-");
        if (parts.length !== 3) return text;
        return parts[2] + "/" + parts[1] + "/" + parts[0];
    }

    function formatMoney(value) {
        return formatadorMoeda.format(toNumber(value));
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
            "saldos-limites-save-status--ok",
            "saldos-limites-save-status--error",
            "saldos-limites-save-status--progress"
        );
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function buildPayloadFromRow(rowData) {
        return {
            data: toText(rowData.data_iso),
            empresa_titular_id: toText(rowData.empresa_titular_id),
            conta_bancaria_id: toText(rowData.conta_bancaria_id),
            tipo_movimentacao: toText(rowData.tipo_movimentacao),
            valor_atual: toText(rowData.valor_atual),
        };
    }

    function updateLocalLabels(rowData) {
        var titularId = String(rowData.empresa_titular_id || "");
        var contaId = String(rowData.conta_bancaria_id || "");
        var tipo = String(rowData.tipo_movimentacao || "");
        rowData.empresa_titular_label = empresasLabelById[titularId] || "";
        rowData.tipo_movimentacao_label = tiposValues[tipo] || tipo;
        if (contasById[contaId]) {
            rowData.conta_label = contasById[contaId].label || "";
            rowData.banco = contasById[contaId].banco || "";
        }
        rowData.data = formatDateIsoToBr(rowData.data_iso);
    }

    function restoreCellValue(cell, oldValue) {
        if (!cell) return;
        if (typeof cell.restoreOldValue === "function") {
            cell.restoreOldValue();
            return;
        }
        internalUpdate = true;
        cell.setValue(oldValue, true);
        internalUpdate = false;
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
        if (field) {
            rollbackData[field] = oldValue;
        }
        updateLocalLabels(rollbackData);
        internalUpdate = true;
        Promise.resolve(row.update(rollbackData))
            .catch(function () {
                if (field) {
                    restoreCellValue(row.getCell(field), oldValue);
                }
            })
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
        var currentSeq = Number(seqByRowId[rowId] || 0) + 1;
        seqByRowId[rowId] = currentSeq;

        var oldValue = typeof cell.getOldValue === "function" ? cell.getOldValue() : null;
        var payload = buildPayloadFromRow(rowData);
        var formData = new FormData();
        appendCsrfToken(formData);
        Object.keys(payload).forEach(function (key) {
            formData.append(key, payload[key]);
        });

        setSaveStatus("Salvando alteracao...", "saldos-limites-save-status--progress");

        var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
        var timeoutId = null;
        if (controller && typeof window.setTimeout === "function") {
            timeoutId = window.setTimeout(function () {
                controller.abort();
            }, 15000);
        }

        var fetchOptions = {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        };
        if (controller) {
            fetchOptions.signal = controller.signal;
        }

        fetch(rowData.editar_url, fetchOptions)
            .then(parseJsonResponse)
            .then(function (result) {
                if (seqByRowId[rowId] !== currentSeq) return;

                if (!result.ok || !result.body || result.body.ok === false || !result.body.registro) {
                    rollbackEditedField(row, rowData, editedField, oldValue);
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao salvar.",
                        "saldos-limites-save-status--error"
                    );
                    return;
                }

                internalUpdate = true;
                Promise.resolve(row.update(result.body.registro))
                    .then(function () {
                        var updatedRowData = row.getData() || {};
                        updateLocalLabels(updatedRowData);

                        var tipoCell = typeof row.getCell === "function" ? row.getCell("tipo_movimentacao") : null;
                        if (tipoCell && typeof tipoCell.setValue === "function") {
                            tipoCell.setValue(toText(updatedRowData.tipo_movimentacao), true);
                        }

                        refreshRowVisual(row);
                        var rowIndex = data.findIndex(function (item) {
                            return Number(item.id) === Number(result.body.registro.id);
                        });
                        if (rowIndex >= 0) {
                            data[rowIndex] = updatedRowData;
                        }
                        rebuildExternalFiltersByDate();
                        updateDashboard(getVisibleRowsData());
                        setSaveStatus("Salvo automaticamente.", "saldos-limites-save-status--ok");
                    })
                    .catch(function () {
                        rollbackEditedField(row, rowData, editedField, oldValue);
                        setSaveStatus("Falha ao aplicar retorno no front.", "saldos-limites-save-status--error");
                    })
                    .finally(function () {
                        internalUpdate = false;
                    });
                return;
            })
            .catch(function (error) {
                if (seqByRowId[rowId] !== currentSeq) return;
                rollbackEditedField(row, rowData, editedField, oldValue);
                if (error && error.name === "AbortError") {
                    setSaveStatus("Tempo de resposta excedido ao salvar. Alteracao revertida.", "saldos-limites-save-status--error");
                    return;
                }
                setSaveStatus("Falha ao salvar. Alteracao revertida.", "saldos-limites-save-status--error");
            })
            .finally(function () {
                if (timeoutId) {
                    window.clearTimeout(timeoutId);
                }
            });
    }

    function onCellEdited(cell) {
        if (internalUpdate) return;
        saveRowAutomatically(cell);
    }

    function getDataScopedByDate() {
        if (!selectedDateIso) return data.slice();
        return data.filter(function (rowData) {
            return toText(rowData.data_iso) === selectedDateIso;
        });
    }

    function createFilterDefinitions() {
        return [
            {
                key: "banco",
                label: "Banco",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.banco : "";
                },
            },
            {
                key: "tipo_movimentacao_label",
                label: "Tipo de Movimentação",
                singleSelect: false,
                extractValue: function (rowData) {
                    if (!rowData) return "";
                    return tiposValues[String(rowData.tipo_movimentacao || "")] || rowData.tipo_movimentacao_label || "";
                },
            },
            {
                key: "empresa_titular_label",
                label: "Empresa Titular",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.empresa_titular_label : "";
                },
            },
        ];
    }

    function rebuildExternalFiltersByDate() {
        if (!window.ModuleFilterCore || !filtrosColunaEsquerda || !filtrosColunaDireita) {
            externalFilters = null;
            if (tabela && typeof tabela.refreshFilter === "function") {
                tabela.refreshFilter();
            }
            return;
        }

        if (secFiltros) {
            secFiltros.dataset.moduleFiltersManual = "true";
            var placeholder = secFiltros.querySelector(".module-filters-placeholder");
            if (placeholder) placeholder.remove();
        }

        externalFilters = window.ModuleFilterCore.create({
            data: getDataScopedByDate(),
            definitions: createFilterDefinitions(),
            leftColumn: filtrosColunaEsquerda,
            rightColumn: filtrosColunaDireita,
            onChange: function () {
                if (tabela && typeof tabela.refreshFilter === "function") {
                    tabela.refreshFilter();
                }
            },
        });

        if (tabela && typeof tabela.refreshFilter === "function") {
            tabela.refreshFilter();
        }
    }

    function matchesGlobalFilters(rowData) {
        if (selectedDateIso && toText(rowData.data_iso) !== selectedDateIso) {
            return false;
        }
        if (externalFilters && typeof externalFilters.matchesRecord === "function") {
            return externalFilters.matchesRecord(rowData);
        }
        return true;
    }

    function getVisibleRowsData() {
        if (!tabela || typeof tabela.getData !== "function") return getDataScopedByDate();
        return tabela.getData("active") || [];
    }

    function updateDashboard(linhas) {
        var limiteInicial = 0;
        var limiteFinal = 0;
        var saldoInicial = 0;
        var saldoFinal = 0;
        var antecipacoes = 0;

        (linhas || []).forEach(function (item) {
            var tipo = toText(item.tipo_movimentacao);
            var valor = toNumber(item.valor_atual);
            if (tipo === "limite_inicial") limiteInicial += valor;
            if (tipo === "limite_final") limiteFinal += valor;
            if (tipo === "saldo_inicial") saldoInicial += valor;
            if (tipo === "saldo_final") saldoFinal += valor;
            if (tipo === "antecipacao") antecipacoes += valor;
        });

        if (kpiLimiteInicialEl) kpiLimiteInicialEl.textContent = formatMoney(limiteInicial);
        if (kpiLimiteFinalEl) kpiLimiteFinalEl.textContent = formatMoney(limiteFinal);
        if (kpiLimitesTotalEl) kpiLimitesTotalEl.textContent = formatMoney(limiteInicial + limiteFinal);
        if (kpiSaldoInicialEl) kpiSaldoInicialEl.textContent = formatMoney(saldoInicial);
        if (kpiSaldoFinalEl) kpiSaldoFinalEl.textContent = formatMoney(saldoFinal);
        if (kpiSaldosTotalEl) kpiSaldosTotalEl.textContent = formatMoney(saldoInicial + saldoFinal);
        if (kpiAntecipacoesEl) kpiAntecipacoesEl.textContent = formatMoney(antecipacoes);
    }

    function applyDateFilterValue(nextDateIso) {
        selectedDateIso = toText(nextDateIso);
        if (filtroDataInput && filtroDataInput.value !== selectedDateIso) {
            filtroDataInput.value = selectedDateIso;
        }
        rebuildExternalFiltersByDate();
        updateDashboard(getVisibleRowsData());
    }

    function bindFilterClearButtons() {
        function limparTodosFiltros() {
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

        var clearButtons = document.querySelectorAll(".module-filters-clear-all, .module-shell-clear-filters");
        clearButtons.forEach(function (button) {
            button.addEventListener("click", limparTodosFiltros);
        });
    }

    function submitCreate(event) {
        if (!event) return;
        event.preventDefault();
        if (!tabela || typeof tabela.addData !== "function") return;

        var url = cadastroForm.getAttribute("action");
        if (!url) return;

        var formData = new FormData(cadastroForm);
        if (!formData.get("csrfmiddlewaretoken")) {
            appendCsrfToken(formData);
        }

        setSaveStatus("Criando registro...", "saldos-limites-save-status--progress");

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
                        "saldos-limites-save-status--error"
                    );
                    return;
                }

                data.push(result.body.registro);
                Promise.resolve(tabela.addData([result.body.registro], true))
                    .then(function () {
                        cadastroForm.reset();
                        rebuildExternalFiltersByDate();
                        updateDashboard(getVisibleRowsData());
                        setSaveStatus("Registro criado e tabela atualizada.", "saldos-limites-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro criado, mas houve falha ao atualizar a tabela.",
                            "saldos-limites-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao criar registro.", "saldos-limites-save-status--error");
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

        setSaveStatus("Excluindo registro...", "saldos-limites-save-status--progress");

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
                        "saldos-limites-save-status--error"
                    );
                    return;
                }

                var idExcluido = Number(rowData.id);
                data = data.filter(function (item) {
                    return Number(item.id) !== idExcluido;
                });

                Promise.resolve(row.delete())
                    .then(function () {
                        rebuildExternalFiltersByDate();
                        updateDashboard(getVisibleRowsData());
                        setSaveStatus("Registro excluido e tabela atualizada.", "saldos-limites-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro excluido, mas houve falha ao atualizar a tabela.",
                            "saldos-limites-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao excluir registro.", "saldos-limites-save-status--error");
            });
    }

    function renderCadastroContasOptions(empresaTitularId) {
        if (!cadastroContaSelect) return;

        var filtroTitular = toText(empresaTitularId);
        var selectedAtual = toText(cadastroContaSelect.value);
        var html = ['<option value="">Selecione</option>'];
        var selecionadoAindaDisponivel = false;

        contasOpcoes.forEach(function (conta) {
            var titularId = toText(conta.empresa_titular_id);
            if (filtroTitular && titularId !== filtroTitular) return;
            var id = toText(conta.id);
            var label = toText(conta.titular_label) + " | " + toText(conta.banco) + " | " + toText(conta.label);
            if (id && id === selectedAtual) {
                selecionadoAindaDisponivel = true;
            }
            html.push('<option value="' + id + '">' + label + "</option>");
        });

        cadastroContaSelect.innerHTML = html.join("");
        if (selecionadoAindaDisponivel) {
            cadastroContaSelect.value = selectedAtual;
        }
    }

    tabela = window.TabulatorDefaults.create("#saldos-limites-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {
                title: "Data",
                field: "data_iso",
                editor: "input",
                editorParams: {
                    elementAttributes: {
                        type: "date",
                    },
                },
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
                cellEdited: onCellEdited,
            },
            {
                title: "Empresa Titular",
                field: "empresa_titular_id",
                editor: "list",
                editorParams: {
                    values: empresasValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.empresa_titular_label || empresasValues[String(row.empresa_titular_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 220,
            },
            {
                title: "Conta",
                field: "conta_bancaria_id",
                editor: "list",
                editorParams: {
                    values: contasValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.conta_label || "";
                },
                cellEdited: onCellEdited,
                width: 180,
            },
            {title: "Banco", field: "banco", width: 180},
            {
                title: "Tipo de Movimentação",
                field: "tipo_movimentacao",
                editor: "list",
                editorParams: {
                    values: tiposValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var tipoAtual = String(cell.getValue() || row.tipo_movimentacao || "");
                    return tiposValues[tipoAtual] || row.tipo_movimentacao_label || tipoAtual;
                },
                cellEdited: onCellEdited,
                width: 210,
            },
            {
                title: "Valor",
                field: "valor_atual",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
                },
                cellEdited: onCellEdited,
                width: 150,
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

    if (filtroDataInput) {
        filtroDataInput.addEventListener("change", function () {
            applyDateFilterValue(filtroDataInput.value);
        });
    }

    if (btnUltimaData) {
        btnUltimaData.addEventListener("click", function () {
            if (!ultimaDataIso) return;
            applyDateFilterValue(ultimaDataIso);
        });
    }

    if (btnLimparData) {
        btnLimparData.addEventListener("click", function () {
            applyDateFilterValue("");
        });
    }

    cadastroForm.addEventListener("submit", submitCreate);
    if (cadastroTitularSelect) {
        cadastroTitularSelect.addEventListener("change", function () {
            renderCadastroContasOptions(cadastroTitularSelect.value);
        });
    }
    bindFilterClearButtons();
    renderCadastroContasOptions(cadastroTitularSelect ? cadastroTitularSelect.value : "");
    applyDateFilterValue("");
    setSaveStatus("", "");
})();
