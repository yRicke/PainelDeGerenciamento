(function () {
    var dataElement = document.getElementById("parceiros-tabulator-data");
    var cidadesElement = document.getElementById("parceiros-cidades-data");
    if (!dataElement || !cidadesElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var cidades = JSON.parse(cidadesElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var cidadeValues = {"": "Sem cidade"};

    cidades.forEach(function (cidade) {
        var codigo = cidade && cidade.codigo ? String(cidade.codigo) : "";
        var nome = cidade && cidade.nome ? String(cidade.nome) : "";
        var sufixoCodigo = codigo ? " (" + codigo + ")" : "";
        cidadeValues[String(cidade.id)] = nome + sufixoCodigo;
    });

    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                nome: row.nome || "",
                codigo: row.codigo || "",
                cidade_id: row.cidade_id || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir parceiro?",
    });

    var tabela = window.TabulatorDefaults.create("#parceiros-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Nome", field: "nome", editor: "input"},
            {title: "Código", field: "codigo", editor: "input"},
            {
                title: "Cidade",
                field: "cidade_id",
                editor: "list",
                editorParams: {
                    values: cidadeValues,
                    clearable: true,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    return row.cidade_nome || "Sem cidade";
                },
                cellEdited: function (cell) {
                    var row = cell.getRow().getData();
                    var cidadeId = String(row.cidade_id || "");
                    var cidadeSelecionada = cidades.find(function (item) {
                        return String(item.id) === cidadeId;
                    });
                    row.cidade_nome = cidadeSelecionada ? (cidadeSelecionada.nome || "") : "";
                    cell.getRow().update({cidade_nome: row.cidade_nome});
                },
            },
            colunaAcoes,
        ],
    });

})();
