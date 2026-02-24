(function () {
    var dataElement = document.getElementById("transportadoras-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroNome = document.getElementById("filtro-transportadora-nome");
    var filtroCodigo = document.getElementById("filtro-transportadora-codigo");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-transportadoras");

    var tabela = window.TabulatorDefaults.create("#transportadoras-tabulator", {
        data: data,
        layout: "fitDataStretch",
        pagination: true,
        paginationSize: 100,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Nome", field: "nome", editor: "input"},
            {title: "Código", field: "codigo_transportadora", editor: "input"},
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
                            codigo_transportadora: row.codigo_transportadora || "",
                        });
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("btn-danger")) {
                        submitPost(row.excluir_url, {}, "Excluir transportadora?");
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
            if (codigo && !(dataRow.codigo_transportadora || "").toLowerCase().includes(codigo)) return false;
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
