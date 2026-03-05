(function () {
    var form = document.getElementById("upload-faturamento-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-faturamento");
    var input = document.getElementById("arquivo-faturamento-input");
    var fileStatus = document.getElementById("nome-arquivo-faturamento-selecionado");
    var temArquivoExistente = form.dataset.temArquivoExistente === "1";

    function isArquivoVisivel(file) {
        if (!file) return false;
        var caminho = String(file.webkitRelativePath || file.name || "").replace(/\\/g, "/");
        if (!caminho) return false;

        var partes = caminho.split("/").filter(Boolean);
        if (!partes.length) return false;
        var nome = partes[partes.length - 1];
        if (!nome || nome.startsWith("~$") || nome.startsWith(".")) return false;
        for (var i = 0; i < partes.length; i += 1) {
            if (partes[i].startsWith(".")) return false;
        }
        return true;
    }

    function coletarArquivosXlsx(files) {
        if (!files || !files.length) return [];
        return Array.from(files).filter(function (file) {
            return isArquivoVisivel(file) && String(file.name || "").toLowerCase().endsWith(".xlsx");
        });
    }

    function atualizarStatus() {
        var arquivosXlsx = coletarArquivosXlsx(input.files);
        if (!arquivosXlsx.length) {
            fileStatus.textContent = "";
            return;
        }
        fileStatus.textContent = arquivosXlsx.length + " arquivo(s) .xlsx selecionado(s).";
    }

    function confirmarSubstituicaoSeNecessario() {
        if (!temArquivoExistente) return true;
        return window.confirm("Ja existe lote na pasta de importacao. Deseja substituir o lote atual?");
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
        if (!event.dataTransfer || !event.dataTransfer.files || !event.dataTransfer.files.length) return;
        input.files = event.dataTransfer.files;
        atualizarStatus();
    });

    input.addEventListener("change", atualizarStatus);

    form.addEventListener("submit", function (event) {
        var arquivosXlsx = coletarArquivosXlsx(input.files);
        if (!arquivosXlsx.length) {
            event.preventDefault();
            window.alert("Selecione uma pasta com arquivos .xlsx para continuar.");
            return;
        }
        if (!confirmarSubstituicaoSeNecessario()) {
            event.preventDefault();
        }
    });
})();

