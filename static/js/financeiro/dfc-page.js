(function () {
    var form = document.getElementById("upload-dfc-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-dfc");
    var input = document.getElementById("arquivo-dfc-input");
    var confirmInput = document.getElementById("confirmar-substituicao-input");
    var fileStatus = document.getElementById("nome-arquivo-dfc-selecionado");
    var temArquivoExistente = form.dataset.temArquivoExistente === "1";

    function atualizarNomeArquivo() {
        if (!input.files || !input.files.length) {
            fileStatus.textContent = "";
            return;
        }
        fileStatus.textContent = "Arquivo selecionado: " + input.files[0].name;
    }

    function validarExtensaoXls(file) {
        return file && file.name.toLowerCase().endsWith(".xls");
    }

    function confirmarSubstituicaoSeNecessario() {
        if (!temArquivoExistente) {
            confirmInput.value = "0";
            return true;
        }
        if (!window.confirm("Ja existe um arquivo de DFC. Deseja substituir o arquivo atual?")) return false;
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
            window.alert("Envie apenas arquivo .xls.");
            return;
        }
        input.files = files;
        atualizarNomeArquivo();
    });

    input.addEventListener("change", function () {
        if (!input.files || !input.files.length) return;
        if (!validarExtensaoXls(input.files[0])) {
            window.alert("Envie apenas arquivo .xls.");
            input.value = "";
        }
        atualizarNomeArquivo();
    });

    form.addEventListener("submit", function (event) {
        if (!input.files || !input.files.length) {
            event.preventDefault();
            window.alert("Selecione um arquivo .xls para continuar.");
            return;
        }
        if (!validarExtensaoXls(input.files[0])) {
            event.preventDefault();
            window.alert("Envie apenas arquivo .xls.");
            return;
        }
        if (temArquivoExistente && confirmInput.value !== "1" && !confirmarSubstituicaoSeNecessario()) {
            event.preventDefault();
        }
    });
})();

