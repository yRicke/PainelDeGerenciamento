(function () {
    var dataElement = document.getElementById("empresas-titulares-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;

    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                codigo: row.codigo || "",
                nome: row.nome || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir empresa titular?",
    });

    window.TabulatorDefaults.create("#empresas-titulares-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Codigo", field: "codigo", editor: "input"},
            {title: "Nome", field: "nome", editor: "input"},
            colunaAcoes,
        ],
    });
})();
