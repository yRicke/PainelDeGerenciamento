(function () {
    var dataElement = document.getElementById("bancos-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;

    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                nome: row.nome || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir banco?",
    });

    window.TabulatorDefaults.create("#bancos-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Nome", field: "nome", editor: "input"},
            colunaAcoes,
        ],
    });
})();
