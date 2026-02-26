(function () {
    var dataElement = document.getElementById("parceiros-tabulator-data");
    var cidadesElement = document.getElementById("parceiros-cidades-data");
    if (!dataElement || !cidadesElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var cidades = JSON.parse(cidadesElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroNome = document.getElementById("filtro-parceiro-nome");
    var filtroCodigo = document.getElementById("filtro-parceiro-codigo");
    var filtroCidade = document.getElementById("filtro-parceiro-cidade");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-parceiros");
    var cidadesValues = {"": "Sem cidade"};

    cidades.forEach(function (cidade) {
        cidadesValues[String(cidade.id)] = (cidade.nome || "") + " (" + (cidade.codigo || "") + ")";
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
                    values: cidadesValues,
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
                    row.cidade_nome = cidadeSelecionada ? cidadeSelecionada.nome : "";
                    cell.getRow().update({cidade_nome: row.cidade_nome});
                },
            },
            {
                title: "Ações",
                field: "editar_url",
                hozAlign: "center",
                formatter: function () {
                    return '<button class="btn-primary" type="button">Salvar</button> <button class="btn-danger" type="button">Excluir</button>';
                },
                cellClick: function (e, cell) {
                    var row = cell.getRow().getData();
                    if (e.target && e.target.classList && e.target.classList.contains("btn-primary")) {
                        submitPost(row.editar_url, {
                            nome: row.nome || "",
                            codigo: row.codigo || "",
                            cidade_id: row.cidade_id || "",
                        });
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("btn-danger")) {
                        submitPost(row.excluir_url, {}, "Excluir parceiro?");
                    }
                },
            },
        ],
    });

    function aplicarFiltros() {
        var nome = (filtroNome.value || "").toLowerCase().trim();
        var codigo = (filtroCodigo.value || "").toLowerCase().trim();
        var cidade = (filtroCidade.value || "").toLowerCase().trim();
        tabela.setFilter(function (dataRow) {
            if (nome && !(dataRow.nome || "").toLowerCase().includes(nome)) return false;
            if (codigo && !(dataRow.codigo || "").toLowerCase().includes(codigo)) return false;
            if (cidade && !(dataRow.cidade_nome || "").toLowerCase().includes(cidade)) return false;
            return true;
        });
    }

    [filtroNome, filtroCodigo, filtroCidade].forEach(function (element) {
        element.addEventListener("input", aplicarFiltros);
    });

    limparFiltrosBtn.addEventListener("click", function () {
        filtroNome.value = "";
        filtroCodigo.value = "";
        filtroCidade.value = "";
        tabela.clearFilter(true);
    });
})();



