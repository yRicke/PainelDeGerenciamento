(function () {
    var dataElement = document.getElementById("comite-diario-tabulator-data");
    var empresasElement = document.getElementById("comite-diario-empresas-opcoes-data");
    var parceirosElement = document.getElementById("comite-diario-parceiros-opcoes-data");
    var naturezasElement = document.getElementById("comite-diario-naturezas-opcoes-data");
    var centrosElement = document.getElementById("comite-diario-centros-opcoes-data");
    var bancosElement = document.getElementById("comite-diario-bancos-opcoes-data");
    var receitaDespesaElement = document.getElementById("comite-diario-receita-despesa-opcoes-data");
    var tipoMovimentoElement = document.getElementById("comite-diario-tipo-movimento-opcoes-data");
    var decisaoElement = document.getElementById("comite-diario-decisao-opcoes-data");
    var ultimaDataElement = document.getElementById("comite-diario-ultima-data-iso");
    var cadastroForm = document.getElementById("comite-diario-cadastro-form");
    var saveStatusEl = document.getElementById("comite-diario-save-status");
    var cadastroDecisaoSelect = cadastroForm ? cadastroForm.querySelector('select[name="decisao"]') : null;
    var cadastroTransferFields = cadastroForm
        ? [
            cadastroForm.querySelector('select[name="de_banco_id"]'),
            cadastroForm.querySelector('select[name="para_banco_id"]'),
            cadastroForm.querySelector('select[name="para_empresa_id"]'),
        ]
        : [];

    if (
        !dataElement ||
        !empresasElement ||
        !parceirosElement ||
        !naturezasElement ||
        !centrosElement ||
        !bancosElement ||
        !receitaDespesaElement ||
        !tipoMovimentoElement ||
        !decisaoElement ||
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
    var parceirosOpcoes = JSON.parse(parceirosElement.textContent || "[]");
    var naturezasOpcoes = JSON.parse(naturezasElement.textContent || "[]");
    var centrosOpcoes = JSON.parse(centrosElement.textContent || "[]");
    var bancosOpcoes = JSON.parse(bancosElement.textContent || "[]");
    var receitaDespesaOpcoes = JSON.parse(receitaDespesaElement.textContent || "[]");
    var tipoMovimentoOpcoes = JSON.parse(tipoMovimentoElement.textContent || "[]");
    var decisaoOpcoes = JSON.parse(decisaoElement.textContent || "[]");
    var ultimaDataIso = "";
    try {
        ultimaDataIso = JSON.parse(ultimaDataElement ? (ultimaDataElement.textContent || "\"\"") : "\"\"");
    } catch (_error) {
        ultimaDataIso = "";
    }

    var filtroDataInput = document.getElementById("comite-diario-data-filtro");
    var btnUltimaData = document.getElementById("comite-diario-btn-ultima-data");
    var btnLimparData = document.getElementById("comite-diario-btn-limpar-data");
    var secFiltros = document.getElementById("sec-filtros");
    var filtrosColunaEsquerda = document.getElementById("comite-filtros-coluna-esquerda");
    var filtrosColunaDireita = document.getElementById("comite-filtros-coluna-direita");

    var kpiTotalEl = document.getElementById("comite-kpi-total-registros");
    var kpiReceitasEl = document.getElementById("comite-kpi-receitas");
    var kpiDespesasEl = document.getElementById("comite-kpi-despesas");
    var kpiSaldoEl = document.getElementById("comite-kpi-saldo");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});

    var empresasValues = {};
    var parceirosValues = {};
    var naturezasValues = {};
    var centrosValues = {};
    var bancosValues = {};
    var receitaDespesaValues = {};
    var tipoMovimentoValues = {};
    var decisaoValues = {};

    empresasOpcoes.forEach(function (item) {
        var id = String(item.id || "").trim();
        if (!id) return;
        empresasValues[id] = String(item.label || "").trim();
    });

    parceirosOpcoes.forEach(function (item) {
        var id = String(item.id || "").trim();
        if (!id) return;
        parceirosValues[id] = String(item.label || "").trim();
    });

    naturezasOpcoes.forEach(function (item) {
        var id = String(item.id || "").trim();
        if (!id) return;
        naturezasValues[id] = String(item.label || "").trim();
    });

    centrosOpcoes.forEach(function (item) {
        var id = String(item.id || "").trim();
        if (!id) return;
        centrosValues[id] = String(item.label || "").trim();
    });

    bancosOpcoes.forEach(function (item) {
        var id = String(item.id || "").trim();
        if (!id) return;
        bancosValues[id] = String(item.label || "").trim();
    });

    receitaDespesaOpcoes.forEach(function (item) {
        var value = String(item.value || "").trim();
        if (!value) return;
        receitaDespesaValues[value] = String(item.label || "").trim() || value;
    });

    tipoMovimentoOpcoes.forEach(function (item) {
        var value = String(item.value || "").trim();
        if (!value) return;
        tipoMovimentoValues[value] = String(item.label || "").trim() || value;
    });

    decisaoOpcoes.forEach(function (item) {
        var value = String(item.value || "").trim();
        if (!value) return;
        decisaoValues[value] = String(item.label || "").trim() || value;
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
            "comite-diario-save-status--ok",
            "comite-diario-save-status--error",
            "comite-diario-save-status--progress"
        );
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function updateLocalLabels(rowData) {
        var empresaTitularId = String(rowData.empresa_titular_id || "");
        var parceiroId = String(rowData.parceiro_id || "");
        var naturezaId = String(rowData.natureza_id || "");
        var centroResultadoId = String(rowData.centro_resultado_id || "");
        var deBancoId = String(rowData.de_banco_id || "");
        var paraBancoId = String(rowData.para_banco_id || "");
        var paraEmpresaId = String(rowData.para_empresa_id || "");
        var receitaDespesa = String(rowData.receita_despesa || "");
        var tipoMovimento = String(rowData.tipo_movimento || "");
        var decisao = String(rowData.decisao || "");

        rowData.empresa_titular_label = empresasValues[empresaTitularId] || "";
        rowData.parceiro_label = parceirosValues[parceiroId] || "";
        rowData.natureza_label = naturezasValues[naturezaId] || "";
        rowData.centro_resultado_label = centrosValues[centroResultadoId] || "";
        rowData.de_banco_label = bancosValues[deBancoId] || "";
        rowData.para_banco_label = bancosValues[paraBancoId] || "";
        rowData.para_empresa_label = empresasValues[paraEmpresaId] || "";
        rowData.receita_despesa_label = receitaDespesaValues[receitaDespesa] || receitaDespesa;
        rowData.tipo_movimento_label = tipoMovimentoValues[tipoMovimento] || tipoMovimento;
        rowData.decisao_label = decisaoValues[decisao] || decisao;
        rowData.data_negociacao = formatDateIsoToBr(rowData.data_negociacao_iso);
        rowData.data_vencimento = formatDateIsoToBr(rowData.data_vencimento_iso);
        rowData.data_prorrogada = formatDateIsoToBr(rowData.data_prorrogada_iso);
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
        if (field) rollbackData[field] = oldValue;
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

    function buildPayloadFromRow(rowData) {
        return {
            data_negociacao: toText(rowData.data_negociacao_iso),
            data_vencimento: toText(rowData.data_vencimento_iso),
            receita_despesa: toText(rowData.receita_despesa),
            empresa_titular_id: toText(rowData.empresa_titular_id),
            parceiro_id: toText(rowData.parceiro_id),
            natureza_id: toText(rowData.natureza_id),
            centro_resultado_id: toText(rowData.centro_resultado_id),
            historico: toText(rowData.historico),
            numero_nota: toText(rowData.numero_nota),
            valor_liquido: toText(rowData.valor_liquido),
            tipo_movimento: toText(rowData.tipo_movimento),
            decisao: toText(rowData.decisao),
            data_prorrogada: toText(rowData.data_prorrogada_iso),
            de_banco_id: toText(rowData.de_banco_id),
            para_banco_id: toText(rowData.para_banco_id),
            para_empresa_id: toText(rowData.para_empresa_id),
        };
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

        setSaveStatus("Salvando alteracao...", "comite-diario-save-status--progress");

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
                        "comite-diario-save-status--error"
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
                            return Number(item.id) === Number(result.body.registro.id);
                        });
                        if (rowIndex >= 0) {
                            data[rowIndex] = updatedRowData;
                        }

                        rebuildExternalFiltersByDate();
                        updateDashboard(getVisibleRowsData());
                        setSaveStatus("Salvo automaticamente.", "comite-diario-save-status--ok");
                    })
                    .catch(function () {
                        rollbackEditedField(row, rowData, editedField, oldValue);
                        setSaveStatus("Falha ao aplicar retorno no front.", "comite-diario-save-status--error");
                    })
                    .finally(function () {
                        internalUpdate = false;
                    });
            })
            .catch(function (error) {
                if (seqByRowId[rowId] !== currentSeq) return;
                rollbackEditedField(row, rowData, editedField, oldValue);
                if (error && error.name === "AbortError") {
                    setSaveStatus("Tempo de resposta excedido ao salvar. Alteracao revertida.", "comite-diario-save-status--error");
                    return;
                }
                setSaveStatus("Falha ao salvar. Alteracao revertida.", "comite-diario-save-status--error");
            })
            .finally(function () {
                if (timeoutId) window.clearTimeout(timeoutId);
            });
    }

    function onCellEdited(cell) {
        if (internalUpdate) return;
        saveRowAutomatically(cell);
    }

    function getDataScopedByDate() {
        if (!selectedDateIso) return data.slice();
        return data.filter(function (rowData) {
            return toText(rowData.data_negociacao_iso) === selectedDateIso;
        });
    }

    function createFilterDefinitions() {
        return [
            {
                key: "receita_despesa_label",
                label: "Receita/Despesa",
                singleSelect: false,
                extractValue: function (rowData) {
                    if (!rowData) return "";
                    var receitaDespesa = String(rowData.receita_despesa || "");
                    return receitaDespesaValues[receitaDespesa] || rowData.receita_despesa_label || "";
                },
            },
            {
                key: "decisao_label",
                label: "Decisao",
                singleSelect: false,
                extractValue: function (rowData) {
                    if (!rowData) return "";
                    var decisao = String(rowData.decisao || "");
                    return decisaoValues[decisao] || rowData.decisao_label || "";
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
            {
                key: "parceiro_label",
                label: "Parceiro",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.parceiro_label : "";
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
        if (selectedDateIso && toText(rowData.data_negociacao_iso) !== selectedDateIso) {
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
        var totalRegistros = 0;
        var totalReceitas = 0;
        var totalDespesas = 0;

        (linhas || []).forEach(function (item) {
            totalRegistros += 1;
            var valor = toNumber(item.valor_liquido);
            var tipo = String(item.receita_despesa || "");
            if (tipo === "receita") totalReceitas += valor;
            if (tipo === "despesa") totalDespesas += valor;
        });

        var saldoLiquido = totalReceitas - totalDespesas;

        if (kpiTotalEl) kpiTotalEl.textContent = String(totalRegistros);
        if (kpiReceitasEl) kpiReceitasEl.textContent = formatMoney(totalReceitas);
        if (kpiDespesasEl) kpiDespesasEl.textContent = formatMoney(totalDespesas);
        if (kpiSaldoEl) kpiSaldoEl.textContent = formatMoney(saldoLiquido);
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

    function toggleTransferFieldsRequirement() {
        if (!cadastroDecisaoSelect || !cadastroTransferFields.length) return;
        var isTransferir = toText(cadastroDecisaoSelect.value) === "transferir";
        cadastroTransferFields.forEach(function (field) {
            if (!field) return;
            field.required = isTransferir;
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

        setSaveStatus("Criando registro...", "comite-diario-save-status--progress");

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
                        "comite-diario-save-status--error"
                    );
                    return;
                }

                data.push(result.body.registro);
                Promise.resolve(tabela.addData([result.body.registro], true))
                    .then(function () {
                        cadastroForm.reset();
                        toggleTransferFieldsRequirement();
                        rebuildExternalFiltersByDate();
                        updateDashboard(getVisibleRowsData());
                        setSaveStatus("Registro criado e tabela atualizada.", "comite-diario-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro criado, mas houve falha ao atualizar a tabela.",
                            "comite-diario-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao criar registro.", "comite-diario-save-status--error");
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

        setSaveStatus("Excluindo registro...", "comite-diario-save-status--progress");

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
                        "comite-diario-save-status--error"
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
                        setSaveStatus("Registro excluido e tabela atualizada.", "comite-diario-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro excluido, mas houve falha ao atualizar a tabela.",
                            "comite-diario-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao excluir registro.", "comite-diario-save-status--error");
            });
    }

    tabela = window.TabulatorDefaults.create("#comite-diario-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {
                title: "Data Negociacao",
                field: "data_negociacao_iso",
                editor: "input",
                editorParams: {elementAttributes: {type: "date"}},
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
                cellEdited: onCellEdited,
                width: 150,
            },
            {
                title: "Data Vencimento",
                field: "data_vencimento_iso",
                editor: "input",
                editorParams: {elementAttributes: {type: "date"}},
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
                cellEdited: onCellEdited,
                width: 150,
            },
            {
                title: "Receita/Despesa",
                field: "receita_despesa",
                editor: "list",
                editorParams: {values: receitaDespesaValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var value = String(cell.getValue() || row.receita_despesa || "");
                    return receitaDespesaValues[value] || row.receita_despesa_label || value;
                },
                cellEdited: onCellEdited,
                width: 170,
            },
            {
                title: "Empresa Titular",
                field: "empresa_titular_id",
                editor: "list",
                editorParams: {values: empresasValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.empresa_titular_label || empresasValues[String(row.empresa_titular_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 220,
            },
            {
                title: "Parceiro",
                field: "parceiro_id",
                editor: "list",
                editorParams: {values: parceirosValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.parceiro_label || parceirosValues[String(row.parceiro_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 240,
            },
            {
                title: "Natureza",
                field: "natureza_id",
                editor: "list",
                editorParams: {values: naturezasValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.natureza_label || naturezasValues[String(row.natureza_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 240,
            },
            {
                title: "Centro Resultado",
                field: "centro_resultado_id",
                editor: "list",
                editorParams: {values: centrosValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.centro_resultado_label || centrosValues[String(row.centro_resultado_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 220,
            },
            {title: "Historico", field: "historico", editor: "input", cellEdited: onCellEdited, width: 260},
            {title: "Numero Nota", field: "numero_nota", editor: "input", cellEdited: onCellEdited, width: 130},
            {
                title: "Valor Liquido",
                field: "valor_liquido",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
                },
                cellEdited: onCellEdited,
                width: 140,
            },
            {
                title: "Tipo Movimento",
                field: "tipo_movimento",
                editor: "list",
                editorParams: {values: tipoMovimentoValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var value = String(cell.getValue() || row.tipo_movimento || "");
                    return tipoMovimentoValues[value] || row.tipo_movimento_label || value;
                },
                cellEdited: onCellEdited,
                width: 170,
            },
            {
                title: "Decisao",
                field: "decisao",
                editor: "list",
                editorParams: {values: decisaoValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var value = String(cell.getValue() || row.decisao || "");
                    return decisaoValues[value] || row.decisao_label || value;
                },
                cellEdited: onCellEdited,
                width: 200,
            },
            {
                title: "Data Prorrogada",
                field: "data_prorrogada_iso",
                editor: "input",
                editorParams: {elementAttributes: {type: "date"}},
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
                cellEdited: onCellEdited,
                width: 150,
            },
            {
                title: "De Banco",
                field: "de_banco_id",
                editor: "list",
                editorParams: {values: bancosValues, clearable: true},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.de_banco_label || bancosValues[String(row.de_banco_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 170,
            },
            {
                title: "Para Banco",
                field: "para_banco_id",
                editor: "list",
                editorParams: {values: bancosValues, clearable: true},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.para_banco_label || bancosValues[String(row.para_banco_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 170,
            },
            {
                title: "Para Empresa",
                field: "para_empresa_id",
                editor: "list",
                editorParams: {values: empresasValues, clearable: true},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.para_empresa_label || empresasValues[String(row.para_empresa_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 220,
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
    if (cadastroDecisaoSelect) {
        cadastroDecisaoSelect.addEventListener("change", toggleTransferFieldsRequirement);
    }

    bindFilterClearButtons();
    toggleTransferFieldsRequirement();
    applyDateFilterValue("");
    setSaveStatus("", "");
})();
