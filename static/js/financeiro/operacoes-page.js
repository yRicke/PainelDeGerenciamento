(function () {
    var dataElement = document.getElementById("operacoes-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroCodigo = document.getElementById("filtro-operacao-codigo");
    var filtroDescricao = document.getElementById("filtro-operacao-descricao");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-operacoes");

    var tabela = new Tabulator("#operacoes-tabulator", {
        data: data,
        layout: "fitDataStretch",
        pagination: true,
        paginationSize: 100,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Codigo", field: "tipo_operacao_codigo", editor: "input"},
            {title: "Descricao Receita/Despesa", field: "descricao_receita_despesa", editor: "input"},
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
                            tipo_operacao_codigo: row.tipo_operacao_codigo || "",
                            descricao_receita_despesa: row.descricao_receita_despesa || "",
                        });
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("btn-danger")) {
                        submitPost(row.excluir_url, {}, "Excluir operacao?");
                    }
                },
            },
        ],
    });

    function aplicarFiltros() {
        var codigo = (filtroCodigo.value || "").toLowerCase().trim();
        var descricao = (filtroDescricao.value || "").toLowerCase().trim();
        tabela.setFilter(function (dataRow) {
            if (codigo && !(dataRow.tipo_operacao_codigo || "").toLowerCase().includes(codigo)) return false;
            if (descricao && !(dataRow.descricao_receita_despesa || "").toLowerCase().includes(descricao)) return false;
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

