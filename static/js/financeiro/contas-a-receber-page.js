(function () {
    var form = document.getElementById("upload-contas-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-contas");
    var input = document.getElementById("arquivo-contas-input");
    var fileStatus = document.getElementById("nome-arquivo-contas-selecionado");

    function coletarArquivosXls(files) {
        if (!files || !files.length) return [];
        return Array.from(files).filter(function (file) {
            return file && file.name.toLowerCase().endsWith(".xls");
        });
    }

    function atualizarStatus(filesXls) {
        if (!filesXls.length) {
            fileStatus.textContent = "";
            return;
        }
        fileStatus.textContent = filesXls.length + " arquivo(s) .xls selecionado(s).";
    }

    function atribuirArquivosNoInput(filesXls) {
        var dt = new DataTransfer();
        filesXls.forEach(function (file) { dt.items.add(file); });
        input.files = dt.files;
    }

    function selecionarArquivos(files) {
        var arquivosXls = coletarArquivosXls(files);
        if (!arquivosXls.length) {
            window.alert("Nenhum arquivo .xls encontrado.");
            input.value = "";
            atualizarStatus([]);
            return;
        }
        atribuirArquivosNoInput(arquivosXls);
        atualizarStatus(arquivosXls);
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
        selecionarArquivos(event.dataTransfer.files);
    });

    input.addEventListener("change", function () {
        selecionarArquivos(input.files);
    });

    form.addEventListener("submit", function (event) {
        var arquivosXls = coletarArquivosXls(input.files);
        if (!arquivosXls.length) {
            event.preventDefault();
            window.alert("Selecione uma pasta com arquivos .xls para continuar.");
        }
    });
})();

