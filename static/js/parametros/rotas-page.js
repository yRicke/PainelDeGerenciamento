(function () {
    var dataElement = document.getElementById("rotas-tabulator-data");
    var ufsElement = document.getElementById("rotas-ufs-data");
    if (!dataElement || !ufsElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var ufs = JSON.parse(ufsElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var ufValues = {"": "Sem UF"};

    ufs.forEach(function (uf) {
        ufValues[String(uf.id)] = (uf.sigla || "") + " (" + (uf.codigo || "") + ")";
    });

    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                codigo_rota: row.codigo_rota || "",
                nome: row.nome || "",
                uf_id: row.uf_id || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir rota?",
    });

    var tabela = window.TabulatorDefaults.create("#rotas-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "CÃ³digo da Rota", field: "codigo_rota", editor: "input"},
            {title: "Nome", field: "nome", editor: "input"},
            {
                title: "UF",
                field: "uf_id",
                editor: "list",
                editorParams: {
                    values: ufValues,
                    clearable: true,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    return row.uf_sigla || "Sem UF";
                },
                cellEdited: function (cell) {
                    var row = cell.getRow().getData();
                    var ufId = String(row.uf_id || "");
                    var ufSelecionada = ufs.find(function (item) {
                        return String(item.id) === ufId;
                    });
                    row.uf_sigla = ufSelecionada ? ufSelecionada.sigla : "";
                    cell.getRow().update({uf_sigla: row.uf_sigla});
                },
            },
            colunaAcoes,
        ],
    });

})();
