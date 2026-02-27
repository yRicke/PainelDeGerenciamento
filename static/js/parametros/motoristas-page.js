(function () {
    var dataElement = document.getElementById("motoristas-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                nome: row.nome || "",
                codigo_motorista: row.codigo_motorista || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir motorista?",
    });

    var tabela = window.TabulatorDefaults.create("#motoristas-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Nome", field: "nome", editor: "input"},
            {title: "CÃ³digo", field: "codigo_motorista", editor: "input"},
            colunaAcoes,
        ],
    });

})();