(function () {
    var dataElement = document.getElementById("contas-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-contas");
    var statusContainer = document.getElementById("filtro-contas-status");
    var intervaloContainer = document.getElementById("filtro-contas-intervalo");
    var dataVencimentoContainer = document.getElementById("filtro-contas-data-vencimento");
    var dataArquivoContainer = document.getElementById("filtro-contas-data-arquivo");
    var dataArquivoInicialInput = document.getElementById("filtro-contas-data-arquivo-inicial");
    var dataArquivoFinalInput = document.getElementById("filtro-contas-data-arquivo-final");
    var selecionarMaisRecenteBtn = document.getElementById("filtro-contas-data-arquivo-mais-recente");
    var tituloDescricaoContainer = document.getElementById("filtro-contas-titulo-descricao");
    var nomeFantasiaContainer = document.getElementById("filtro-contas-nome-fantasia");
    var naturezaDescricaoContainer = document.getElementById("filtro-contas-natureza-descricao");
    var kpiQuantidadeEl = document.getElementById("contas-kpi-quantidade");
    var kpiFaturadoEl = document.getElementById("contas-kpi-faturado");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});

    function compararDataIso(aRow, bRow, campoIso) {
        var aIso = aRow.getData()[campoIso] || "";
        var bIso = bRow.getData()[campoIso] || "";
        return aIso.localeCompare(bIso);
    }

    var tabela = window.TabulatorDefaults.create("#contas-tabulator", {
        data: data,
        layout: "fitDataTable",
        pagination: true,
        paginationSize: 100,
        columns: [
            {
                title: "Dt. Negociacao",
                field: "data_negociacao",
                headerFilter: "input",
                sorter: function (_a, _b, aRow, bRow) {
                    return compararDataIso(aRow, bRow, "data_negociacao_iso");
                },
            },
            {
                title: "Dt. Vencimento",
                field: "data_vencimento",
                headerFilter: "input",
                sorter: function (_a, _b, aRow, bRow) {
                    return compararDataIso(aRow, bRow, "data_vencimento_iso");
                },
            },
            {
                title: "Data Arquivo",
                field: "data_arquivo",
                headerFilter: "input",
                sorter: function (_a, _b, aRow, bRow) {
                    return compararDataIso(aRow, bRow, "data_arquivo_iso");
                },
            },
            {title: "Nome Fantasia (Empresa)", field: "nome_fantasia_empresa", headerFilter: "input"},
            {title: "Nome Parceiro (Parceiro)", field: "parceiro_nome", headerFilter: "input"},
            {title: "Nro Nota", field: "numero_nota", headerFilter: "input"},
            {
                title: "Vlr do Desdobramento",
                field: "valor_desdobramento",
                hozAlign: "right",
                formatter: "money",
                formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2},
            },
            {
                title: "Valor Liquido",
                field: "valor_liquido",
                hozAlign: "right",
                formatter: "money",
                formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2},
            },
            {title: "Descricao (Tipo de Titulo)", field: "titulo_descricao", headerFilter: "input"},
            {title: "Descricao (Natureza)", field: "natureza_descricao", headerFilter: "input"},
            {title: "Descricao (Centro de Resultado)", field: "centro_resultado_descricao", headerFilter: "input"},
            {title: "Vendedor", field: "vendedor", headerFilter: "input"},
            {title: "Receita/Despesa", field: "operacao_descricao", headerFilter: "input"},
            {title: "Status", field: "status", headerFilter: "input"},
            {title: "Dias Diferenca", field: "dias_diferenca", hozAlign: "center", headerFilter: "input"},
            {title: "Intervalo", field: "intervalo", headerFilter: "input"},
            {
                title: "Acoes",
                field: "editar_url",
                formatter: function (cell) {
                    var url = cell.getValue();
                    return '<a class="btn-primary" href="' + url + '">Editar</a>';
                },
                hozAlign: "center",
            },
        ],
    });

    function normalizarTexto(valor, vazioLabel) {
        var texto = (valor || "").toString().trim();
        return texto || vazioLabel;
    }

    function valoresUnicosOrdenados(campo, vazioLabel) {
        var setValores = new Set();
        data.forEach(function (item) {
            setValores.add(normalizarTexto(item[campo], vazioLabel));
        });
        return Array.from(setValores).sort(function (a, b) {
            return a.localeCompare(b, "pt-BR");
        });
    }

    function parseDataBrParaOrdenacao(valor) {
        if (!valor || !valor.includes("/")) return "";
        var partes = valor.split("/");
        if (partes.length !== 3) return "";
        return [partes[2], partes[1], partes[0]].join("-");
    }

    function valoresUnicosDataOrdenados(campo, vazioLabel) {
        var setValores = new Set();
        data.forEach(function (item) {
            setValores.add(normalizarTexto(item[campo], vazioLabel));
        });
        return Array.from(setValores).sort(function (a, b) {
            if (a === vazioLabel) return 1;
            if (b === vazioLabel) return -1;
            var isoA = parseDataBrParaOrdenacao(a);
            var isoB = parseDataBrParaOrdenacao(b);
            return isoB.localeCompare(isoA);
        });
    }

    function criarEstadoSelecao() {
        return {
            status: new Set(),
            intervalo: new Set(),
            data_vencimento: new Set(),
            data_arquivo: new Set(),
            titulo_descricao: new Set(),
            nome_fantasia_empresa: new Set(),
            natureza_descricao: new Set(),
        };
    }

    var filtrosSelecionados = criarEstadoSelecao();

    function criarBotaoFiltro(valor, onToggle) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "contas-filtro-btn";
        btn.textContent = valor;
        btn.addEventListener("click", function () {
            btn.classList.toggle("is-active");
            onToggle(btn.classList.contains("is-active"), valor);
            aplicarFiltros();
        });
        return btn;
    }

    function montarGrupoFiltros(container, valores, chaveEstado) {
        if (!container) return;
        container.innerHTML = "";
        valores.forEach(function (valor) {
            var btn = criarBotaoFiltro(valor, function (ativo, valorToggle) {
                if (ativo) filtrosSelecionados[chaveEstado].add(valorToggle);
                else filtrosSelecionados[chaveEstado].delete(valorToggle);
            });
            container.appendChild(btn);
        });
    }

    function normalizarTipoOperacao(item) {
        var tipo = (item.operacao_descricao || "").toLowerCase();
        if (tipo.includes("receita")) return "receita";
        if (tipo.includes("despesa")) return "despesa";
        return "";
    }

    function calcularValorFaturado(item) {
        var valor = Number(item.valor_liquido || 0);
        var tipo = normalizarTipoOperacao(item);
        if (tipo === "receita") return valor;
        if (tipo === "despesa") return -Math.abs(valor);
        return valor;
    }

    function atualizarDashboard() {
        if (!kpiQuantidadeEl && !kpiFaturadoEl) return;

        var linhas = tabela.getData("active");
        if (!linhas) linhas = [];

        var totalFaturado = linhas.reduce(function (acc, item) {
            return acc + calcularValorFaturado(item);
        }, 0);

        if (kpiQuantidadeEl) kpiQuantidadeEl.textContent = String(linhas.length);
        if (kpiFaturadoEl) kpiFaturadoEl.textContent = formatadorMoeda.format(totalFaturado);
    }

    function aplicarFiltros() {
        var dataArquivoInicial = dataArquivoInicialInput ? dataArquivoInicialInput.value : "";
        var dataArquivoFinal = dataArquivoFinalInput ? dataArquivoFinalInput.value : "";

        tabela.setFilter(function (item) {
            var statusValor = normalizarTexto(item.status, "<SEM STATUS>");
            var intervaloValor = normalizarTexto(item.intervalo, "<SEM INTERVALO>");
            var vencimentoValor = normalizarTexto(item.data_vencimento, "<SEM DATA VENCIMENTO>");
            var dataArquivoValor = normalizarTexto(item.data_arquivo, "<SEM DATA ARQUIVO>");
            var tituloValor = normalizarTexto(item.titulo_descricao, "<SEM TIPO DE TITULO>");
            var nomeFantasiaValor = normalizarTexto(item.nome_fantasia_empresa, "<SEM NOME FANTASIA>");
            var naturezaValor = normalizarTexto(item.natureza_descricao, "<SEM NATUREZA>");
            var dataArquivoIso = item.data_arquivo_iso || "";

            if (dataArquivoInicial && (!dataArquivoIso || dataArquivoIso < dataArquivoInicial)) return false;
            if (dataArquivoFinal && (!dataArquivoIso || dataArquivoIso > dataArquivoFinal)) return false;

            if (filtrosSelecionados.status.size && !filtrosSelecionados.status.has(statusValor)) return false;
            if (filtrosSelecionados.intervalo.size && !filtrosSelecionados.intervalo.has(intervaloValor)) return false;
            if (filtrosSelecionados.data_vencimento.size && !filtrosSelecionados.data_vencimento.has(vencimentoValor)) return false;
            if (filtrosSelecionados.data_arquivo.size && !filtrosSelecionados.data_arquivo.has(dataArquivoValor)) return false;
            if (filtrosSelecionados.titulo_descricao.size && !filtrosSelecionados.titulo_descricao.has(tituloValor)) return false;
            if (filtrosSelecionados.nome_fantasia_empresa.size && !filtrosSelecionados.nome_fantasia_empresa.has(nomeFantasiaValor)) return false;
            if (filtrosSelecionados.natureza_descricao.size && !filtrosSelecionados.natureza_descricao.has(naturezaValor)) return false;
            return true;
        });

        atualizarDashboard();
    }

    function limparFiltrosExternos() {
        filtrosSelecionados = criarEstadoSelecao();
        if (dataArquivoInicialInput) dataArquivoInicialInput.value = "";
        if (dataArquivoFinalInput) dataArquivoFinalInput.value = "";
        document.querySelectorAll(".contas-filtro-btn.is-active").forEach(function (btn) {
            btn.classList.remove("is-active");
        });
        tabela.clearFilter(true);
        tabela.clearHeaderFilter();
        atualizarDashboard();
    }

    montarGrupoFiltros(statusContainer, valoresUnicosOrdenados("status", "<SEM STATUS>"), "status");
    montarGrupoFiltros(intervaloContainer, valoresUnicosOrdenados("intervalo", "<SEM INTERVALO>"), "intervalo");
    montarGrupoFiltros(dataVencimentoContainer, valoresUnicosDataOrdenados("data_vencimento", "<SEM DATA VENCIMENTO>"), "data_vencimento");
    montarGrupoFiltros(dataArquivoContainer, valoresUnicosDataOrdenados("data_arquivo", "<SEM DATA ARQUIVO>"), "data_arquivo");
    montarGrupoFiltros(tituloDescricaoContainer, valoresUnicosOrdenados("titulo_descricao", "<SEM TIPO DE TITULO>"), "titulo_descricao");
    montarGrupoFiltros(nomeFantasiaContainer, valoresUnicosOrdenados("nome_fantasia_empresa", "<SEM NOME FANTASIA>"), "nome_fantasia_empresa");
    montarGrupoFiltros(naturezaDescricaoContainer, valoresUnicosOrdenados("natureza_descricao", "<SEM NATUREZA>"), "natureza_descricao");

    [dataArquivoInicialInput, dataArquivoFinalInput].forEach(function (input) {
        if (!input) return;
        input.addEventListener("change", aplicarFiltros);
    });

    if (selecionarMaisRecenteBtn) {
        selecionarMaisRecenteBtn.addEventListener("click", function () {
            var linhasComData = data.filter(function (item) { return Boolean(item.data_arquivo_iso); });
            if (!linhasComData.length) return;
            var maisRecenteIso = linhasComData
                .map(function (item) { return item.data_arquivo_iso; })
                .sort(function (a, b) { return b.localeCompare(a); })[0];
            var labelMaisRecente = linhasComData.find(function (item) {
                return item.data_arquivo_iso === maisRecenteIso;
            }).data_arquivo;
            filtrosSelecionados.data_arquivo = new Set([labelMaisRecente]);
            document.querySelectorAll("#filtro-contas-data-arquivo .contas-filtro-btn").forEach(function (btn) {
                btn.classList.toggle("is-active", btn.textContent === labelMaisRecente);
            });
            aplicarFiltros();
        });
    }

    if (limparFiltrosBtn) {
        limparFiltrosBtn.addEventListener("click", limparFiltrosExternos);
    }

    tabela.on("tableBuilt", atualizarDashboard);
    tabela.on("dataFiltered", atualizarDashboard);
    tabela.on("renderComplete", atualizarDashboard);
    setTimeout(atualizarDashboard, 0);
})();

