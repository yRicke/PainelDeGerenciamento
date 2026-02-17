(function () {
    var formCriacao = document.getElementById("criar-carga-form");
    if (!formCriacao) return;

    var dataChegada = document.getElementById("data-chegada-criar");
    var dataFinalizacao = document.getElementById("data-finalizacao-criar");
    if (!dataChegada || !dataFinalizacao) return;

    function atualizarBloqueioFinalizacao() {
        var temChegada = Boolean(dataChegada.value);
        dataFinalizacao.disabled = !temChegada;
        dataFinalizacao.min = dataChegada.value || "";
        if (!temChegada) {
            dataFinalizacao.value = "";
        }
    }

    dataChegada.addEventListener("change", atualizarBloqueioFinalizacao);
    dataChegada.addEventListener("input", atualizarBloqueioFinalizacao);
    atualizarBloqueioFinalizacao();
})();

(function () {
    var form = document.getElementById("upload-cargas-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-cargas");
    var input = document.getElementById("arquivo-cargas-input");
    var statusArquivo = document.getElementById("nome-arquivo-cargas-selecionado");
    var loadingStatus = document.getElementById("cargas-loading-status");
    var confirmarInput = document.getElementById("confirmar-substituicao-input");
    var temArquivoExistente = form.getAttribute("data-tem-arquivo-existente") === "1";

    function iniciarCarregamento() {
        form.classList.add("is-loading");
        loadingStatus.classList.add("is-visible");
    }

    function obterArquivoXls(files) {
        if (!files || !files.length) return null;
        var arquivo = files[0];
        if (!arquivo || !arquivo.name || !arquivo.name.toLowerCase().endsWith(".xls")) {
            return null;
        }
        return arquivo;
    }

    function atualizarStatus(arquivo) {
        if (!arquivo) {
            statusArquivo.textContent = "";
            return;
        }
        statusArquivo.textContent = "Arquivo selecionado: " + arquivo.name;
    }

    function selecionarArquivo(files) {
        var arquivo = obterArquivoXls(files);
        if (!arquivo) {
            window.alert("Selecione um arquivo .xls valido.");
            input.value = "";
            atualizarStatus(null);
            return;
        }
        atualizarStatus(arquivo);
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
        input.files = event.dataTransfer.files;
        selecionarArquivo(input.files);
    });

    input.addEventListener("change", function () {
        selecionarArquivo(input.files);
    });

    form.addEventListener("submit", function (event) {
        var arquivo = obterArquivoXls(input.files);
        if (!arquivo) {
            event.preventDefault();
            window.alert("Selecione um arquivo .xls para continuar.");
            return;
        }

        if (temArquivoExistente) {
            var confirmou = window.confirm(
                "Ja existe arquivo na pasta. Deseja substituir e mover o arquivo antigo para subscritos?"
            );
            if (!confirmou) {
                event.preventDefault();
                return;
            }
            confirmarInput.value = "1";
        }

        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("cargas-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var filtroSituacao = document.getElementById("filtro-situacao");
    var filtroVerificacao = document.getElementById("filtro-verificacao");
    var filtroCritica = document.getElementById("filtro-critica");
    var filtroEmpresa = document.getElementById("filtro-empresa");

    var kpiTotal = document.getElementById("kpi-cargas-em-aberto");
    var kpiNoPrazo = document.getElementById("kpi-cargas-no-prazo");
    var kpiForaPrazo = document.getElementById("kpi-cargas-fora-prazo");

    var data = JSON.parse(dataElement.textContent || "[]");
    var dadosOriginais = Array.isArray(data) ? data.slice() : [];

    function paraTexto(valor) {
        return String(valor || "").toLowerCase();
    }

    function atualizarDashboard(dadosFiltrados) {
        if (!kpiTotal || !kpiNoPrazo || !kpiForaPrazo) return;

        var total = dadosFiltrados.length;
        var foraPrazo = dadosFiltrados.filter(function (item) {
            return Boolean(item.verificacao);
        }).length;

        kpiTotal.textContent = String(total);
        kpiForaPrazo.textContent = String(foraPrazo);
        kpiNoPrazo.textContent = String(total - foraPrazo);
    }

    var table = new Tabulator("#cargas-tabulator", {
        data: dadosOriginais,
        layout: "fitDataStretch",
        movableColumns: true,
        pagination: "local",
        paginationSize: 100,
        locale: true,
        langs: {
            "pt-br": {
                pagination: {
                    first: "Primeira",
                    first_title: "Primeira pagina",
                    last: "Ultima",
                    last_title: "Ultima pagina",
                    prev: "Anterior",
                    prev_title: "Pagina anterior",
                    next: "Proxima",
                    next_title: "Proxima pagina"
                }
            }
        },
        columns: [
            { title: "Ordem Carga", field: "ordem_de_carga_codigo", headerFilter: "input" },
            { title: "Situacao", field: "situacao", headerFilter: "input" },
            { title: "Empresa", field: "nome_fantasia_empresa", headerFilter: "input" },
            { title: "Motorista", field: "nome_motorista", headerFilter: "input" },
            { title: "Regiao", field: "regiao_nome", headerFilter: "input" },
            { title: "Inicio", field: "data_inicio", hozAlign: "center" },
            { title: "Prev. Saida", field: "data_prevista_saida", hozAlign: "center" },
            { title: "Chegada", field: "data_chegada", hozAlign: "center" },
            { title: "Finalizacao", field: "data_finalizacao", hozAlign: "center" },
            { title: "Prazo Max. (dias)", field: "prazo_maximo_dias", hozAlign: "right" },
            { title: "Idade (dias)", field: "idade_dias", hozAlign: "right" },
            {
                title: "Verificacao",
                field: "verificacao",
                hozAlign: "center",
                formatter: function (cell) {
                    return cell.getValue() ? "Verificar" : "Ok";
                }
            },
            { title: "Critica", field: "critica", hozAlign: "center" },
            {
                title: "Acoes",
                field: "editar_url",
                formatter: function (cell) {
                    var url = cell.getValue();
                    return '<a class="btn-primary" href="' + url + '">Editar</a>';
                },
                hozAlign: "center"
            }
        ]
    });

    function aplicarFiltrosExibicao() {
        var situacaoSelecionada = filtroSituacao ? paraTexto(filtroSituacao.value) : "";
        var verificacaoSelecionada = filtroVerificacao ? paraTexto(filtroVerificacao.value) : "";
        var criticaSelecionada = filtroCritica ? paraTexto(filtroCritica.value) : "";
        var empresaDigitada = filtroEmpresa ? paraTexto(filtroEmpresa.value).trim() : "";

        table.setFilter(function (dataItem) {
            var situacaoAtual = paraTexto(dataItem.situacao);
            var empresaAtual = paraTexto(dataItem.nome_fantasia_empresa);
            var criticaAtual = Number(dataItem.critica || 0);
            var verificacaoAtual = Boolean(dataItem.verificacao);

            if (situacaoSelecionada && situacaoAtual !== situacaoSelecionada) return false;
            if (empresaDigitada && empresaAtual.indexOf(empresaDigitada) === -1) return false;

            if (verificacaoSelecionada === "ok" && verificacaoAtual) return false;
            if (verificacaoSelecionada === "verificar" && !verificacaoAtual) return false;

            if (criticaSelecionada === "positiva" && criticaAtual <= 0) return false;
            if (criticaSelecionada === "zero" && criticaAtual !== 0) return false;
            if (criticaSelecionada === "negativa" && criticaAtual >= 0) return false;

            return true;
        });
    }

    function registrarFiltro(el) {
        if (!el) return;
        el.addEventListener("input", aplicarFiltrosExibicao);
        el.addEventListener("change", aplicarFiltrosExibicao);
    }

    registrarFiltro(filtroSituacao);
    registrarFiltro(filtroVerificacao);
    registrarFiltro(filtroCritica);
    registrarFiltro(filtroEmpresa);

    table.on("dataFiltered", function (_filters, rows) {
        var dadosFiltrados = rows.map(function (row) {
            return row.getData();
        });
        atualizarDashboard(dadosFiltrados);
    });

    table.setLocale("pt-br");
    atualizarDashboard(dadosOriginais);
})();

