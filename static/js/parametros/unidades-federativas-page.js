(function () {
    var dataElement = document.getElementById("unidades-federativas-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                codigo: row.codigo || "",
                sigla: row.sigla || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir unidade federativa?",
    });

    var tabela = window.TabulatorDefaults.create("#unidades-federativas-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Codigo", field: "codigo", editor: "input"},
            {title: "Sigla", field: "sigla", editor: "input"},
            colunaAcoes,
        ],
    });

})();


