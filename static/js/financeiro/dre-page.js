(function () {
    var dataElement = document.getElementById("dre-tabulator-data");
    var tableTarget = document.getElementById("dre-tabulator");
    var secFiltros = document.getElementById("sec-filtros");
    var filtrosColunaEsquerda = document.getElementById("dre-filtros-coluna-esquerda");
    var filtrosColunaDireita = document.getElementById("dre-filtros-coluna-direita");
    var saveStatusEl = document.getElementById("dre-save-status");
    var kpiValorTotalEl = document.getElementById("dre-kpi-valor-total");

    if (!dataElement || !tableTarget || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var tabela = null;
    var externalFilters = null;
    var internalUpdate = false;
    var seqByRowId = {};
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});

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

    function normalizeText(value) {
        var text = toText(value).toLowerCase();
        if (!text) return "";
        if (typeof text.normalize === "function") {
            text = text.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        }
        return text;
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
        saveStatusEl.classList.remove("dre-save-status--ok", "dre-save-status--error", "dre-save-status--progress");
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function formatDateIsoToBr(dateIso) {
        var text = toText(dateIso);
        if (!text) return "";
        var parts = text.split("-");
        if (parts.length !== 3) return text;
        return parts[2] + "/" + parts[1] + "/" + parts[0];
    }

    function normalizarReceitaDespesa(item) {
        var text = normalizeText(item && item.receita_despesa);
        if (text === "receita") return "Receita";
        if (text === "despesa") return "Despesa";
        var valor = toNumber(item && item.valor_liquido);
        if (valor > 0) return "Receita";
        if (valor < 0) return "Despesa";
        return "";
    }

    function getVisibleRowsData() {
        if (!tabela) return data.slice();

        if (typeof tabela.getRows === "function") {
            var activeRows = tabela.getRows("active") || [];
            if (activeRows.length) {
                return activeRows.map(function (row) { return row.getData(); });
            }
        }

        if (typeof tabela.getData === "function") {
            var currentData = tabela.getData() || [];
            if (currentData.length) return currentData;
        }

        return data.slice();
    }

    function atualizarDashboard(rows) {
        var linhas = Array.isArray(rows) ? rows : [];
        var totalLiquido = 0;

        linhas.forEach(function (item) {
            var valorLiquido = toNumber(item && item.valor_liquido);
            totalLiquido += valorLiquido;
        });

        if (kpiValorTotalEl) kpiValorTotalEl.textContent = formatMoney(totalLiquido);
    }

    function createFilterDefinitions() {
        return [
            {
                key: "ano_baixa",
                label: "Ano",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.ano_baixa : "";
                },
            },
            {
                key: "nome_fantasia_empresa",
                label: "Nome Fantasia",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.nome_fantasia_empresa : "";
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

    function refreshFiltersAndDashboard() {
        setupExternalFilters();
        atualizarDashboard(getVisibleRowsData());
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
        var valorPagar = toText(rowData.valor_a_pagar) ? String(toNumber(rowData.valor_a_pagar).toFixed(2)) : "";
        return {
            valor_a_pagar: valorPagar,
            plano_contas_tipo_movimento: toText(rowData.plano_contas_tipo_movimento),
            tipo_dre: toText(rowData.tipo_dre),
        };
    }

    function rollbackField(row, rowData, field, oldValue) {
        if (!row || !rowData) return;
        var payload = Object.assign({}, rowData);
        payload[field] = oldValue;
        internalUpdate = true;
        Promise.resolve(row.update(payload)).finally(function () {
            internalUpdate = false;
        });
    }

    function saveEditedRow(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;
        var rowData = row.getData() || {};
        if (!rowData.editar_url) return;

        var field = typeof cell.getField === "function" ? cell.getField() : "";
        var oldValue = typeof cell.getOldValue === "function" ? cell.getOldValue() : null;
        var rowId = rowData.id;
        var currentSeq = Number(seqByRowId[rowId] || 0) + 1;
        seqByRowId[rowId] = currentSeq;

        var formData = new FormData();
        appendCsrfToken(formData);
        var payload = buildPayloadFromRow(rowData);
        Object.keys(payload).forEach(function (key) {
            formData.append(key, payload[key]);
        });

        setSaveStatus("Salvando alteracao...", "dre-save-status--progress");
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
                    rollbackField(row, rowData, field, oldValue);
                    setSaveStatus(
                        (result.body && result.body.message) ? result.body.message : "Falha ao salvar.",
                        "dre-save-status--error"
                    );
                    return;
                }

                internalUpdate = true;
                Promise.resolve(row.update(result.body.registro))
                    .then(function () {
                        var updated = row.getData() || {};
                        var index = data.findIndex(function (item) { return Number(item.id) === Number(updated.id); });
                        if (index >= 0) data[index] = updated;
                        refreshFiltersAndDashboard();
                        setSaveStatus("Salvo automaticamente.", "dre-save-status--ok");
                    })
                    .catch(function () {
                        rollbackField(row, rowData, field, oldValue);
                        setSaveStatus("Falha ao aplicar retorno no front.", "dre-save-status--error");
                    })
                    .finally(function () {
                        internalUpdate = false;
                    });
            })
            .catch(function () {
                if (seqByRowId[rowId] !== currentSeq) return;
                rollbackField(row, rowData, field, oldValue);
                setSaveStatus("Falha ao salvar. Alteracao revertida.", "dre-save-status--error");
            });
    }

    function initTable() {
        var createTable = (window.TabulatorDefaults && typeof window.TabulatorDefaults.create === "function")
            ? window.TabulatorDefaults.create
            : function (selector, options) { return new window.Tabulator(selector, options); };

        tabela = createTable("#dre-tabulator", {
            data: data,
            layout: "fitDataStretch",
            index: "id",
            height: "560px",
            reactiveData: false,
            headerFilterLiveFilterDelay: 300,
            columns: [
                {title: "ID", field: "id", hozAlign: "right", width: 75},
                {title: "Data da Baixa", field: "data_baixa", sorter: "string", headerFilter: "input", minWidth: 130},
                {title: "Dt. Vencimento", field: "data_vencimento", sorter: "string", headerFilter: "input", minWidth: 130},
                {title: "Nome Fantasia (Empresa)", field: "nome_fantasia_empresa", headerFilter: "input", minWidth: 220},
                {title: "Receita/Despesa", field: "receita_despesa", headerFilter: "input", minWidth: 140},
                {title: "Parceiro", field: "parceiro", headerFilter: "input", minWidth: 110},
                {title: "Nome Parceiro (Parceiro)", field: "nome_parceiro", headerFilter: "input", minWidth: 220},
                {title: "Nro Nota", field: "numero_nota", headerFilter: "input", minWidth: 120},
                {title: "Natureza", field: "natureza", headerFilter: "input", minWidth: 110},
                {title: "Descricao (Natureza)", field: "descricao_natureza", headerFilter: "input", minWidth: 220},
                {
                    title: "Valor Liquido",
                    field: "valor_liquido",
                    hozAlign: "right",
                    headerFilter: "input",
                    minWidth: 140,
                    formatter: function (cell) { return formatMoney(cell.getValue()); },
                },
                {
                    title: "Valor a Pagar",
                    field: "valor_a_pagar",
                    hozAlign: "right",
                    headerFilter: "input",
                    minWidth: 140,
                    editor: "input",
                    formatter: function (cell) {
                        var value = cell.getValue();
                        if (toText(value) === "") return "";
                        return formatMoney(value);
                    },
                },
                {title: "Descricao (Tipo de Operacao)", field: "descricao_tipo_operacao", headerFilter: "input", minWidth: 220},
                {title: "Descricao (Centro de Resultado)", field: "descricao_centro_resultado", headerFilter: "input", minWidth: 230},
                {
                    title: "Plano Contas.Tipo Movimento",
                    field: "plano_contas_tipo_movimento",
                    headerFilter: "input",
                    editor: "input",
                    minWidth: 200,
                },
                {
                    title: "Tipo DRE",
                    field: "tipo_dre",
                    headerFilter: "input",
                    editor: "input",
                    minWidth: 140,
                },
            ],
            rowFormatter: function (row) {
                var rowData = row.getData() || {};
                var editable = !!rowData.editar_url;
                var rowEl = row.getElement();
                if (!rowEl) return;
                if (editable) rowEl.classList.add("dre-row-editable");
                else rowEl.classList.remove("dre-row-editable");
            },
            dataFiltered: function (_filters, filteredRows) {
                var linhas = (filteredRows || []).map(function (row) { return row.getData(); });
                atualizarDashboard(linhas);
            },
            cellEdited: function (cell) {
                if (internalUpdate) return;
                var field = toText(cell.getField());
                if (field !== "valor_a_pagar" && field !== "plano_contas_tipo_movimento" && field !== "tipo_dre") {
                    return;
                }
                saveEditedRow(cell);
            },
            initialFilter: [],
        });

        if (typeof tabela.setFilter === "function") {
            tabela.setFilter(function (rowData) {
                return matchesGlobalFilters(rowData);
            });
        }
    }

    data.forEach(function (item) {
        item.data_baixa = item.data_baixa || formatDateIsoToBr(item.data_baixa_iso);
        item.data_vencimento = item.data_vencimento || formatDateIsoToBr(item.data_vencimento_iso);
    });

    initTable();
    bindClearFilterButtons();
    refreshFiltersAndDashboard();
})();
