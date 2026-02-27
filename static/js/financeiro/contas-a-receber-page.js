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
    if (!dataElement) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var tabelaTarget = document.getElementById("contas-a-receber-tabulator");
    var kpiQuantidadeEl = document.getElementById("contas-kpi-quantidade");
    var kpiFaturadoEl = document.getElementById("contas-kpi-faturado");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});

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

    function atualizarDashboard(linhas) {
        var totalFaturado = (linhas || []).reduce(function (acc, item) {
            return acc + calcularValorFaturado(item);
        }, 0);
        if (kpiQuantidadeEl) kpiQuantidadeEl.textContent = String((linhas || []).length);
        if (kpiFaturadoEl) kpiFaturadoEl.textContent = formatadorMoeda.format(totalFaturado);
    }

    if (!tabelaTarget || !window.Tabulator || !window.TabulatorDefaults) {
        atualizarDashboard(data);
        return;
    }

    var colunas = [
        {title: "Data de Negociação", field: "data_negociacao"},
        {title: "Data de Vencimento", field: "data_vencimento"},
        {title: "Nome Fantasia (Empresa)", field: "nome_fantasia_empresa"},
        {title: "Nome do Parceiro", field: "parceiro_nome"},
        {title: "Número da Nota", field: "numero_nota"},
        {title: "Valor do Desdobramento", field: "valor_desdobramento"},
        {title: "Valor Líquido", field: "valor_liquido"},
        {title: "Descrição do Tipo de Título", field: "titulo_descricao"},
        {title: "Descrição da Natureza", field: "natureza_descricao"},
        {title: "Descrição do Centro de Resultado", field: "centro_resultado_descricao"},
        {title: "Vendedor", field: "vendedor"},
        {title: "Receita/Despesa", field: "operacao_descricao"},
        {title: "Status", field: "status", width: 110, hozAlign: "center"},
        {title: "Dias de Diferença", field: "dias_diferenca", width: 130, hozAlign: "center"},
        {title: "Intervalo", field: "intervalo", width: 130},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data, {
        width: 110,
        formatter: function (cell) {
            var url = cell.getValue();
            if (!url) return "";
            return '<button type="button" class="btn-primary js-editar-conta">Editar</button>';
        },
        cellClick: function (e, cell) {
            var row = cell.getRow().getData();
            var target = e.target && e.target.closest ? e.target.closest(".js-editar-conta") : null;
            if (!target || !row.editar_url) return;
            window.location.href = row.editar_url;
        },
    });

    var tabela = window.TabulatorDefaults.create("#contas-a-receber-tabulator", {
        data: data,
        columns: colunas,
        freezeUX: {
            enabled: true,
        },
    });

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

