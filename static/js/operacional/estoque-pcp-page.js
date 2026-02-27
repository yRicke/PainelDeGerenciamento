(function () {
    function vincularParametrosProdutoNoFormulario(formulario) {
        if (!formulario) return;
        var selectProduto = formulario.querySelector('select[name="produto_id"]');
        var inputPacote = formulario.querySelector('input[name="pacote_por_fardo"]');
        var inputMinimo = formulario.querySelector('input[name="estoque_minimo"]');
        var inputFd = formulario.querySelector('input[name="producao_por_dia_fd"]');
        if (!selectProduto || !inputPacote || !inputMinimo || !inputFd) return;

        function aplicarParametrosDaOpcaoSelecionada() {
            var opcao = selectProduto.options[selectProduto.selectedIndex];
            if (!opcao || !opcao.value) {
                inputPacote.value = "0";
                inputMinimo.value = "0";
                inputFd.value = "0";
                return;
            }
            inputPacote.value = opcao.dataset.pacotePorFardo || "0";
            inputFd.value = opcao.dataset.producaoPorDiaFd || "0";
            var parametrizado = (opcao.dataset.produtoParametrizado || "0") === "1";
            inputMinimo.value = parametrizado ? (opcao.dataset.estoqueMinimo || "0") : "12000";
        }

        selectProduto.addEventListener("change", aplicarParametrosDaOpcaoSelecionada);
        aplicarParametrosDaOpcaoSelecionada();
    }

    vincularParametrosProdutoNoFormulario(document.getElementById("criar-estoque-form"));

    var form = document.getElementById("upload-estoque-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-estoque");
    var input = document.getElementById("arquivos-estoque-input");
    var fileStatus = document.getElementById("nome-arquivos-estoque-selecionado");
    var loadingStatus = document.getElementById("estoque-loading-status");
    if (!dropzone || !input || !fileStatus || !loadingStatus) return;

    function iniciarCarregamento() {
        form.classList.add("is-loading");
        loadingStatus.classList.add("is-visible");
    }

    function coletarArquivosXls(files) {
        if (!files || !files.length) return [];
        return Array.from(files).filter(function (file) {
            return file && file.name.toLowerCase().endsWith(".xls");
        });
    }

    function contarPorTipo(arquivosXls) {
        var totais = {posicao: 0, reservado: 0};
        arquivosXls.forEach(function (file) {
            var caminho = String(file.webkitRelativePath || file.name || "").toLowerCase();
            var caminhoNormalizado = caminho;
            if (typeof caminhoNormalizado.normalize === "function") {
                caminhoNormalizado = caminhoNormalizado
                    .normalize("NFD")
                    .replace(/[\u0300-\u036f]/g, "");
            }
            if (caminhoNormalizado.indexOf("posicao") >= 0) totais.posicao += 1;
            if (caminho.indexOf("reservado") >= 0) totais.reservado += 1;
        });
        return totais;
    }

    function atualizarStatus(filesXls) {
        if (!filesXls.length) {
            fileStatus.textContent = "";
            return;
        }
        var totais = contarPorTipo(filesXls);
        fileStatus.textContent = (
            filesXls.length
            + " arquivo(s) .xls selecionado(s) - posicao: "
            + totais.posicao
            + ", reservado: "
            + totais.reservado
            + "."
        );
    }

    function atribuirArquivosNoInput(filesXls) {
        var dt = new DataTransfer();
        filesXls.forEach(function (file) { dt.items.add(file); });
        input.files = dt.files;
    }

    function selecionarArquivos(files) {
        var arquivosXls = coletarArquivosXls(files);
        if (arquivosXls.length < 2) {
            window.alert("Selecione a pasta ESTOQUE com as subpastas de posicao e reservado.");
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
        if (arquivosXls.length < 2) {
            event.preventDefault();
            window.alert("Selecione a pasta ESTOQUE com arquivos .xls das duas subpastas.");
            return;
        }
        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("estoque-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var dadosOriginais = Array.isArray(data) ? data.slice() : [];
    var kpiValor = document.getElementById("kpi-estoque-valor");
    var kpiDataRecente = document.getElementById("kpi-estoque-data-recente");

    function formatMoeda(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            style: "currency",
            currency: "BRL",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function formatNumeroPtBr(valor, casasDecimais) {
        var numero = Number(valor || 0);
        if (!Number.isFinite(numero)) return "-";
        return numero.toLocaleString("pt-BR", {
            minimumFractionDigits: casasDecimais,
            maximumFractionDigits: casasDecimais,
        });
    }

    function formatDataIsoParaBr(iso) {
        if (!iso) return "-";
        var p = String(iso).split("-");
        if (p.length !== 3) return "-";
        return p[2] + "/" + p[1] + "/" + p[0];
    }

    var colunas = [
            {
                title: "Origem",
                field: "nome_origem",
                sorter: function (a, b, aRow, bRow) {
                    var aIso = (aRow.getData().nome_origem_iso || "");
                    var bIso = (bRow.getData().nome_origem_iso || "");
                    return aIso.localeCompare(bIso);
                },
            },
            {
                title: "Data de Contagem",
                field: "data_contagem",
                sorter: function (a, b, aRow, bRow) {
                    var aIso = (aRow.getData().data_contagem_iso || "");
                    var bIso = (bRow.getData().data_contagem_iso || "");
                    return aIso.localeCompare(bIso);
                },
            },
            {title: "Status", field: "status"},
            {title: "Código da Empresa", field: "codigo_empresa"},
            {title: "Código do Produto", field: "produto_codigo"},
            {title: "Descrição do Produto", field: "produto_descricao"},
            {title: "Quantidade em Estoque", field: "qtd_estoque", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Giro Mensal", field: "giro_mensal", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Lead Time de Fornecimento", field: "lead_time_fornecimento", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Código da Unidade de Volume", field: "codigo_volume"},
            {title: "Custo Total", field: "custo_total", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Reservado", field: "reservado", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Pacote por Fardo", field: "pacote_por_fardo", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "SubTotal", field: "sub_total_est_pen", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Estoque Mínimo", field: "estoque_minimo", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {
                title: "PCP",
                cssClass: "pcp-group",
                headerHozAlign: "center",
                columns: [
                    {title: "Produção por Dia (FD)", field: "producao_por_dia_fd", hozAlign: "right", cssClass: "pcp-col", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
                    {title: "Total PCP Pacote", field: "total_pcp_pacote", hozAlign: "right", cssClass: "pcp-col", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
                    {title: "Total PCP Fardo", field: "total_pcp_fardo", hozAlign: "right", cssClass: "pcp-col", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
                    {title: "Dia de Produção", field: "dia_de_producao", hozAlign: "right", cssClass: "pcp-col", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 6); }},
                    {title: "Código do Local", field: "codigo_local", cssClass: "pcp-col"},
                ],
            },
        ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, dadosOriginais);

    var tabela = window.TabulatorDefaults.create("#estoque-tabulator", {
        data: dadosOriginais,
        columns: colunas,
    });

    function atualizarDashboardComLinhas(linhas) {
        if (!kpiValor || !kpiDataRecente) return;
        var custoTotal = 0;
        var dataMaisRecente = "";

        linhas.forEach(function (item) {
            custoTotal += Number(item.custo_total || 0);
            var iso = item.data_contagem_iso || "";
            if (iso && (!dataMaisRecente || iso > dataMaisRecente)) {
                dataMaisRecente = iso;
            }
        });

        kpiValor.textContent = formatMoeda(custoTotal);
        kpiDataRecente.textContent = formatDataIsoParaBr(dataMaisRecente);
    }

    tabela.on("dataFiltered", function (_filters, rows) {
        var dadosFiltrados = rows.map(function (row) { return row.getData(); });
        atualizarDashboardComLinhas(dadosFiltrados);
    });

    tabela.setLocale("pt-br");
    atualizarDashboardComLinhas(dadosOriginais);
})();
