(function () {
    var form = document.getElementById("upload-dfc-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-dfc");
    var input = document.getElementById("arquivo-dfc-input");
    var confirmInput = document.getElementById("confirmar-substituicao-input");
    var fileStatus = document.getElementById("nome-arquivo-dfc-selecionado");
    var temArquivoExistente = form.dataset.temArquivoExistente === "1";
    var frontendText = window.FrontendText || {};
    var commonText = frontendText.common || {};
    var uploadText = frontendText.upload || {};
    var confirmText = frontendText.confirm || {};
    var arquivoXlsLabel = ".xls";

    function mensagemApenasArquivoPermitido() {
        if (typeof uploadText.onlyAllowedFile === "function") {
            return uploadText.onlyAllowedFile(arquivoXlsLabel);
        }
        return "Envie apenas arquivo .xls.";
    }

    function mensagemSelecionarArquivoParaContinuar() {
        if (typeof uploadText.selectFileToContinue === "function") {
            return uploadText.selectFileToContinue(arquivoXlsLabel);
        }
        return "Selecione um arquivo .xls para continuar.";
    }

    function atualizarNomeArquivo() {
        if (!input.files || !input.files.length) {
            fileStatus.textContent = "";
            return;
        }
        var selectedFilePrefix = commonText.selectedFilePrefix || "Arquivo selecionado: ";
        fileStatus.textContent = selectedFilePrefix + input.files[0].name;
    }

    function validarExtensaoXls(file) {
        return file && file.name.toLowerCase().endsWith(".xls");
    }

    function confirmarSubstituicaoSeNecessario() {
        if (!temArquivoExistente) {
            confirmInput.value = "0";
            return true;
        }
        var replaceCurrentFileMessage = confirmText.replaceCurrentFile || "Já existe um arquivo na pasta. Deseja substituir o arquivo atual?";
        if (!window.confirm(replaceCurrentFileMessage)) return false;
        confirmInput.value = "1";
        return true;
    }

    dropzone.addEventListener("click", function () {
        input.click();
    });

    dropzone.addEventListener("dragover", function (event) {
        event.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", function () {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", function (event) {
        event.preventDefault();
        dropzone.classList.remove("dragover");
        var files = event.dataTransfer.files;
        if (!files || !files.length) return;
        if (!validarExtensaoXls(files[0])) {
            window.alert(mensagemApenasArquivoPermitido());
            return;
        }
        input.files = files;
        atualizarNomeArquivo();
    });

    input.addEventListener("change", function () {
        if (!input.files || !input.files.length) return;
        if (!validarExtensaoXls(input.files[0])) {
            window.alert(mensagemApenasArquivoPermitido());
            input.value = "";
        }
        atualizarNomeArquivo();
    });

    form.addEventListener("submit", function (event) {
        if (!input.files || !input.files.length) {
            event.preventDefault();
            window.alert(mensagemSelecionarArquivoParaContinuar());
            return;
        }
        if (!validarExtensaoXls(input.files[0])) {
            event.preventDefault();
            window.alert(mensagemApenasArquivoPermitido());
            return;
        }
        if (temArquivoExistente && confirmInput.value !== "1" && !confirmarSubstituicaoSeNecessario()) {
            event.preventDefault();
        }
    });
})();

(function () {
    var dataElement = document.getElementById("dfc-tabulator-data");
    if (!dataElement) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var tabelaTarget = document.getElementById("dfc-tabulator");
    var receitaEl = document.getElementById("dfc-kpi-receita");
    var despesaEl = document.getElementById("dfc-kpi-despesa");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});
    var nomesMeses = [
        "Janeiro", "Fevereiro", "Mar\u00e7o", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ];

    function toText(valor) {
        if (valor === null || valor === undefined) return "";
        return String(valor).trim();
    }

    function normalizeText(valor) {
        return toText(valor)
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
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
            || section.querySelector("#dfc-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#dfc-filtros-coluna-direita");

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
            left.id = "dfc-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "dfc-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    function mesLabel(valor) {
        var mes = Number(valor || 0);
        if (!mes || mes < 1 || mes > 12) return "(Vazio)";
        return nomesMeses[mes - 1];
    }

    function normalizarTipo(item) {
        var valor = Number(item.valor_liquido || 0);
        if (valor > 0) return "receita";
        if (valor < 0) return "despesa";

        var tipoMovimento = normalizeText(item.tipo_movimento || "");
        if (tipoMovimento.includes("receita")) return "receita";
        if (tipoMovimento.includes("despesa")) return "despesa";

        var tipo = normalizeText(item.operacao_descricao || "");
        if (tipo.includes("receita")) return "receita";
        if (tipo.includes("despesa")) return "despesa";
        return "";
    }

    function tipoLancamentoLabel(item) {
        var tipo = normalizarTipo(item);
        if (tipo === "receita") return "Receita";
        if (tipo === "despesa") return "Despesa";
        return "(Vazio)";
    }

    function tituloTipoLabel(item) {
        var codigo = toText(item && item.titulo_codigo);
        var descricao = toText(item && item.titulo_descricao);
        if (codigo && descricao) return codigo + " - " + descricao;
        return codigo || descricao || "";
    }

    function tipoOperacaoLabel(item) {
        var descricao = toText(item && item.operacao_descricao);
        var codigo = toText(item && item.operacao_codigo);
        return descricao || codigo || "";
    }

    function atualizarDashboard(linhas) {
        var totalReceita = 0;
        var totalDespesa = 0;

        (linhas || []).forEach(function (item) {
            var valor = Number(item.valor_liquido || 0);
            var tipo = normalizarTipo(item);
            if (tipo === "receita") totalReceita += valor;
            if (tipo === "despesa") totalDespesa += valor;
        });

        if (receitaEl) receitaEl.textContent = totalReceita ? formatadorMoeda.format(totalReceita) : "R$ -";
        if (despesaEl) despesaEl.textContent = totalDespesa ? formatadorMoeda.format(Math.abs(totalDespesa)) : "R$ -";
    }

    function criarDefinicoesFiltrosDfc() {
        return [
            {
                key: "receita_despesa",
                label: "Receita/Despesa",
                singleSelect: true,
                extractValue: function (rowData) {
                    return tipoLancamentoLabel(rowData);
                },
                formatValue: formatTextoOuVazio,
                sortOptions: function (a, b) {
                    var ordem = {"Receita": 0, "Despesa": 1, "(Vazio)": 2};
                    var ordemA = Object.prototype.hasOwnProperty.call(ordem, a.label) ? ordem[a.label] : 99;
                    var ordemB = Object.prototype.hasOwnProperty.call(ordem, b.label) ? ordem[b.label] : 99;
                    if (ordemA !== ordemB) return ordemA - ordemB;
                    return ordenarTexto(a, b);
                },
            },
            {
                key: "empresa_nome",
                label: "Empresa",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.empresa_nome : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "ano_negociacao",
                label: "Ano",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.ano_negociacao : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: function (a, b) {
                    return Number(b.value || 0) - Number(a.value || 0);
                },
            },
            {
                key: "mes_negociacao",
                label: "M\u00eas",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.mes_negociacao : "";
                },
                formatValue: mesLabel,
                sortOptions: function (a, b) {
                    return Number(a.value || 0) - Number(b.value || 0);
                },
            },
            {
                key: "tipo_titulo",
                label: "Tipo de T\u00edtulo",
                singleSelect: false,
                extractValue: function (rowData) {
                    return tituloTipoLabel(rowData);
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "centro_resultado",
                label: "Centro de Resultado",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.centro_resultado_descricao : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "tipo_operacao",
                label: "Tipo de Opera\u00e7\u00e3o",
                singleSelect: false,
                extractValue: function (rowData) {
                    return tipoOperacaoLabel(rowData);
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "tipo_movimento",
                label: "Tipo de Movimento",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.tipo_movimento : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
        ];
    }

    function configurarFiltrosExternos(tabela, registros, secFiltros) {
        if (!tabela || !secFiltros || !window.ModuleFilterCore) return null;

        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholderFiltros = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholderFiltros) placeholderFiltros.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (!filtroColumns || !filtroColumns.left || !filtroColumns.right) return null;

        var filtrosExternos = window.ModuleFilterCore.create({
            data: registros,
            definitions: criarDefinicoesFiltrosDfc(),
            leftColumn: filtroColumns.left,
            rightColumn: filtroColumns.right,
            onChange: function () {
                if (typeof tabela.refreshFilter === "function") {
                    tabela.refreshFilter();
                }
            },
        });

        tabela.addFilter(function (rowData) {
            return filtrosExternos.matchesRecord(rowData);
        });

        return {secFiltros: secFiltros, filtrosExternos: filtrosExternos};
    }

    function registrarAcaoLimparFiltros(tabela, secFiltros, filtrosExternos) {
        if (!tabela || !secFiltros || !filtrosExternos) return;

        function limparTodosFiltros() {
            if (typeof filtrosExternos.clearAllFilters === "function") {
                filtrosExternos.clearAllFilters();
            }
            if (typeof tabela.clearHeaderFilter === "function") {
                tabela.clearHeaderFilter();
            }
            if (typeof tabela.refreshFilter === "function") {
                tabela.refreshFilter();
            }
        }

        var limparFiltrosSidebarBtn = secFiltros.querySelector(".module-filters-clear-all");
        var limparFiltrosToolbarBtn = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
        if (limparFiltrosSidebarBtn) {
            limparFiltrosSidebarBtn.addEventListener("click", limparTodosFiltros);
        }
        if (limparFiltrosToolbarBtn) {
            limparFiltrosToolbarBtn.addEventListener("click", limparTodosFiltros);
        }
    }

    if (!tabelaTarget || !window.Tabulator || !window.TabulatorDefaults) {
        atualizarDashboard(data);
        return;
    }

    var colunas = [
        {title: "Empresa", field: "empresa_nome"},
        {title: "Data de Negociação", field: "data_negociacao"},
        {title: "Data de Vencimento", field: "data_vencimento"},
        {title: "Valor Líquido", field: "valor_liquido"},
        {title: "Número da Nota", field: "numero_nota"},
        {title: "Nome do Parceiro", field: "parceiro_nome"},
        {title: "Tipo de Título", field: "titulo_codigo"},
        {title: "Descrição do Tipo de Título", field: "titulo_descricao"},
        {title: "Descrição do Centro de Resultado", field: "centro_resultado_descricao"},
        {title: "Descrição do Tipo de Operação", field: "operacao_descricao"},
        {title: "Natureza", field: "natureza_codigo"},
        {title: "Descrição da Natureza", field: "natureza_descricao"},
        {title: "Histórico", field: "historico"},
        {title: "Código do Parceiro", field: "parceiro_codigo"},
        {title: "Tipo de Operação", field: "operacao_codigo"},
        {title: "Receita/Despesa", field: "operacao_descricao"},
        {title: "Tipo de Movimento", field: "tipo_movimento"},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data, {
        width: 110,
        formatter: function (cell) {
            var url = cell.getValue();
            if (!url) return "";
            return '<button type="button" class="btn-primary js-editar-dfc">Editar</button>';
        },
        cellClick: function (e, cell) {
            var row = cell.getRow().getData();
            var target = e.target && e.target.closest ? e.target.closest(".js-editar-dfc") : null;
            if (!target || !row.editar_url) return;
            window.location.href = row.editar_url;
        },
    });

    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros) {
        secFiltros.dataset.moduleFiltersAuto = "off";
    }

    var tabela = window.TabulatorDefaults.create("#dfc-tabulator", {
        data: data,
        columns: colunas,
        freezeUX: {
            enabled: true,
        },
    });

    var filtrosConfig = configurarFiltrosExternos(tabela, data, secFiltros);
    if (filtrosConfig) {
        registrarAcaoLimparFiltros(tabela, filtrosConfig.secFiltros, filtrosConfig.filtrosExternos);
    }

    function atualizarDashboardComTabela() {
        var linhasAtivas = tabela.getData("active");
        if (!Array.isArray(linhasAtivas)) linhasAtivas = tabela.getData() || [];
        atualizarDashboard(linhasAtivas);
    }

    tabela.on("tableBuilt", atualizarDashboardComTabela);
    tabela.on("dataLoaded", atualizarDashboardComTabela);
    tabela.on("dataFiltered", atualizarDashboardComTabela);
    tabela.on("renderComplete", atualizarDashboardComTabela);
    setTimeout(atualizarDashboardComTabela, 0);
})();




