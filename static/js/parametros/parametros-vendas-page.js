(function () {
    var dataElement = document.getElementById("parametros-vendas-tabulator-data");
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

    function formatPercentFromRatio(value) {
        var percentual = parseRatioInput(value) * 100;
        if (!Number.isFinite(percentual)) percentual = 0;
        return percentual.toLocaleString("pt-BR", {
            minimumFractionDigits: 4,
            maximumFractionDigits: 4,
        }) + "%";
    }

    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        submitPost: submitPost,
        getSaveUrl: function (row) {
            return row.acao_url;
        },
        getDeleteUrl: function (row) {
            return row.acao_url;
        },
        getSavePayload: function (row) {
            return {
                acao: "editar",
                item_id: row.id,
                parametro: toFieldValue(row.parametro),
                criterio: toFieldValue(row.criterio),
                remuneracao_percentual: toFieldValue(row.remuneracao_percentual),
            };
        },
        getDeletePayload: function (row) {
            return {
                acao: "excluir",
                item_id: row.id,
            };
        },
        deleteConfirm: "Excluir parametro?",
    });

    var tabela = window.TabulatorDefaults.create("#parametros-vendas-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Parametro", field: "parametro", editor: "input"},
            {title: "Criterio", field: "criterio", editor: "input"},
            {
                title: "Remuneracao (%)",
                field: "remuneracao_percentual",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatPercentFromRatio(cell.getValue());
                },
            },
            colunaAcoes,
        ],
    });

})();
