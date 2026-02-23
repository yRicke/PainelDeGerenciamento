(function () {
    var dataElement = document.getElementById("unidades-federativas-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroCodigo = document.getElementById("filtro-uf-codigo");
    var filtroSigla = document.getElementById("filtro-uf-sigla");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-ufs");

    var tabela = window.TabulatorDefaults.create("#unidades-federativas-tabulator", {
        data: data,
        layout: "fitDataStretch",
        pagination: true,
        paginationSize: 100,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Codigo", field: "codigo", editor: "input"},
            {title: "Sigla", field: "sigla", editor: "input"},
            {
                title: "Acoes",
                hozAlign: "center",
                formatter: function () {
                    return '<button class="btn-primary" type="button">Salvar</button> <button class="btn-danger" type="button">Excluir</button>';
                },
                cellClick: function (e, cell) {
                    var row = cell.getRow().getData();
                    if (e.target && e.target.classList && e.target.classList.contains("btn-primary")) {
                        submitPost(row.editar_url, {
                            codigo: row.codigo || "",
                            sigla: row.sigla || "",
                        });
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("btn-danger")) {
                        submitPost(row.excluir_url, {}, "Excluir unidade federativa?");
                    }
                },
            },
        ],
    });

    function aplicarFiltros() {
        var codigo = (filtroCodigo.value || "").toLowerCase().trim();
        var sigla = (filtroSigla.value || "").toLowerCase().trim();
        tabela.setFilter(function (dataRow) {
            if (codigo && !(dataRow.codigo || "").toLowerCase().includes(codigo)) return false;
            if (sigla && !(dataRow.sigla || "").toLowerCase().includes(sigla)) return false;
            return true;
        });
    }

    [filtroCodigo, filtroSigla].forEach(function (el) {
        el.addEventListener("input", aplicarFiltros);
    });

    limparFiltrosBtn.addEventListener("click", function () {
        filtroCodigo.value = "";
        filtroSigla.value = "";
        tabela.clearFilter(true);
    });
})();

