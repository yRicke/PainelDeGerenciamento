(function () {
    var dataElement = document.getElementById("kpi-controladoria-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.TabulatorDefaults) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var cadastroForm = document.querySelector("#sec-cadastro form");
    var analiseInput = cadastroForm ? cadastroForm.querySelector('input[name="analise"]') : null;
    var saveStatusEl = document.getElementById("kpi-controladoria-save-status");
    var limparDadosBtn = document.getElementById("kpi-controladoria-limpar-dados-btn");
    var pdfBtn = document.getElementById("kpi-controladoria-pdf-btn");
    var pdfForm = document.getElementById("kpi-controladoria-pdf-form");
    var pdfPayloadEl = document.getElementById("kpi-controladoria-pdf-payload");
    var internalUpdate = false;
    var seqByRowId = {};
    var tabela = null;

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function parseInteger(value) {
        var numero = Number(toText(value));
        if (!Number.isFinite(numero)) return 0;
        return Math.max(0, Math.trunc(numero));
    }

    function definirProximaAnalise(valor) {
        if (!analiseInput) return;
        var proximo = parseInteger(valor);
        analiseInput.value = String(proximo > 0 ? proximo : 1);
    }

    function toBoolean(value) {
        if (typeof value === "boolean") return value;
        var texto = toText(value).toLowerCase();
        return texto === "true" || texto === "1" || texto === "sim" || texto === "yes" || texto === "on";
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

    function parseJsonResponse(response) {
        return response.json().catch(function () {
            return {};
        }).then(function (body) {
            return {ok: response.ok, body: body};
        });
    }

    function setSaveStatus(text, tone) {
        if (!saveStatusEl) return;
        saveStatusEl.classList.remove(
            "kpi-controladoria-save-status--ok",
            "kpi-controladoria-save-status--error",
            "kpi-controladoria-save-status--progress"
        );
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function formatTextoOuVazio(valor) {
        return toText(valor) || "(Vazio)";
    }

    function ordenarTexto(a, b) {
        return String(a.label || "").localeCompare(String(b.label || ""), "pt-BR", {
            sensitivity: "base",
            numeric: true,
        });
    }

    function ensureFilterColumns(section) {
        if (!section) return null;
        var left = section.querySelector('[data-module-filter-column="left"]')
            || section.querySelector("#kpi-controladoria-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#kpi-controladoria-filtros-coluna-direita");
        if (left && right) return {left: left, right: right};
        return null;
    }

    function registrarLimparFiltros(tabelaRef, secFiltros, filtrosExternos) {
        if (!tabelaRef || !secFiltros || !filtrosExternos) return;
        function limparTudo() {
            if (typeof filtrosExternos.clearAllFilters === "function") filtrosExternos.clearAllFilters();
            if (typeof tabelaRef.clearHeaderFilter === "function") tabelaRef.clearHeaderFilter();
            if (typeof tabelaRef.refreshFilter === "function") tabelaRef.refreshFilter();
        }
        var limparSidebar = secFiltros.querySelector(".module-filters-clear-all");
        var limparToolbar = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
        if (limparSidebar) limparSidebar.addEventListener("click", limparTudo);
        if (limparToolbar) limparToolbar.addEventListener("click", limparTudo);
    }

    function payloadFromRow(rowData) {
        return {
            analise: String(parseInteger(rowData.analise) || ""),
            tipo: toText(rowData.tipo),
            descricao: toText(rowData.descricao),
            parametro_meta: toText(rowData.parametro_meta),
            parametro_compromisso: toText(rowData.parametro_compromisso),
            semana_1_conferencia: String(toBoolean(rowData.semana_1_conferencia)),
            semana_1_resultado: toText(rowData.semana_1_resultado),
            semana_2_conferencia: String(toBoolean(rowData.semana_2_conferencia)),
            semana_2_resultado: toText(rowData.semana_2_resultado),
            semana_3_conferencia: String(toBoolean(rowData.semana_3_conferencia)),
            semana_3_resultado: toText(rowData.semana_3_resultado),
            semana_4_conferencia: String(toBoolean(rowData.semana_4_conferencia)),
            semana_4_resultado: toText(rowData.semana_4_resultado),
            semana_5_conferencia: String(toBoolean(rowData.semana_5_conferencia)),
            semana_5_resultado: toText(rowData.semana_5_resultado),
            total_mes_conferencia: String(toBoolean(rowData.total_mes_conferencia)),
            total_mes_resultado: toText(rowData.total_mes_resultado),
            consideracoes: toText(rowData.consideracoes),
        };
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

    function aplicarClasseResultado(cell) {
        var value = toText(cell.getValue());
        var element = cell.getElement();
        if (!element) return value;
        element.classList.remove("kpi-cell-ok", "kpi-cell-alerta");
        if (value === "Ok") element.classList.add("kpi-cell-ok");
        if (value === "Alerta") element.classList.add("kpi-cell-alerta");
        return value;
    }

    function salvarLinhaAutomatica(cell) {
        if (!tabela || !cell) return;
        var row = cell.getRow();
        if (!row) return;
        var rowData = row.getData() || {};
        if (!rowData.editar_url) return;

        var rowId = rowData.id;
        var currentSeq = Number(seqByRowId[rowId] || 0) + 1;
        seqByRowId[rowId] = currentSeq;
        var valorAntigo = typeof cell.getOldValue === "function" ? cell.getOldValue() : null;
        var payload = payloadFromRow(rowData);
        var formData = new FormData();
        var csrfToken = getCsrfToken();
        if (csrfToken) formData.append("csrfmiddlewaretoken", csrfToken);
        Object.keys(payload).forEach(function (key) {
            formData.append(key, payload[key]);
        });

        setSaveStatus("Salvando alteracao...", "kpi-controladoria-save-status--progress");

        fetch(rowData.editar_url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (seqByRowId[rowId] !== currentSeq) return;
                if (!result.ok || !result.body || result.body.ok === false) {
                    restoreCellValue(cell, valorAntigo);
                    setSaveStatus(result.body && result.body.message ? result.body.message : "Falha ao salvar.", "kpi-controladoria-save-status--error");
                    return;
                }
                if (result.body.registro && typeof row.update === "function") {
                    internalUpdate = true;
                    row.update(result.body.registro);
                    internalUpdate = false;
                }
                setSaveStatus("Salvo automaticamente.", "kpi-controladoria-save-status--ok");
            })
            .catch(function () {
                if (seqByRowId[rowId] !== currentSeq) return;
                restoreCellValue(cell, valorAntigo);
                setSaveStatus("Falha ao salvar.", "kpi-controladoria-save-status--error");
            });
    }

    function onCellEdited(cell) {
        if (internalUpdate) return;
        salvarLinhaAutomatica(cell);
    }

    function salvarNovoRegistro(event) {
        if (!event || !cadastroForm) return;
        event.preventDefault();
        var url = cadastroForm.getAttribute("action");
        if (!url) return;
        var formData = new FormData(cadastroForm);
        var csrfToken = getCsrfToken();
        if (csrfToken && !formData.get("csrfmiddlewaretoken")) formData.append("csrfmiddlewaretoken", csrfToken);
        setSaveStatus("Criando registro...", "kpi-controladoria-save-status--progress");

        fetch(url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false || !result.body.registro) {
                    setSaveStatus(result.body && result.body.message ? result.body.message : "Falha ao criar registro.", "kpi-controladoria-save-status--error");
                    return;
                }
                Promise.resolve(tabela.addData([result.body.registro], true))
                    .then(function () {
                        cadastroForm.reset();
                        definirProximaAnalise(result.body.proxima_analise);
                        setSaveStatus("Registro criado e tabela atualizada.", "kpi-controladoria-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus("Registro criado, mas houve falha ao atualizar a tabela.", "kpi-controladoria-save-status--error");
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao criar registro.", "kpi-controladoria-save-status--error");
            });
    }

    function excluirRegistro(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;
        var rowData = row.getData() || {};
        if (!rowData.excluir_url) return;
        if (!window.confirm("Excluir registro?")) return;

        var formData = new FormData();
        var csrfToken = getCsrfToken();
        if (csrfToken) formData.append("csrfmiddlewaretoken", csrfToken);
        setSaveStatus("Excluindo registro...", "kpi-controladoria-save-status--progress");

        fetch(rowData.excluir_url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false) {
                    setSaveStatus(result.body && result.body.message ? result.body.message : "Falha ao excluir registro.", "kpi-controladoria-save-status--error");
                    return;
                }
                Promise.resolve(row.delete())
                    .then(function () {
                        setSaveStatus("Registro excluido e tabela atualizada.", "kpi-controladoria-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus("Registro excluido, mas houve falha ao atualizar a tabela.", "kpi-controladoria-save-status--error");
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao excluir registro.", "kpi-controladoria-save-status--error");
            });
    }

    function coletarLinhasAtivas() {
        if (!tabela) return Array.isArray(data) ? data.slice() : [];
        try {
            var rowsAtivos = tabela.getRows("active");
            if (Array.isArray(rowsAtivos) && rowsAtivos.length) {
                return rowsAtivos.map(function (row) { return row.getData(); });
            }
        } catch (_err) {}
        try {
            var dataAtiva = tabela.getData("active");
            if (Array.isArray(dataAtiva) && dataAtiva.length) return dataAtiva;
        } catch (_err2) {}
        var todos = tabela.getData();
        return Array.isArray(todos) ? todos : [];
    }

    function limparCamposAcompanhamentoLocais() {
        if (!tabela || typeof tabela.getRows !== "function") return;
        tabela.getRows().forEach(function (row) {
            internalUpdate = true;
            row.update({
                semana_1_conferencia: false,
                semana_1_resultado: "",
                semana_2_conferencia: false,
                semana_2_resultado: "",
                semana_3_conferencia: false,
                semana_3_resultado: "",
                semana_4_conferencia: false,
                semana_4_resultado: "",
                semana_5_conferencia: false,
                semana_5_resultado: "",
                total_mes_conferencia: false,
                total_mes_resultado: "",
                consideracoes: "",
            });
            internalUpdate = false;
        });
    }

    function limparDados() {
        if (!limparDadosBtn) return;
        var url = window.location.pathname.replace(/\/$/, "") + "/limpar-dados/";
        if (!window.confirm("Limpar os dados das semanas, total do mes e consideracoes de todos os registros?")) return;
        var formData = new FormData();
        var csrfToken = getCsrfToken();
        if (csrfToken) formData.append("csrfmiddlewaretoken", csrfToken);
        setSaveStatus("Limpando dados...", "kpi-controladoria-save-status--progress");

        fetch(url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false) {
                    setSaveStatus(result.body && result.body.message ? result.body.message : "Falha ao limpar dados.", "kpi-controladoria-save-status--error");
                    return;
                }
                limparCamposAcompanhamentoLocais();
                setSaveStatus(result.body.message || "Dados limpos com sucesso.", "kpi-controladoria-save-status--ok");
            })
            .catch(function () {
                setSaveStatus("Falha ao limpar dados.", "kpi-controladoria-save-status--error");
            });
    }

    function exportarPdf() {
        if (!pdfForm || !pdfPayloadEl) return;
        var payload = {
            rows: coletarLinhasAtivas().map(function (item) {
                return {
                    analise: parseInteger(item.analise),
                    tipo: toText(item.tipo),
                    descricao: toText(item.descricao),
                    parametro_meta: toText(item.parametro_meta),
                    parametro_compromisso: toText(item.parametro_compromisso),
                    semana_1_conferencia: toBoolean(item.semana_1_conferencia),
                    semana_1_resultado: toText(item.semana_1_resultado),
                    semana_2_conferencia: toBoolean(item.semana_2_conferencia),
                    semana_2_resultado: toText(item.semana_2_resultado),
                    semana_3_conferencia: toBoolean(item.semana_3_conferencia),
                    semana_3_resultado: toText(item.semana_3_resultado),
                    semana_4_conferencia: toBoolean(item.semana_4_conferencia),
                    semana_4_resultado: toText(item.semana_4_resultado),
                    semana_5_conferencia: toBoolean(item.semana_5_conferencia),
                    semana_5_resultado: toText(item.semana_5_resultado),
                    total_mes_conferencia: toBoolean(item.total_mes_conferencia),
                    total_mes_resultado: toText(item.total_mes_resultado),
                    consideracoes: toText(item.consideracoes),
                };
            }),
        };
        try {
            pdfPayloadEl.value = JSON.stringify(payload);
        } catch (_err) {
            pdfPayloadEl.value = '{"rows":[]}';
        }
        pdfForm.submit();
    }

    var colunaExcluir = {
        title: "Acoes",
        field: "excluir_url",
        frozen: true,
        hozAlign: "center",
        formatter: function (cell) {
            if (!cell.getValue()) return "";
            return '<button class="btn-danger js-kpi-controladoria-excluir" type="button">Excluir</button>';
        },
        cellClick: function (event, cell) {
            var target = event && event.target;
            var botao = target && target.closest ? target.closest(".js-kpi-controladoria-excluir") : null;
            if (!botao) return;
            excluirRegistro(cell);
        },
    };

    tabela = window.TabulatorDefaults.create("#kpi-controladoria-tabulator", {
        data: data,
        layout: "fitDataStretch",
        columns: [
            {
                title: "Analise",
                field: "analise",
                editor: "number",
                hozAlign: "center",
                width: 90,
                editorParams: {min: 1, step: 1},
                mutatorEdit: function (value) { return parseInteger(value); },
                cellEdited: onCellEdited,
            },
            {
                title: "Tipo",
                field: "tipo",
                editor: "list",
                editorParams: {values: ["Verificacao", "Controle"]},
                width: 130,
                cellEdited: onCellEdited,
            },
            {
                title: "Descricao",
                field: "descricao",
                editor: "input",
                minWidth: 220,
                cellEdited: onCellEdited,
            },
            {
                title: "Parametros",
                cssClass: "kpi-col-parametros",
                columns: [
                    {title: "Meta", field: "parametro_meta", editor: "input", minWidth: 170, cellEdited: onCellEdited},
                    {title: "Compromisso", field: "parametro_compromisso", editor: "input", minWidth: 170, cellEdited: onCellEdited},
                ],
            },
            {
                title: "Semana 1",
                cssClass: "kpi-col-semana",
                columns: [
                    {title: "Conferencia", field: "semana_1_conferencia", formatter: "tickCross", editor: "tickCross", hozAlign: "center", width: 110, mutatorEdit: toBoolean, cellEdited: onCellEdited},
                    {title: "Resultado", field: "semana_1_resultado", editor: "list", editorParams: {values: ["", "Ok", "Alerta"]}, hozAlign: "center", width: 110, formatter: aplicarClasseResultado, cellEdited: onCellEdited},
                ],
            },
            {
                title: "Semana 2",
                cssClass: "kpi-col-semana",
                columns: [
                    {title: "Conferencia", field: "semana_2_conferencia", formatter: "tickCross", editor: "tickCross", hozAlign: "center", width: 110, mutatorEdit: toBoolean, cellEdited: onCellEdited},
                    {title: "Resultado", field: "semana_2_resultado", editor: "list", editorParams: {values: ["", "Ok", "Alerta"]}, hozAlign: "center", width: 110, formatter: aplicarClasseResultado, cellEdited: onCellEdited},
                ],
            },
            {
                title: "Semana 3",
                cssClass: "kpi-col-semana",
                columns: [
                    {title: "Conferencia", field: "semana_3_conferencia", formatter: "tickCross", editor: "tickCross", hozAlign: "center", width: 110, mutatorEdit: toBoolean, cellEdited: onCellEdited},
                    {title: "Resultado", field: "semana_3_resultado", editor: "list", editorParams: {values: ["", "Ok", "Alerta"]}, hozAlign: "center", width: 110, formatter: aplicarClasseResultado, cellEdited: onCellEdited},
                ],
            },
            {
                title: "Semana 4",
                cssClass: "kpi-col-semana",
                columns: [
                    {title: "Conferencia", field: "semana_4_conferencia", formatter: "tickCross", editor: "tickCross", hozAlign: "center", width: 110, mutatorEdit: toBoolean, cellEdited: onCellEdited},
                    {title: "Resultado", field: "semana_4_resultado", editor: "list", editorParams: {values: ["", "Ok", "Alerta"]}, hozAlign: "center", width: 110, formatter: aplicarClasseResultado, cellEdited: onCellEdited},
                ],
            },
            {
                title: "Semana 5",
                cssClass: "kpi-col-semana",
                columns: [
                    {title: "Conferencia", field: "semana_5_conferencia", formatter: "tickCross", editor: "tickCross", hozAlign: "center", width: 110, mutatorEdit: toBoolean, cellEdited: onCellEdited},
                    {title: "Resultado", field: "semana_5_resultado", editor: "list", editorParams: {values: ["", "Ok", "Alerta"]}, hozAlign: "center", width: 110, formatter: aplicarClasseResultado, cellEdited: onCellEdited},
                ],
            },
            {
                title: "Total Mes",
                cssClass: "kpi-col-total-mes",
                columns: [
                    {title: "Conferencia", field: "total_mes_conferencia", formatter: "tickCross", editor: "tickCross", hozAlign: "center", width: 110, mutatorEdit: toBoolean, cellEdited: onCellEdited},
                    {title: "Resultado", field: "total_mes_resultado", editor: "list", editorParams: {values: ["", "Ok", "Alerta"]}, hozAlign: "center", width: 110, formatter: aplicarClasseResultado, cellEdited: onCellEdited},
                ],
            },
            {
                title: "Consideracoes",
                field: "consideracoes",
                editor: "input",
                minWidth: 220,
                cellEdited: onCellEdited,
            },
            colunaExcluir,
        ],
    });

    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros && window.ModuleFilterCore) {
        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholder = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholder) placeholder.remove();
        var filtroColumns = ensureFilterColumns(secFiltros);
        if (filtroColumns && filtroColumns.left && filtroColumns.right) {
            var filtrosExternos = window.ModuleFilterCore.create({
                data: data,
                definitions: [
                    {
                        key: "tipo",
                        label: "Tipo",
                        extractValue: function (rowData) { return rowData ? rowData.tipo : ""; },
                        formatValue: formatTextoOuVazio,
                        sortOptions: ordenarTexto,
                    },
                    {
                        key: "semana_1_resultado",
                        label: "Semana 1 Resultado",
                        extractValue: function (rowData) { return rowData ? rowData.semana_1_resultado : ""; },
                        formatValue: formatTextoOuVazio,
                        sortOptions: ordenarTexto,
                    },
                    {
                        key: "semana_5_resultado",
                        label: "Semana 5 Resultado",
                        extractValue: function (rowData) { return rowData ? rowData.semana_5_resultado : ""; },
                        formatValue: formatTextoOuVazio,
                        sortOptions: ordenarTexto,
                    },
                    {
                        key: "total_mes_resultado",
                        label: "Total Mes Resultado",
                        extractValue: function (rowData) { return rowData ? rowData.total_mes_resultado : ""; },
                        formatValue: formatTextoOuVazio,
                        sortOptions: ordenarTexto,
                    },
                ],
                leftColumn: filtroColumns.left,
                rightColumn: filtroColumns.right,
                onChange: function () {
                    if (typeof tabela.refreshFilter === "function") tabela.refreshFilter();
                },
            });
            tabela.addFilter(function (rowData) {
                return filtrosExternos.matchesRecord(rowData);
            });
            registrarLimparFiltros(tabela, secFiltros, filtrosExternos);
        }
    }

    setSaveStatus("", "");
    definirProximaAnalise(analiseInput ? analiseInput.value : 1);
    if (cadastroForm) cadastroForm.addEventListener("submit", salvarNovoRegistro);
    if (limparDadosBtn) limparDadosBtn.addEventListener("click", limparDados);
    if (pdfBtn) pdfBtn.addEventListener("click", exportarPdf);
})();
