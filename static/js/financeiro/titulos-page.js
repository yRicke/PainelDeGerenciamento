(function () {
    var dataElement = document.getElementById("titulos-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                tipo_titulo_codigo: row.tipo_titulo_codigo || "",
                descricao: row.descricao || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir titulo?",
    });

    var tabela = window.TabulatorDefaults.create("#titulos-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Código", field: "tipo_titulo_codigo", editor: "input"},
            {title: "Descrição", field: "descricao", editor: "input"},
            colunaAcoes,
        ],
    });

})();