(function () {
    var dataElement = document.getElementById("dfc-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var limparBtn = document.getElementById("limpar-filtros-dfc");
    var receitaDespesaSelect = document.getElementById("filtro-dfc-receita-despesa");
    var anoSelect = document.getElementById("filtro-dfc-ano");
    var mesSelect = document.getElementById("filtro-dfc-mes");
    var tituloSelect = document.getElementById("filtro-dfc-titulo");
    var centroResultadoSelect = document.getElementById("filtro-dfc-centro-resultado");
    var tipoOperacaoSelect = document.getElementById("filtro-dfc-tipo-operacao");
    var tipoMovimentoSelect = document.getElementById("filtro-dfc-tipo-movimento");
    var receitaEl = document.getElementById("dfc-kpi-receita");
    var despesaEl = document.getElementById("dfc-kpi-despesa");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});

    function preencherSelect(select, valores, mesLabel) {
        valores.forEach(function (valor) {
            var option = document.createElement("option");
            option.value = String(valor);
            option.textContent = mesLabel ? mesLabel[valor] || String(valor) : String(valor);
            select.appendChild(option);
        });
    }

    function valoresUnicos(campo) {
        return Array.from(new Set(data.map(function (item) { return item[campo]; }).filter(Boolean)));
    }

    preencherSelect(receitaDespesaSelect, ["Receita", "Despesa"]);
    preencherSelect(anoSelect, valoresUnicos("ano_negociacao").sort(function (a, b) { return b - a; }));
    preencherSelect(mesSelect, valoresUnicos("mes_negociacao").sort(function (a, b) { return a - b; }), {
        1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
    });
    preencherSelect(tituloSelect, valoresUnicos("titulo_codigo").sort());
    preencherSelect(centroResultadoSelect, valoresUnicos("centro_resultado_descricao").sort());
    preencherSelect(tipoOperacaoSelect, valoresUnicos("operacao_codigo").sort());
    preencherSelect(tipoMovimentoSelect, valoresUnicos("tipo_movimento").sort());

    var tabela = window.TabulatorDefaults.create("#dfc-tabulator", {
        data: data,
        layout: "fitDataTable",
        pagination: true,
        paginationSize: 100,
        columns: [
            {title: "ID", field: "id", width: 70, hozAlign: "center", headerFilter: "input"},
            {
                title: "Data negociacao",
                field: "data_negociacao",
                headerFilter: "input",
                sorter: function (a, b, aRow, bRow) {
                    var aIso = aRow.getData().data_negociacao_iso || "";
                    var bIso = bRow.getData().data_negociacao_iso || "";
                    return aIso.localeCompare(bIso);
                },
            },
            {
                title: "Data vencimento",
                field: "data_vencimento",
                headerFilter: "input",
                sorter: function (a, b, aRow, bRow) {
                    var aIso = aRow.getData().data_vencimento_iso || "";
                    var bIso = bRow.getData().data_vencimento_iso || "";
                    return aIso.localeCompare(bIso);
                },
            },
            {
                title: "Valor liquido",
                field: "valor_liquido",
                hozAlign: "right",
                headerFilter: "input",
                formatter: "money",
                formatterParams: {
                    decimal: ",",
                    thousand: ".",
                    symbol: "R$ ",
                    symbolAfter: false,
                    precision: 2,
                },
            },
            {title: "Numero nota", field: "numero_nota", headerFilter: "input"},
            {title: "Titulo codigo", field: "titulo_codigo", headerFilter: "input"},
            {title: "Titulo descricao", field: "titulo_descricao", headerFilter: "input"},
            {title: "Centro resultado", field: "centro_resultado_descricao", headerFilter: "input"},
            {title: "Tipo operacao", field: "operacao_codigo", headerFilter: "input"},
            {title: "Natureza codigo", field: "natureza_codigo", headerFilter: "input"},
            {title: "Natureza descricao", field: "natureza_descricao", headerFilter: "input"},
            {title: "Historico", field: "historico", headerFilter: "input"},
            {title: "Parceiro codigo", field: "parceiro_codigo", headerFilter: "input"},
            {title: "Parceiro", field: "parceiro_nome", headerFilter: "input"},
            {title: "Receita/Despesa", field: "operacao_descricao", headerFilter: "input"},
            {title: "Tipo movimento", field: "tipo_movimento", headerFilter: "input"},
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

    function atualizarDashboard() {
        var linhas = tabela.getData("active");
        if (!linhas) linhas = [];

        var totalReceita = 0;
        var totalDespesa = 0;

        linhas.forEach(function (item) {
            var valor = Number(item.valor_liquido || 0);
            var tipo = normalizarTipo(item);
            if (tipo === "receita") totalReceita += valor;
            if (tipo === "despesa") totalDespesa += valor;
        });

        receitaEl.textContent = totalReceita ? formatadorMoeda.format(totalReceita) : "R$ -";
        despesaEl.textContent = totalDespesa ? formatadorMoeda.format(Math.abs(totalDespesa)) : "R$ -";
    }

    function normalizarTipo(item) {
        var valor = Number(item.valor_liquido || 0);
        if (valor > 0) return "receita";
        if (valor < 0) return "despesa";

        var tipo = (item.operacao_descricao || "").toLowerCase();
        if (tipo.includes("receita")) return "receita";
        if (tipo.includes("despesa")) return "despesa";
        return "";
    }

    function aplicarFiltros() {
        var receitaDespesa = receitaDespesaSelect.value || "";
        var ano = anoSelect.value || "";
        var mes = mesSelect.value || "";
        var titulo = tituloSelect.value || "";
        var centroResultado = centroResultadoSelect.value || "";
        var tipoOperacao = tipoOperacaoSelect.value || "";
        var tipoMovimento = tipoMovimentoSelect.value || "";

        tabela.setFilter(function (item) {
            if (receitaDespesa) {
                var tipoSelecionado = receitaDespesa.toLowerCase().includes("receita") ? "receita" : "despesa";
                if (normalizarTipo(item) !== tipoSelecionado) return false;
            }
            if (ano && String(item.ano_negociacao) !== String(ano)) return false;
            if (mes && String(item.mes_negociacao) !== String(mes)) return false;
            if (titulo && item.titulo_codigo !== titulo) return false;
            if (centroResultado && item.centro_resultado_descricao !== centroResultado) return false;
            if (tipoOperacao && item.operacao_codigo !== tipoOperacao) return false;
            if (tipoMovimento && item.tipo_movimento !== tipoMovimento) return false;
            return true;
        });

        atualizarDashboard();
    }

    [
        receitaDespesaSelect,
        anoSelect,
        mesSelect,
        tituloSelect,
        centroResultadoSelect,
        tipoOperacaoSelect,
        tipoMovimentoSelect,
    ].forEach(function (element) {
        if (!element) return;
        element.addEventListener("change", aplicarFiltros);
    });

    limparBtn.addEventListener("click", function () {
        receitaDespesaSelect.value = "";
        anoSelect.value = "";
        mesSelect.value = "";
        tituloSelect.value = "";
        centroResultadoSelect.value = "";
        tipoOperacaoSelect.value = "";
        tipoMovimentoSelect.value = "";
        tabela.clearFilter(true);
        tabela.clearHeaderFilter();
        atualizarDashboard();
    });

    tabela.on("tableBuilt", atualizarDashboard);
    tabela.on("dataFiltered", atualizarDashboard);
    tabela.on("renderComplete", atualizarDashboard);
    setTimeout(atualizarDashboard, 0);
})();


