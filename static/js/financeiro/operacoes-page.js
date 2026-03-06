(function () {
    var dataElement = document.getElementById("operacoes-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                tipo_operacao_codigo: row.tipo_operacao_codigo || "",
                descricao_receita_despesa: row.descricao_receita_despesa || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir operacao?",
    });

    var tabela = window.TabulatorDefaults.create("#operacoes-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Codigo", field: "tipo_operacao_codigo", editor: "input"},
            {title: "Descricao Receita/Despesa", field: "descricao_receita_despesa", editor: "input"},
            colunaAcoes,
        ],
    });

})();
