(function () {
    var dataElement = document.getElementById("titulos-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroCodigo = document.getElementById("filtro-titulo-codigo");
    var filtroDescricao = document.getElementById("filtro-titulo-descricao");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-titulos");

    var tabela = window.TabulatorDefaults.create("#titulos-tabulator", {
        data: data,
        layout: "fitDataStretch",
        pagination: true,
        paginationSize: 100,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Codigo", field: "tipo_titulo_codigo", editor: "input"},
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
                        submitPost(row.editar_url, {tipo_titulo_codigo: row.tipo_titulo_codigo || "", descricao: row.descricao || ""});
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("btn-danger")) {
                        submitPost(row.excluir_url, {}, "Excluir titulo?");
                    }
                },
            },
        ],
    });

    function aplicarFiltros() {
        var codigo = (filtroCodigo.value || "").toLowerCase().trim();
        var descricao = (filtroDescricao.value || "").toLowerCase().trim();
        tabela.setFilter(function (dataRow) {
            if (codigo && !(dataRow.tipo_titulo_codigo || "").toLowerCase().includes(codigo)) return false;
            if (descricao && !(dataRow.descricao || "").toLowerCase().includes(descricao)) return false;
            return true;
        });
    }

    [filtroCodigo, filtroDescricao].forEach(function (el) {
        el.addEventListener("input", aplicarFiltros);
    });

    limparFiltrosBtn.addEventListener("click", function () {
        filtroCodigo.value = "";
        filtroDescricao.value = "";
        tabela.clearFilter(true);
    });
})();


