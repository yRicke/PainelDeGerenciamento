(function () {
    var form = document.getElementById("upload-fretes-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-fretes");
    var input = document.getElementById("arquivo-fretes-input");
    var statusArquivo = document.getElementById("nome-arquivo-fretes-selecionado");
    var loadingStatus = document.getElementById("fretes-loading-status");
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
    var dataElement = document.getElementById("fretes-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var dadosOriginais = Array.isArray(data) ? data.slice() : [];
    var colunas = [
            { title: "Cidade Código", field: "cidade_codigo" },
            { title: "Cidade Nome", field: "cidade_nome" },
            { title: "UF Código", field: "unidade_federativa_codigo" },
            { title: "UF Sigla", field: "unidade_federativa_sigla" },
            { title: "Região Código", field: "regiao_codigo" },
            { title: "Região Nome", field: "regiao_nome" },
            { title: "Valor Frete Comercial", field: "valor_frete_comercial", hozAlign: "right" },
            { title: "Data/Hora Alteração", field: "data_hora_alteracao" },
            { title: "Valor Frete Mínimo", field: "valor_frete_minimo", hozAlign: "right" },
            { title: "Valor Frete Tonelada", field: "valor_frete_tonelada", hozAlign: "right" },
            { title: "Tipo Frete", field: "tipo_frete" },
            { title: "Valor Frete por KM", field: "valor_frete_por_km", hozAlign: "right" },
            { title: "Valor Taxa Entrada", field: "valor_taxa_entrada", hozAlign: "right" },
            { title: "Venda Mínima", field: "venda_minima", hozAlign: "right" },
        ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, dadosOriginais);

    var table = window.TabulatorDefaults.create("#fretes-tabulator", {
        data: dadosOriginais,
        columns: colunas
    });

    table.setLocale("pt-br");
})();



