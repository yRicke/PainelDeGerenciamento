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

    function normalizarTipo(item) {
        var valor = Number(item.valor_liquido || 0);
        if (valor > 0) return "receita";
        if (valor < 0) return "despesa";

        var tipoMovimento = (item.tipo_movimento || "").toLowerCase();
        if (tipoMovimento.includes("receita")) return "receita";
        if (tipoMovimento.includes("despesa")) return "despesa";

        var tipo = (item.operacao_descricao || "").toLowerCase();
        if (tipo.includes("receita")) return "receita";
        if (tipo.includes("despesa")) return "despesa";
        return "";
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

    if (!tabelaTarget || !window.Tabulator || !window.TabulatorDefaults) {
        atualizarDashboard(data);
        return;
    }

    var colunas = [
        {title: "ID", field: "id", width: 90, hozAlign: "center"},
        {title: "Empresa ID", field: "empresa_id", width: 120, hozAlign: "center"},
        {title: "Empresa", field: "empresa_nome"},
        {title: "Data negociacao", field: "data_negociacao"},
        {title: "Data vencimento", field: "data_vencimento"},
        {title: "Valor liquido", field: "valor_liquido"},
        {title: "Numero nota", field: "numero_nota"},
        {title: "Titulo ID", field: "titulo_id", hozAlign: "center"},
        {title: "Titulo cod", field: "titulo_codigo"},
        {title: "Titulo descricao", field: "titulo_descricao"},
        {title: "Centro resultado ID", field: "centro_resultado_id", hozAlign: "center"},
        {title: "Centro resultado", field: "centro_resultado_descricao"},
        {title: "Natureza ID", field: "natureza_id", hozAlign: "center"},
        {title: "Natureza cod", field: "natureza_codigo"},
        {title: "Natureza descricao", field: "natureza_descricao"},
        {title: "Historico", field: "historico"},
        {title: "Parceiro ID", field: "parceiro_id", hozAlign: "center"},
        {title: "Parceiro cod", field: "parceiro_codigo"},
        {title: "Parceiro nome", field: "parceiro_nome"},
        {title: "Operacao ID", field: "operacao_id", hozAlign: "center"},
        {title: "Operacao cod", field: "operacao_codigo"},
        {title: "Operacao descricao", field: "operacao_descricao"},
        {title: "Tipo movimento", field: "tipo_movimento"},
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

    var tabela = window.TabulatorDefaults.create("#dfc-tabulator", {
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




