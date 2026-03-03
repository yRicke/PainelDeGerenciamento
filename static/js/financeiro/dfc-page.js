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




