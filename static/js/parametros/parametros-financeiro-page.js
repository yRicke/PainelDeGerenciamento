(function () {
    var dataElement = document.getElementById("parametros-financeiro-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;

    function toFieldValue(value) {
        if (value === null || value === undefined) return "";
        return String(value);
    }

    function parseRatioInput(texto) {
        var t = String(texto || "").trim();
        if (!t) return 0;
        var temPercentual = t.indexOf("%") >= 0;
        t = t.replace(/%/g, "").replace(/\s/g, "");
        if (t.indexOf(",") >= 0) {
            t = t.replace(/\./g, "").replace(",", ".");
        } else if ((t.match(/\./g) || []).length > 1 && t.toLowerCase().indexOf("e") < 0) {
            t = t.replace(/\./g, "");
        }
        var numero = Number(t);
        if (!Number.isFinite(numero)) return 0;
        if (temPercentual) return numero / 100;
        if (Math.abs(numero) > 1) return numero / 100;
        return numero;
    }

    function formatPercentFromRatio(ratio) {
        var percentual = parseRatioInput(ratio) * 100;
        if (!Number.isFinite(percentual)) percentual = 0;
        return percentual.toLocaleString("pt-BR", {
            minimumFractionDigits: 4,
            maximumFractionDigits: 4,
        }) + "%";
    }

    function atualizarCampoRemuneracao(taxaInput, remuneracaoInput) {
        if (!taxaInput || !remuneracaoInput) return;
        var taxa = parseRatioInput(taxaInput.value);
        remuneracaoInput.value = formatPercentFromRatio(taxa / 30);
    }

    var taxaNovo = document.getElementById("taxa-ao-mes-novo");
    var remuneracaoNovo = document.getElementById("remuneracao-novo");
    if (taxaNovo && remuneracaoNovo) {
        atualizarCampoRemuneracao(taxaNovo, remuneracaoNovo);
        taxaNovo.addEventListener("input", function () {
            atualizarCampoRemuneracao(taxaNovo, remuneracaoNovo);
        });
    }

    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        submitPost: submitPost,
        field: "editar_url",
        getSavePayload: function (row) {
            return {
                parametro: toFieldValue(row.parametro),
                taxa_ao_mes: toFieldValue(row.taxa_ao_mes),
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir parametro?",
    });

    var tabela = window.TabulatorDefaults.create("#parametros-financeiro-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Parametro", field: "parametro", editor: "input"},
            {
                title: "Taxa ao Mes (%)",
                field: "taxa_ao_mes",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatPercentFromRatio(cell.getValue());
                },
                cellEdited: function (cell) {
                    var row = cell.getRow();
                    var rowData = row.getData();
                    var taxa = parseRatioInput(rowData.taxa_ao_mes);
                    row.update({remuneracao_percentual: taxa / 30});
                },
            },
            {
                title: "Remuneracao (%)",
                field: "remuneracao_percentual",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatPercentFromRatio(cell.getValue());
                },
            },
            colunaAcoes,
        ],
    });

})();
