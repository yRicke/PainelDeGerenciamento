(function () {
    var dataElement = document.getElementById("rotas-tabulator-data");
    var ufsElement = document.getElementById("rotas-ufs-data");
    if (!dataElement || !ufsElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var ufs = JSON.parse(ufsElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroCodigo = document.getElementById("filtro-rota-codigo");
    var filtroNome = document.getElementById("filtro-rota-nome");
    var filtroUf = document.getElementById("filtro-rota-uf");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-rotas");
    var ufValues = {"": "Sem UF"};

    ufs.forEach(function (uf) {
        ufValues[String(uf.id)] = (uf.sigla || "") + " (" + (uf.codigo || "") + ")";
    });

    var tabela = window.TabulatorDefaults.create("#rotas-tabulator", {
        data: data,
        layout: "fitDataStretch",
        pagination: true,
        paginationSize: 100,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Código da Rota", field: "codigo_rota", editor: "input"},
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
                            codigo_rota: row.codigo_rota || "",
                            nome: row.nome || "",
                            uf_id: row.uf_id || "",
                        });
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("btn-danger")) {
                        submitPost(row.excluir_url, {}, "Excluir rota?");
                    }
                },
            },
        ],
    });

    function aplicarFiltros() {
        var codigo = (filtroCodigo.value || "").toLowerCase().trim();
        var nome = (filtroNome.value || "").toLowerCase().trim();
        var uf = (filtroUf.value || "").toLowerCase().trim();
        tabela.setFilter(function (dataRow) {
            if (codigo && !(dataRow.codigo_rota || "").toLowerCase().includes(codigo)) return false;
            if (nome && !(dataRow.nome || "").toLowerCase().includes(nome)) return false;
            if (uf && !(dataRow.uf_sigla || "").toLowerCase().includes(uf)) return false;
            return true;
        });
    }

    [filtroCodigo, filtroNome, filtroUf].forEach(function (element) {
        element.addEventListener("input", aplicarFiltros);
    });

    limparFiltrosBtn.addEventListener("click", function () {
        filtroCodigo.value = "";
        filtroNome.value = "";
        filtroUf.value = "";
        tabela.clearFilter(true);
    });
})();
