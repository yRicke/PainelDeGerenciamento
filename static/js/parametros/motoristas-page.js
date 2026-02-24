(function () {
    var dataElement = document.getElementById("motoristas-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroNome = document.getElementById("filtro-motorista-nome");
    var filtroCodigo = document.getElementById("filtro-motorista-codigo");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-motoristas");

    var tabela = window.TabulatorDefaults.create("#motoristas-tabulator", {
        data: data,
        layout: "fitDataStretch",
        pagination: true,
        paginationSize: 100,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Nome", field: "nome", editor: "input"},
            {title: "Código", field: "codigo_motorista", editor: "input"},
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
                            codigo_motorista: row.codigo_motorista || "",
                        });
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("btn-danger")) {
                        submitPost(row.excluir_url, {}, "Excluir motorista?");
                    }
                },
            },
        ],
    });

    function aplicarFiltros() {
        var nome = (filtroNome.value || "").toLowerCase().trim();
        var codigo = (filtroCodigo.value || "").toLowerCase().trim();
        tabela.setFilter(function (dataRow) {
            if (nome && !(dataRow.nome || "").toLowerCase().includes(nome)) return false;
            if (codigo && !(dataRow.codigo_motorista || "").toLowerCase().includes(codigo)) return false;
            return true;
        });
    }

    [filtroNome, filtroCodigo].forEach(function (element) {
        element.addEventListener("input", aplicarFiltros);
    });

    limparFiltrosBtn.addEventListener("click", function () {
        filtroNome.value = "";
        filtroCodigo.value = "";
        tabela.clearFilter(true);
    });
})();
