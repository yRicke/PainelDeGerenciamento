(function () {
    var form = document.getElementById("upload-controle-margem-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-controle-margem");
    var input = document.getElementById("arquivo-controle-margem-input");
    var confirmInput = document.getElementById("confirmar-substituicao-input");
    var fileStatus = document.getElementById("nome-arquivo-controle-margem-selecionado");
    var loadingStatus = document.getElementById("controle-margem-loading-status");
    var temArquivoExistente = form.dataset.temArquivoExistente === "1";
    var frontendText = window.FrontendText || {};
    var commonText = frontendText.common || {};
    var uploadText = frontendText.upload || {};
    var confirmText = frontendText.confirm || {};
    var arquivoXlsOuXlsxLabel = ".xls ou .xlsx";

    function mensagemApenasArquivoPermitido() {
        if (typeof uploadText.onlyAllowedFile === "function") {
            return uploadText.onlyAllowedFile(arquivoXlsOuXlsxLabel);
        }
        return "Envie apenas arquivo .xls ou .xlsx.";
    }

    function mensagemSelecionarArquivoParaContinuar() {
        if (typeof uploadText.selectFileToContinue === "function") {
            return uploadText.selectFileToContinue(arquivoXlsOuXlsxLabel);
        }
        return "Selecione um arquivo .xls ou .xlsx para continuar.";
    }

    function validarExtensao(file) {
        if (!file) return false;
        var nome = file.name.toLowerCase();
        return nome.endsWith(".xls") || nome.endsWith(".xlsx");
    }

    function atualizarNomeArquivo() {
        if (!input.files || !input.files.length) {
            fileStatus.textContent = "";
            return;
        }
        var selectedFilePrefix = commonText.selectedFilePrefix || "Arquivo selecionado: ";
        fileStatus.textContent = selectedFilePrefix + input.files[0].name;
    }

    function iniciarCarregamento() {
        form.classList.add("is-loading");
        if (loadingStatus) loadingStatus.classList.add("is-visible");
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
        if (!validarExtensao(files[0])) {
            window.alert(mensagemApenasArquivoPermitido());
            return;
        }
        input.files = files;
        atualizarNomeArquivo();
    });

    input.addEventListener("change", function () {
        if (!input.files || !input.files.length) return;
        if (!validarExtensao(input.files[0])) {
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
        if (!validarExtensao(input.files[0])) {
            event.preventDefault();
            window.alert(mensagemApenasArquivoPermitido());
            return;
        }
        if (temArquivoExistente && confirmInput.value !== "1" && !confirmarSubstituicaoSeNecessario()) {
            event.preventDefault();
            return;
        }
        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("controle-margem-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var dashboardPedido = document.getElementById("dashboard-pedido");
    var dashboardCmv = document.getElementById("dashboard-cmv");
    var dashboardLucro = document.getElementById("dashboard-lucro");
    var dashboardMargem = document.getElementById("dashboard-margem");

    function fmtMoeda(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            style: "currency",
            currency: "BRL",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function fmtPercentualRatio(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            style: "percent",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function normalizarSituacao(valor) {
        return String(valor || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();
    }

    function obterCorSituacao(situacao) {
        var situacaoNormalizada = normalizarSituacao(situacao);
        if (situacaoNormalizada === "roxo") return "#8e24aa";
        if (situacaoNormalizada === "vermelho") return "#e74c3c";
        if (situacaoNormalizada === "amarelo") return "#f4b000";
        if (situacaoNormalizada === "verde") return "#2f9e44";
        return "";
    }

    function formatTextoOuVazio(valor) {
        var texto = String(valor || "").trim();
        return texto || "(Vazio)";
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
            || section.querySelector("#controle-margem-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#controle-margem-filtros-coluna-direita");

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
            left.id = "controle-margem-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "controle-margem-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    function criarDefinicoesFiltros() {
        return [
            {
                key: "situacao",
                label: "Situacao",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.situacao : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "descricao_perfil",
                label: "Descricao (Perfil)",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.descricao_perfil : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "apelido_vendedor",
                label: "Vendedor",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.apelido_vendedor : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "nome_empresa",
                label: "Nome Empresa",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.nome_empresa : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "tipo_venda",
                label: "Tipo de Venda",
                singleSelect: true,
                extractValue: function (rowData) { return rowData ? rowData.tipo_venda : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
        ];
    }

    function atualizarDashboard() {
        var linhas = tabela.getData("active");
        if (!linhas || !linhas.length) {
            linhas = tabela.getData() || [];
        }

        var pedido = 0;
        var cmv = 0;
        linhas.forEach(function (item) {
            pedido += Number(item.vlr_nota || 0);
            cmv += Number(item.custo_total_produto || 0);
        });
        var lucro = pedido - cmv;
        var margem = pedido === 0 ? 0 : (lucro / pedido);

        if (dashboardPedido) dashboardPedido.textContent = fmtMoeda(pedido);
        if (dashboardCmv) dashboardCmv.textContent = fmtMoeda(cmv);
        if (dashboardLucro) dashboardLucro.textContent = fmtMoeda(lucro);
        if (dashboardMargem) dashboardMargem.textContent = fmtPercentualRatio(margem);
    }

    var colunas = [
            {title: "Número Único", field: "nro_unico", sorter: "number", headerFilter: "input"},
            {title: "Nome da Empresa", field: "nome_empresa", headerFilter: "input"},
            {title: "Código e Nome do Parceiro", field: "cod_nome_parceiro", headerFilter: "input"},
            {title: "Descrição do Perfil", field: "descricao_perfil", headerFilter: "input"},
            {title: "Apelido (Vendedor)", field: "apelido_vendedor", headerFilter: "input"},
            {title: "Gerente", field: "gerente", headerFilter: "input"},
            {title: "Data de Negociação", field: "dt_neg", headerFilter: "input"},
            {title: "Previsão de Entrega", field: "previsao_entrega", headerFilter: "input"},
            {title: "Tipo da Venda", field: "tipo_venda", headerFilter: "input"},
            {title: "Valor da Nota", field: "vlr_nota", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Custo Total do Produto", field: "custo_total_produto", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {
                title: "Margem Bruta",
                field: "margem_bruta",
                hozAlign: "right",
                formatter: function (cell) {
                    var valorFormatado = fmtPercentualRatio(cell.getValue());
                    var rowData = cell.getRow() ? cell.getRow().getData() : null;
                    var cor = obterCorSituacao(rowData ? rowData.situacao : "");
                    if (!cor) return valorFormatado;
                    var textoEscuro = normalizarSituacao(rowData && rowData.situacao) === "amarelo";
                    var corTexto = textoEscuro ? "#1f2937" : "#ffffff";
                    return '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:' + cor + ";color:" + corTexto + ';font-weight:600;">' + valorFormatado + "</span>";
                },
            },
            {title: "Lucro Bruto", field: "lucro_bruto", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Valor por Tonelada (Frete SAFIA)", field: "valor_tonelada_frete_safia", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Peso Bruto (KG)", field: "peso_bruto", hozAlign: "right"},
            {title: "Custo por KG", field: "custo_por_kg", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Vendas", field: "vendas", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Produção", field: "producao", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Operador Logística", field: "operador_logistica", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Frete Distribuição", field: "frete_distribuicao", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Total Logística", field: "total_logistica", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Administração", field: "administracao", hozAlign: "right", headerFilter: "input", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Financeiro", field: "financeiro", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Total de Setores", field: "total_setores", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Valor Líquido", field: "valor_liquido", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Margem Líquida", field: "margem_liquida", hozAlign: "right", formatter: function (cell) { return fmtPercentualRatio(cell.getValue()); }},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data);

    var tabela = window.TabulatorDefaults.create("#controle-margem-tabulator", {
        data: data,
        columns: colunas,
    });

    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros) {
        secFiltros.dataset.moduleFiltersAuto = "off";
    }

    var filtrosExternos = null;
    if (window.ModuleFilterCore && secFiltros) {
        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholderFiltros = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholderFiltros) placeholderFiltros.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (filtroColumns && filtroColumns.left && filtroColumns.right) {
            filtrosExternos = window.ModuleFilterCore.create({
                data: data,
                definitions: criarDefinicoesFiltros(),
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
        }
    }

    function limparTodosFiltros() {
        if (filtrosExternos && typeof filtrosExternos.clearAllFilters === "function") {
            filtrosExternos.clearAllFilters();
        }
        if (typeof tabela.clearHeaderFilter === "function") {
            tabela.clearHeaderFilter();
        }
        if (typeof tabela.refreshFilter === "function") {
            tabela.refreshFilter();
        }
    }

    var limparFiltrosSidebarBtn = secFiltros ? secFiltros.querySelector(".module-filters-clear-all") : null;
    var limparFiltrosToolbarBtn = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
    if (limparFiltrosSidebarBtn) {
        limparFiltrosSidebarBtn.addEventListener("click", limparTodosFiltros);
    }
    if (limparFiltrosToolbarBtn) {
        limparFiltrosToolbarBtn.addEventListener("click", limparTodosFiltros);
    }

    tabela.on("tableBuilt", atualizarDashboard);
    tabela.on("dataFiltered", atualizarDashboard);
    tabela.on("renderComplete", atualizarDashboard);
    setTimeout(atualizarDashboard, 0);
})();


