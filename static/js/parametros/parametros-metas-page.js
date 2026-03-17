(function () {
    var dataElement = document.getElementById("parametros-metas-tabulator-data");
    var descricoesElement = document.getElementById("parametros-metas-descricoes-data");
    if (!dataElement || !descricoesElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var descricoes = JSON.parse(descricoesElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var descricaoValues = {};

    descricoes.forEach(function (item) {
        descricaoValues[String(item.id)] = item.descricao || "";
    });

    function toFieldValue(value) {
        if (value === null || value === undefined) return "";
        return String(value);
    }

    function parseRatioInput(texto) {
        var t = String(texto || "").trim();
        if (!t) return null;
        var temPercentual = t.indexOf("%") >= 0;
        t = t.replace(/%/g, "").replace(/\s/g, "");
        if (t.indexOf(",") >= 0) {
            t = t.replace(/\./g, "").replace(",", ".");
        } else if ((t.match(/\./g) || []).length > 1 && t.toLowerCase().indexOf("e") < 0) {
            t = t.replace(/\./g, "");
        }
        var numero = Number(t);
        if (!Number.isFinite(numero)) return null;
        if (temPercentual) return numero / 100;
        if (Math.abs(numero) > 1) return numero / 100;
        if (Math.abs(numero) >= 0.1) return numero / 100;
        return numero;
    }

    function parseDecimalInput(texto) {
        var t = String(texto || "").trim();
        if (!t) return null;
        t = t.replace(/R\$/g, "").replace(/\s/g, "");
        if (t.indexOf(",") >= 0) {
            t = t.replace(/\./g, "").replace(",", ".");
        } else if ((t.match(/\./g) || []).length > 1 && t.toLowerCase().indexOf("e") < 0) {
            t = t.replace(/\./g, "");
        }
        var numero = Number(t);
        if (!Number.isFinite(numero)) return null;
        return numero;
    }

    function formatPercentFromRatio(value) {
        var ratio = parseRatioInput(value);
        if (ratio === null) return "";
        var percentual = ratio * 100;
        if (!Number.isFinite(percentual)) return "";
        return percentual.toLocaleString("pt-BR", {
            minimumFractionDigits: 4,
            maximumFractionDigits: 4,
        }) + "%";
    }

    function formatMoney(value) {
        var numero = parseDecimalInput(value);
        if (numero === null) return "";
        return "R$ " + numero.toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                descricao_perfil_id: row.descricao_perfil_id || "",
                meta_acabado_percentual: toFieldValue(row.meta_acabado_percentual),
                valor_meta_pd_acabado: toFieldValue(row.valor_meta_pd_acabado),
                meta_mt_prima_percentual: toFieldValue(row.meta_mt_prima_percentual),
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir parametro de metas?",
    });

    window.TabulatorDefaults.create("#parametros-metas-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {
                title: "Descricao Perfil",
                field: "descricao_perfil_id",
                editor: "list",
                editorParams: {
                    values: descricaoValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    return row.descricao_perfil_descricao || "";
                },
                cellEdited: function (cell) {
                    var row = cell.getRow().getData();
                    var id = String(row.descricao_perfil_id || "");
                    row.descricao_perfil_descricao = descricaoValues[id] || "";
                    cell.getRow().update({descricao_perfil_descricao: row.descricao_perfil_descricao});
                },
            },
            {
                title: "% Meta Acabado",
                field: "meta_acabado_percentual",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatPercentFromRatio(cell.getValue());
                },
            },
            {
                title: "Valor Meta Pd. Acabado (R$)",
                field: "valor_meta_pd_acabado",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
                },
            },
            {
                title: "% Meta Mt. Prima",
                field: "meta_mt_prima_percentual",
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

