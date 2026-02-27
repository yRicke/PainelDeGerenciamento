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
        {title: "ID", field: "id", width: 90, hozAlign: "center"},
        {title: "Status", field: "status", width: 110, hozAlign: "center"},
        {title: "Intervalo", field: "intervalo", width: 130},
        {title: "Dias diferenca", field: "dias_diferenca", width: 130, hozAlign: "center"},
        {title: "Data negociacao", field: "data_negociacao"},
        {title: "Data vencimento", field: "data_vencimento"},
        {title: "Data arquivo", field: "data_arquivo"},
        {title: "Ano negociacao", field: "ano_negociacao", hozAlign: "center"},
        {title: "Mes negociacao", field: "mes_negociacao", hozAlign: "center"},
        {title: "Nome fantasia empresa", field: "nome_fantasia_empresa"},
        {title: "Numero nota", field: "numero_nota"},
        {title: "Vendedor", field: "vendedor"},
        {title: "Valor desdobramento", field: "valor_desdobramento"},
        {title: "Valor liquido", field: "valor_liquido"},
        {title: "Titulo cod", field: "titulo_codigo"},
        {title: "Titulo descricao", field: "titulo_descricao"},
        {title: "Natureza cod", field: "natureza_codigo"},
        {title: "Natureza descricao", field: "natureza_descricao"},
        {title: "Centro resultado", field: "centro_resultado_descricao"},
        {title: "Parceiro cod", field: "parceiro_codigo"},
        {title: "Parceiro nome", field: "parceiro_nome"},
        {title: "Operacao cod", field: "operacao_codigo"},
        {title: "Operacao descricao", field: "operacao_descricao"},
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