(function () {
    var dataElement = document.getElementById("dfc-saldo-planejado-data");
    var wrapper = document.getElementById("dfc-saldo-table-wrapper");
    if (!dataElement || !wrapper) return;

    var payload = {};
    try {
        payload = JSON.parse(dataElement.textContent || "{}");
    } catch (err) {
        return;
    }

    var columns = Array.isArray(payload.columns) ? payload.columns : [];
    var sourceRows = Array.isArray(payload.rows) ? payload.rows : [];
    if (!columns.length || !sourceRows.length) return;

    var includePrevisoesInput = document.getElementById("dfc-saldo-incluir-previsoes");
    var includeOutrasInput = document.getElementById("dfc-saldo-incluir-outras");
    var saveStatus = document.getElementById("dfc-saldo-save-status");
    var saldoAtualEl = document.getElementById("dfc-kpi-saldo-atual");
    var saldoPeriodoEl = document.getElementById("dfc-kpi-saldo-periodo");
    var saldoDiferencaEl = document.getElementById("dfc-kpi-saldo-diferenca");
    var saveUrl = window.location.pathname;
    var KPI_DIFF_CLASSES = ["dfc-kpi-saldo-diff-positive", "dfc-kpi-saldo-diff-negative", "dfc-kpi-saldo-diff-neutral"];
    var SAVE_STATUS_CLASSES = ["dfc-saldo-save-ok", "dfc-saldo-save-error"];

    var checkboxDefaults = payload.checkbox_defaults || {};
    if (includePrevisoesInput && typeof checkboxDefaults.incluir_previsoes === "boolean") {
        includePrevisoesInput.checked = checkboxDefaults.incluir_previsoes;
    }
    if (includeOutrasInput && typeof checkboxDefaults.incluir_outras_consideracoes === "boolean") {
        includeOutrasInput.checked = checkboxDefaults.incluir_outras_consideracoes;
    }

    function toNumber(value) {
        var num = Number(value);
        return Number.isFinite(num) ? num : 0;
    }

    function cloneRow(row) {
        var values = {};
        var srcValues = row && row.values ? row.values : {};
        Object.keys(srcValues).forEach(function (key) {
            var val = srcValues[key];
            values[key] = val === null || val === undefined ? null : toNumber(val);
        });
        return {
            key: row.key || "",
            label: row.label || "",
            group: row.group || "",
            editable_day: !!row.editable_day,
            manual_tipo: row.manual_tipo || "",
            values: values,
            is_detail: !!row.is_detail,
            parent_key: row.parent_key || "",
            has_children: !!row.has_children,
            expanded_default: !!row.expanded_default,
            use_checkbox: !!row.use_checkbox,
            checked: row.checked_default !== false,
            uses_special_day_rule: !!row.uses_special_day_rule,
        };
    }

    var rows = sourceRows.map(cloneRow);
    var rowMap = {};
    rows.forEach(function (row) {
        rowMap[row.key] = row;
    });
    var contasReceberBaselineValues = {};
    if (rowMap.contas_receber && rowMap.contas_receber.values) {
        Object.keys(rowMap.contas_receber.values).forEach(function (key) {
            contasReceberBaselineValues[key] = rowMap.contas_receber.values[key];
        });
    }
    var dayColumns = columns.filter(function (col) {
        return col && col.kind === "day";
    });
    var detailRowsByParent = {};
    rows.forEach(function (row) {
        if (!row.is_detail || !row.parent_key) return;
        if (!detailRowsByParent[row.parent_key]) {
            detailRowsByParent[row.parent_key] = [];
        }
        detailRowsByParent[row.parent_key].push(row);
    });
    var parentExpanded = {};
    Object.keys(detailRowsByParent).forEach(function (parentKey) {
        var parentRow = rowMap[parentKey];
        parentExpanded[parentKey] = parentRow ? !!parentRow.expanded_default : false;
    });

    function formatCurrencyOrDash(value) {
        var num = toNumber(value);
        if (!num) return "R$ -";
        var abs = Math.abs(num).toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
        if (num < 0) return "-R$ " + abs;
        return "R$ " + abs;
    }

    function formatInputNumber(value) {
        var num = toNumber(value);
        if (!num) return "";
        return num.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }

    function parseInputNumber(text) {
        var raw = String(text || "").trim();
        if (!raw) return 0;
        raw = raw.replace(/[R$\s]/g, "");
        if (raw.indexOf(",") >= 0) {
            raw = raw.replace(/\./g, "").replace(",", ".");
        }
        var parsed = Number(raw);
        if (!Number.isFinite(parsed)) return 0;
        return Math.round(parsed * 100) / 100;
    }

    function getCsrfToken() {
        var input = document.querySelector("input[name='csrfmiddlewaretoken']");
        if (input && input.value) return input.value;
        if (!document.cookie) return "";
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i += 1) {
            var cookie = cookies[i].trim();
            if (cookie.indexOf("csrftoken=") === 0) {
                return decodeURIComponent(cookie.substring("csrftoken=".length));
            }
        }
        return "";
    }

    function replaceClasses(element, classes, nextClass) {
        if (!element) return;
        classes.forEach(function (className) {
            element.classList.remove(className);
        });
        if (nextClass) {
            element.classList.add(nextClass);
        }
    }

    function setSaveStatus(text, cls) {
        if (!saveStatus) return;
        saveStatus.textContent = text || "";
        replaceClasses(saveStatus, SAVE_STATUS_CLASSES, cls);
    }

    function sumDayColumns(row) {
        var total = 0;
        dayColumns.forEach(function (col) {
            total += toNumber(row.values[col.key]);
        });
        return Math.round(total * 100) / 100;
    }

    function updateTotalPeriodoByRowKey(rowKey) {
        var row = rowMap[rowKey];
        if (!row || !row.values) return;
        row.values.total_periodo = sumDayColumns(row);
    }

    function round2(value) {
        return Math.round(toNumber(value) * 100) / 100;
    }

    function formatCurrencyKpi(value) {
        var num = toNumber(value);
        var abs = Math.abs(num).toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
        if (num < 0) return "-R$ " + abs;
        return "R$ " + abs;
    }

    function updateSaldoKpiCard() {
        if (!saldoAtualEl && !saldoPeriodoEl && !saldoDiferencaEl) return;
        var saldoFinal = rowMap.saldo_final || {values: {}};
        var firstDayKey = dayColumns.length ? dayColumns[0].key : "";
        var lastDayKey = dayColumns.length ? dayColumns[dayColumns.length - 1].key : "";
        var saldoAtual = firstDayKey ? toNumber(saldoFinal.values[firstDayKey]) : 0;
        var saldoPeriodo = lastDayKey ? toNumber(saldoFinal.values[lastDayKey]) : 0;
        var diferenca = round2(saldoPeriodo - saldoAtual);

        if (saldoAtualEl) saldoAtualEl.textContent = formatCurrencyKpi(saldoAtual);
        if (saldoPeriodoEl) saldoPeriodoEl.textContent = formatCurrencyKpi(saldoPeriodo);
        if (saldoDiferencaEl) {
            saldoDiferencaEl.textContent = formatCurrencyKpi(diferenca);
            var diffClass = "dfc-kpi-saldo-diff-neutral";
            if (diferenca > 0) diffClass = "dfc-kpi-saldo-diff-positive";
            else if (diferenca < 0) diffClass = "dfc-kpi-saldo-diff-negative";
            replaceClasses(saldoDiferencaEl, KPI_DIFF_CLASSES, diffClass);
        }
    }

    function recalculateContasReceberFromDetails() {
        var parent = rowMap.contas_receber;
        var details = detailRowsByParent.contas_receber || [];
        if (!parent || !details.length) return;
        var enabledDetails = details.filter(function (detailRow) {
            return detailRow.checked !== false;
        });

        if (enabledDetails.length === details.length) {
            Object.keys(contasReceberBaselineValues).forEach(function (key) {
                parent.values[key] = contasReceberBaselineValues[key];
            });
            return;
        }

        columns.forEach(function (column) {
            parent.values[column.key] = 0;
        });
        enabledDetails.forEach(function (detailRow) {
            columns.forEach(function (column) {
                var key = column.key;
                parent.values[key] = round2(toNumber(parent.values[key]) + toNumber(detailRow.values[key]));
            });
        });

        var finalDayKey = dayColumns.length ? dayColumns[dayColumns.length - 1].key : "";
        if (finalDayKey) {
            parent.values[finalDayKey] = round2(toNumber(parent.values.total_posterior));
        }
    }

    function recalculateComputedRows() {
        recalculateContasReceberFromDetails();

        var contasReceber = rowMap.contas_receber || {values: {}};
        var previsaoRecebivel = rowMap.previsao_recebivel || {values: {}};
        var outrasReceita = rowMap.outras_consideracoes_receita || {values: {}};
        var contasPagar = rowMap.contas_pagar || {values: {}};
        var adiantamentosPrevisao = rowMap.adiantamentos_previsao || {values: {}};
        var outrasDespesa = rowMap.outras_consideracoes_despesa || {values: {}};
        var saldoInicial = rowMap.saldo_inicial || {values: {}};
        var saldoDia = rowMap.saldo_dia || {values: {}};
        var saldoFinal = rowMap.saldo_final || {values: {}};

        var incluirPrevisoes = includePrevisoesInput ? !!includePrevisoesInput.checked : true;
        var incluirOutras = includeOutrasInput ? !!includeOutrasInput.checked : true;
        var saldoFinalAnterior = 0;

        dayColumns.forEach(function (col, index) {
            var key = col.key;
            if (index === 0) {
                saldoInicial.values[key] = 0;
            } else {
                saldoInicial.values[key] = saldoFinalAnterior;
            }

            var entradas = toNumber(contasReceber.values[key]);
            var saidas = toNumber(contasPagar.values[key]);
            if (incluirPrevisoes) {
                entradas += toNumber(previsaoRecebivel.values[key]);
                saidas += toNumber(adiantamentosPrevisao.values[key]);
            }
            if (incluirOutras) {
                entradas += toNumber(outrasReceita.values[key]);
                saidas += toNumber(outrasDespesa.values[key]);
            }

            var saldoDiaValor = Math.round((entradas - saidas) * 100) / 100;
            var saldoFinalValor = Math.round((toNumber(saldoInicial.values[key]) + saldoDiaValor) * 100) / 100;

            saldoDia.values[key] = saldoDiaValor;
            saldoFinal.values[key] = saldoFinalValor;
            saldoFinalAnterior = saldoFinalValor;
        });

        [
            "previsao_recebivel",
            "outras_consideracoes_receita",
            "adiantamentos_previsao",
            "outras_consideracoes_despesa",
            "saldo_dia",
            "saldo_final",
        ].forEach(updateTotalPeriodoByRowKey);
        updateSaldoKpiCard();
    }

    function saveManualValue(row, column, value, previousValue) {
        var csrfToken = getCsrfToken();
        if (!csrfToken || !row.manual_tipo || !column.date_iso) return;

        setSaveStatus("Salvando...", "");
        var formData = new FormData();
        formData.append("csrfmiddlewaretoken", csrfToken);
        formData.append("acao", "salvar_dfc_saldo_manual");
        formData.append("tipo", row.manual_tipo);
        formData.append("data_referencia", column.date_iso);
        formData.append("valor", String(value));

        fetch(saveUrl, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        })
            .then(function (response) {
                return response
                    .json()
                    .catch(function () {
                        return {};
                    })
                    .then(function (body) {
                        return {ok: response.ok, body: body};
                    });
            })
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false) {
                    row.values[column.key] = previousValue;
                    recalculateComputedRows();
                    renderTable();
                    setSaveStatus(result.body && result.body.message ? result.body.message : "Falha ao salvar.", "dfc-saldo-save-error");
                    return;
                }
                setSaveStatus("Salvo", "dfc-saldo-save-ok");
            })
            .catch(function () {
                row.values[column.key] = previousValue;
                recalculateComputedRows();
                renderTable();
                setSaveStatus("Falha ao salvar.", "dfc-saldo-save-error");
            });
    }

    function bindManualInput(input, row, column) {
        if (!input || !row || !column) return;

        function commitValue() {
            var previousValue = toNumber(row.values[column.key]);
            var parsedValue = parseInputNumber(input.value);
            if (Math.abs(parsedValue - previousValue) < 0.0001) {
                input.value = formatInputNumber(parsedValue);
                return;
            }

            row.values[column.key] = parsedValue;
            recalculateComputedRows();
            renderTable();
            saveManualValue(row, column, parsedValue, previousValue);
        }

        input.addEventListener("blur", commitValue);
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                input.blur();
            }
        });
    }

    function renderTable() {
        recalculateComputedRows();

        var table = document.createElement("table");
        table.className = "dfc-saldo-table";

        var thead = document.createElement("thead");
        var headRow = document.createElement("tr");
        var lineHeader = document.createElement("th");
        lineHeader.className = "dfc-saldo-col-label";
        lineHeader.textContent = "Linha";
        headRow.appendChild(lineHeader);
        columns.forEach(function (column) {
            var th = document.createElement("th");
            th.textContent = column.label || "";
            headRow.appendChild(th);
        });
        thead.appendChild(headRow);
        table.appendChild(thead);

        var tbody = document.createElement("tbody");
        rows.forEach(function (row) {
            if (row.is_detail && !parentExpanded[row.parent_key]) return;

            var tr = document.createElement("tr");
            tr.classList.add("dfc-saldo-row-" + (row.group || "total"));
            if (row.key === "contas_pagar" || row.key === "saldo_dia") {
                tr.classList.add("dfc-saldo-row-separator");
            }
            if (row.is_detail) {
                tr.classList.add("dfc-saldo-row-detail");
                if (row.uses_special_day_rule) {
                    tr.classList.add("dfc-saldo-row-detail-special");
                }
                if (row.checked === false) {
                    tr.classList.add("dfc-saldo-row-detail-unchecked");
                }
            }

            var labelTd = document.createElement("td");
            var labelWrap = document.createElement("div");
            labelWrap.className = "dfc-saldo-label-wrap";

            if (row.has_children) {
                var expandBtn = document.createElement("button");
                expandBtn.type = "button";
                expandBtn.className = "dfc-saldo-expand-btn";
                expandBtn.textContent = parentExpanded[row.key] ? "-" : "+";
                expandBtn.addEventListener("click", function () {
                    parentExpanded[row.key] = !parentExpanded[row.key];
                    renderTable();
                });
                labelWrap.appendChild(expandBtn);
            } else if (row.is_detail) {
                var spacer = document.createElement("span");
                spacer.className = "dfc-saldo-expand-spacer";
                spacer.textContent = "";
                labelWrap.appendChild(spacer);
            }

            if (row.is_detail && row.use_checkbox) {
                var checkbox = document.createElement("input");
                checkbox.type = "checkbox";
                checkbox.className = "dfc-saldo-line-checkbox";
                checkbox.checked = row.checked !== false;
                checkbox.addEventListener("change", function () {
                    row.checked = !!checkbox.checked;
                    renderTable();
                });
                labelWrap.appendChild(checkbox);
            }

            var labelText = document.createElement("span");
            labelText.textContent = row.label || "";
            if (row.is_detail) {
                labelText.className = "dfc-saldo-detail-label";
            }
            labelWrap.appendChild(labelText);

            labelTd.appendChild(labelWrap);
            tr.appendChild(labelTd);

            columns.forEach(function (column) {
                var td = document.createElement("td");
                var value = row.values[column.key];

                if (row.editable_day && column.kind === "day") {
                    var input = document.createElement("input");
                    input.type = "text";
                    input.className = "dfc-saldo-input";
                    input.value = formatInputNumber(value);
                    td.appendChild(input);
                    bindManualInput(input, row, column);
                } else {
                    var span = document.createElement("span");
                    span.className = "dfc-saldo-cell-value";
                    span.textContent = value === null || value === undefined ? "R$ -" : formatCurrencyOrDash(value);
                    if (toNumber(value) < 0) {
                        span.classList.add("dfc-saldo-cell-negative");
                    }
                    td.appendChild(span);
                }

                tr.appendChild(td);
            });

            tbody.appendChild(tr);
        });
        table.appendChild(tbody);

        wrapper.innerHTML = "";
        wrapper.appendChild(table);
    }

    if (includePrevisoesInput) {
        includePrevisoesInput.addEventListener("change", renderTable);
    }
    if (includeOutrasInput) {
        includeOutrasInput.addEventListener("change", renderTable);
    }

    renderTable();
})();
