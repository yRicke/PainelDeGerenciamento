(function () {
    var dataElement = document.getElementById("parametros-logistica-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;

    function toFieldValue(value) {
        if (value === null || value === undefined) return "";
        return String(value);
    }

    function parseDecimalInput(texto) {
        var t = String(texto || "").trim();
        if (!t) return 0;
        t = t.replace(/R\$/g, "").replace(/\s/g, "");
        if (t.indexOf(",") >= 0) {
            t = t.replace(/\./g, "").replace(",", ".");
        } else if ((t.match(/\./g) || []).length > 1 && t.toLowerCase().indexOf("e") < 0) {
            t = t.replace(/\./g, "");
        }
        var numero = Number(t);
        if (!Number.isFinite(numero)) return 0;
        return numero;
    }

    function formatMoney(value) {
        var numero = parseDecimalInput(value);
        if (!Number.isFinite(numero)) numero = 0;
        return "R$ " + numero.toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 4,
        });
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
                remuneracao_rs: toFieldValue(row.remuneracao_rs),
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

    var tabela = window.TabulatorDefaults.create("#parametros-logistica-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Parametro", field: "parametro", editor: "input"},
            {title: "Criterio", field: "criterio", editor: "input"},
            {
                title: "Remuneracao (R$)",
                field: "remuneracao_rs",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
                },
            },
            colunaAcoes,
        ],
    });

})();
