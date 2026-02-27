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
    var receitaEl = document.getElementById("dfc-kpi-receita");
    var despesaEl = document.getElementById("dfc-kpi-despesa");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});

    function normalizarTipo(item) {
        var valor = Number(item.valor_liquido || 0);
        if (valor > 0) return "receita";
        if (valor < 0) return "despesa";

        var tipo = (item.operacao_descricao || "").toLowerCase();
        if (tipo.includes("receita")) return "receita";
        if (tipo.includes("despesa")) return "despesa";
        return "";
    }

    var totalReceita = 0;
    var totalDespesa = 0;
    data.forEach(function (item) {
        var valor = Number(item.valor_liquido || 0);
        var tipo = normalizarTipo(item);
        if (tipo === "receita") totalReceita += valor;
        if (tipo === "despesa") totalDespesa += valor;
    });

    if (receitaEl) receitaEl.textContent = totalReceita ? formatadorMoeda.format(totalReceita) : "R$ -";
    if (despesaEl) despesaEl.textContent = totalDespesa ? formatadorMoeda.format(Math.abs(totalDespesa)) : "R$ -";
})();




