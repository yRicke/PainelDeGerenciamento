(function () {
    var dataElement = document.getElementById("centros-resultado-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroDescricao = document.getElementById("filtro-centro-resultado-descricao");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-centros-resultado");

    var tabela = new Tabulator("#centros-resultado-tabulator", {
        data: data,
        layout: "fitDataStretch",
        pagination: true,
        paginationSize: 100,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Descricao", field: "descricao", editor: "input"},
            {
                title: "Acoes",
                hozAlign: "center",
                formatter: function () {
                    return '<button class="btn-primary" type="button">Salvar</button> <button class="btn-danger" type="button">Excluir</button>';
                },
                cellClick: function (e, cell) {
                    var row = cell.getRow().getData();
                    if (e.target && e.target.classList && e.target.classList.contains("btn-primary")) {
                        submitPost(row.editar_url, {descricao: row.descricao || ""});
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("btn-danger")) {
                        submitPost(row.excluir_url, {}, "Excluir centro resultado?");
                    }
                },
            },
        ],
    });

    function aplicarFiltros() {
        var descricao = (filtroDescricao.value || "").toLowerCase().trim();
        tabela.setFilter(function (dataRow) {
            if (descricao && !(dataRow.descricao || "").toLowerCase().includes(descricao)) return false;
            return true;
        });
    }

    filtroDescricao.addEventListener("input", aplicarFiltros);

    limparFiltrosBtn.addEventListener("click", function () {
        filtroDescricao.value = "";
        tabela.clearFilter(true);
    });
})();
