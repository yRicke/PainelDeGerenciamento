(function () {
    var dataElement = document.getElementById("transportadoras-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                nome: row.nome || "",
                codigo_transportadora: row.codigo_transportadora || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir transportadora?",
    });

    var tabela = window.TabulatorDefaults.create("#transportadoras-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Nome", field: "nome", editor: "input"},
            {title: "CÃ³digo", field: "codigo_transportadora", editor: "input"},
            colunaAcoes,
        ],
    });

})();
