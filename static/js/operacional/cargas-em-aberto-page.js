(function () {
    var formCriacao = document.getElementById("criar-carga-form");
    if (!formCriacao) return;

    var dataInicio = formCriacao.querySelector('input[name="data_inicio"]');
    var dataPrevistaSaida = document.getElementById("data-prevista-saida-criar");
    var dataChegada = document.getElementById("data-chegada-criar");
    var dataFinalizacao = document.getElementById("data-finalizacao-criar");
    if (!dataInicio || !dataPrevistaSaida || !dataChegada || !dataFinalizacao) return;

    function atualizarEncadeamentoDatas() {
        var valorInicio = dataInicio.value || "";
        dataPrevistaSaida.disabled = !valorInicio;
        dataPrevistaSaida.min = valorInicio || "";
        if (!valorInicio) {
            dataPrevistaSaida.value = "";
            dataChegada.value = "";
            dataFinalizacao.value = "";
        }
        if (valorInicio && dataPrevistaSaida.value && dataPrevistaSaida.value < valorInicio) {
            dataPrevistaSaida.value = "";
            dataChegada.value = "";
            dataFinalizacao.value = "";
        }

        var valorSaida = dataPrevistaSaida.value || "";
        dataChegada.disabled = !valorSaida;
        dataChegada.min = valorSaida || "";
        if (!valorSaida) {
            dataChegada.value = "";
            dataFinalizacao.value = "";
        }
        if (valorSaida && dataChegada.value && dataChegada.value < valorSaida) {
            dataChegada.value = "";
            dataFinalizacao.value = "";
        }

        var valorChegada = dataChegada.value || "";
        dataFinalizacao.disabled = !valorChegada;
        dataFinalizacao.min = valorChegada || "";
        if (!valorChegada) {
            dataFinalizacao.value = "";
        }
        if (valorChegada && dataFinalizacao.value && dataFinalizacao.value < valorChegada) {
            dataFinalizacao.value = "";
        }
    }

    [dataInicio, dataPrevistaSaida, dataChegada, dataFinalizacao].forEach(function (input) {
        input.addEventListener("change", atualizarEncadeamentoDatas);
        input.addEventListener("input", atualizarEncadeamentoDatas);
    });
    atualizarEncadeamentoDatas();
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
            window.alert("Selecione um arquivo .xls válido.");
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
                "Já existe arquivo na pasta. Deseja substituir e mover o arquivo antigo para subscritos?"
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
    var limparFiltrosBtn = document.getElementById("limpar-filtros-cargas");

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

    var table = window.TabulatorDefaults.create("#cargas-tabulator", {
        data: dadosOriginais,
        layout: "fitDataTable",
        movableColumns: true,
        pagination: "local",
        paginationSize: 100,
        locale: true,
        langs: {
            "pt-br": {
                pagination: {
                    first: "Primeira",
                    first_title: "Primeira página",
                    last: "Última",
                    last_title: "Última página",
                    prev: "Anterior",
                    prev_title: "Página anterior",
                    next: "Próxima",
                    next_title: "Próxima página"
                }
            }
        },
        columns: [
            { title: "Ordem Carga", field: "ordem_de_carga_codigo", headerFilter: "input" },
            { title: "Situação", field: "situacao", headerFilter: "input" },
            { title: "Empresa", field: "nome_fantasia_empresa", headerFilter: "input" },
            { title: "Motorista", field: "nome_motorista", headerFilter: "input" },
            { title: "Região", field: "regiao_nome", headerFilter: "input" },
            { title: "Início", field: "data_inicio", hozAlign: "center" },
            { title: "Prev. Saída", field: "data_prevista_saida", hozAlign: "center" },
            { title: "Chegada", field: "data_chegada", hozAlign: "center" },
            { title: "Finalização", field: "data_finalizacao", hozAlign: "center" },
            { title: "Prazo Max. (dias)", field: "prazo_maximo_dias", hozAlign: "right" },
            { title: "Idade (dias)", field: "idade_dias", hozAlign: "right" },
            {
                title: "Verificação",
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

    if (limparFiltrosBtn) {
        limparFiltrosBtn.addEventListener("click", function () {
            if (filtroSituacao) filtroSituacao.value = "";
            if (filtroVerificacao) filtroVerificacao.value = "";
            if (filtroCritica) filtroCritica.value = "";
            if (filtroEmpresa) filtroEmpresa.value = "";
            table.clearFilter(true);
            table.clearHeaderFilter();
            atualizarDashboard(dadosOriginais);
        });
    }

    table.on("dataFiltered", function (_filters, rows) {
        var dadosFiltrados = rows.map(function (row) {
            return row.getData();
        });
        atualizarDashboard(dadosFiltrados);
    });

    table.setLocale("pt-br");
    atualizarDashboard(dadosOriginais);
})();