(function () {
    var dataElement = document.getElementById("faturamento-tabulator-data");
    if (!dataElement) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var tabelaTarget = document.getElementById("faturamento-tabulator");
    var quantidadeEl = document.getElementById("faturamento-kpi-quantidade");
    var valorUnicoEl = document.getElementById("faturamento-kpi-valor-unico");
    var valorFreteEl = document.getElementById("faturamento-kpi-valor-frete");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});
    var nomesMeses = [
        "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ];

    function toText(valor) {
        if (valor === null || valor === undefined) return "";
        return String(valor).trim();
    }

    function formatTextoOuVazio(valor) {
        return toText(valor) || "(Vazio)";
    }

    function normalizeText(valor) {
        return toText(valor)
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
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
            || section.querySelector("#faturamento-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#faturamento-filtros-coluna-direita");

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
            left.id = "faturamento-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "faturamento-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    function mesLabel(valor) {
        var mes = Number(valor || 0);
        if (!mes || mes < 1 || mes > 12) return "(Vazio)";
        return nomesMeses[mes - 1];
    }

    function formatPercentual(valor, casas) {
        var decimais = Number(casas || 3);
        var numero = Number(valor || 0);
        var texto = numero.toFixed(decimais).replace(".", ",");
        return texto + "%";
    }

    function formatMoedaCell(cell) {
        return formatadorMoeda.format(Number(cell.getValue() || 0));
    }

    function formatPercentualCell(cell) {
        return formatPercentual(cell.getValue(), 3);
    }

    function formatPercentualClienteCell(cell) {
        return formatPercentual(cell.getValue(), 2);
    }

    function atualizarDashboard(linhas) {
        var itens = Array.isArray(linhas) ? linhas : [];
        var totalValorUnico = 0;
        var totalValorFrete = 0;

        itens.forEach(function (item) {
            totalValorUnico += Number(item.valor_nota_unico || 0);
            totalValorFrete += Number(item.valor_frete || 0);
        });

        if (quantidadeEl) quantidadeEl.textContent = String(itens.length);
        if (valorUnicoEl) valorUnicoEl.textContent = formatadorMoeda.format(totalValorUnico);
        if (valorFreteEl) valorFreteEl.textContent = formatadorMoeda.format(totalValorFrete);
    }

    function criarDefinicoesFiltrosFaturamento() {
        return [
            {
                key: "nome_empresa",
                label: "Empresa",
                singleSelect: true,
                extractValue: function (rowData) { return rowData ? rowData.nome_empresa : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "ano_faturamento",
                label: "Ano",
                singleSelect: true,
                extractValue: function (rowData) { return rowData ? rowData.ano_faturamento : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: function (a, b) { return Number(b.value || 0) - Number(a.value || 0); },
            },
            {
                key: "mes_faturamento",
                label: "Mes",
                singleSelect: true,
                extractValue: function (rowData) { return rowData ? rowData.mes_faturamento : ""; },
                formatValue: mesLabel,
                sortOptions: function (a, b) { return Number(a.value || 0) - Number(b.value || 0); },
            },
            {
                key: "status_nfe",
                label: "Status NF-e",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.status_nfe : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "tipo_venda",
                label: "Tipo da Venda",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.tipo_venda : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "operacao_descricao",
                label: "Descricao (Tipo de Operacao)",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.operacao_descricao : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "cidade_parceiro",
                label: "Cidade Parceiro",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.cidade_parceiro : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "gerente",
                label: "Gerente",
                singleSelect: false,
                extractValue: function (rowData) {
                    var valor = rowData ? rowData.gerente : "";
                    var token = normalizeText(valor);
                    if (token === "sem gerente" || token === "<sem gerente>" || token === "sem vendedor" || token === "<sem vendedor>") {
                        return "";
                    }
                    return valor;
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
            definitions: criarDefinicoesFiltrosFaturamento(),
            leftColumn: filtroColumns.left,
            rightColumn: filtroColumns.right,
            onChange: function () {
                if (typeof tabela.refreshFilter === "function") tabela.refreshFilter();
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
            if (typeof filtrosExternos.clearAllFilters === "function") filtrosExternos.clearAllFilters();
            if (typeof tabela.clearHeaderFilter === "function") tabela.clearHeaderFilter();
            if (typeof tabela.refreshFilter === "function") tabela.refreshFilter();
        }

        var limparFiltrosSidebarBtn = secFiltros.querySelector(".module-filters-clear-all");
        var limparFiltrosToolbarBtn = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
        if (limparFiltrosSidebarBtn) limparFiltrosSidebarBtn.addEventListener("click", limparTodosFiltros);
        if (limparFiltrosToolbarBtn) limparFiltrosToolbarBtn.addEventListener("click", limparTodosFiltros);
    }

    if (!tabelaTarget || !window.Tabulator || !window.TabulatorDefaults) {
        atualizarDashboard(data);
        return;
    }

    var colunas = [
        {title: "Nome Origem", field: "nome_origem"},
        {title: "Dt. do Faturamento", field: "data_faturamento"},
        {title: "Nome Empresa", field: "nome_empresa"},
        {title: "Parceiro", field: "parceiro_label"},
        {title: "Nro. Nota", field: "numero_nota"},
        {title: "Vlr. Nota", field: "valor_nota", formatter: formatMoedaCell},
        {title: "%Part. Venda Geral", field: "participacao_venda_geral", formatter: formatPercentualCell},
        {title: "%Part. Venda Cliente", field: "participacao_venda_cliente", formatter: formatPercentualClienteCell},
        {title: "Vlr. Nota (Unico)", field: "valor_nota_unico", formatter: formatMoedaCell},
        {title: "Peso Bruto (Unico)", field: "peso_bruto_unico"},
        {title: "Qtd. Volumes", field: "quantidade_volumes"},
        {title: "Qtd. Saida", field: "quantidade_saida"},
        {title: "Status NF-e", field: "status_nfe"},
        {title: "Apelido (Vendedor)", field: "apelido_vendedor"},
        {title: "Descricao (Tipo de Operacao)", field: "operacao_descricao"},
        {title: "Descricao (Natureza)", field: "natureza_descricao"},
        {title: "Descricao (Centro de Resultado)", field: "centro_resultado_descricao"},
        {title: "Tipo de Movimento", field: "tipo_movimento"},
        {title: "Prazo Medio [SAFIA]", field: "prazo_medio_safia"},
        {title: "Media (Unica)", field: "media_unica"},
        {title: "Tipo da Venda", field: "tipo_venda"},
        {title: "Produto", field: "produto_label"},
        {title: "Cidade Parceiro [SAFIA]", field: "cidade_parceiro"},
        {title: "Gerente", field: "gerente"},
        {title: "Descricao (Perfil)", field: "descricao_perfil"},
        {title: "Valor Frete", field: "valor_frete", formatter: formatMoedaCell},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data, {
        width: 110,
        formatter: function (cell) {
            var url = cell.getValue();
            if (!url) return "";
            return '<button type="button" class="btn-primary js-editar-faturamento">Editar</button>';
        },
        cellClick: function (e, cell) {
            var row = cell.getRow().getData();
            var target = e.target && e.target.closest ? e.target.closest(".js-editar-faturamento") : null;
            if (!target || !row.editar_url) return;
            window.location.href = row.editar_url;
        },
    });

    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros) secFiltros.dataset.moduleFiltersAuto = "off";

    var tabela = window.TabulatorDefaults.create("#faturamento-tabulator", {
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
