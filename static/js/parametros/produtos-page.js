(function () {
    var dataElement = document.getElementById("produtos-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroCodigo = document.getElementById("filtro-produto-codigo");
    var filtroDescricao = document.getElementById("filtro-produto-descricao");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-produtos");

    var tabela = window.TabulatorDefaults.create("#produtos-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Codigo", field: "codigo_produto"},
            {title: "Status", field: "status"},
            {title: "Descricao", field: "descricao_produto"},
            {title: "KG", field: "kg", hozAlign: "right"},
            {title: "Rem. por Fardo", field: "remuneracao_por_fardo", hozAlign: "right"},
            {title: "PPM", field: "ppm", hozAlign: "right"},
            {title: "Peso (KG)", field: "peso_kg", hozAlign: "right"},
            {title: "Pacote/Fardo", field: "pacote_por_fardo", hozAlign: "right"},
            {title: "Turno", field: "turno", hozAlign: "right"},
            {title: "Horas", field: "horas", hozAlign: "right"},
            {title: "Setup", field: "setup", hozAlign: "right"},
            {title: "Horas Uteis", field: "horas_uteis", hozAlign: "right"},
            {title: "Empacotadeiras", field: "empacotadeiras", hozAlign: "right"},
            {title: "Prod. Dia (FD)", field: "producao_por_dia_fd", hozAlign: "right"},
            {title: "Est. Min. Pacote", field: "estoque_minimo_pacote", hozAlign: "right"},
            {
                title: "Acoes",
                hozAlign: "center",
                formatter: function () {
                    return '<a class="btn-primary" href="#">Editar</a> <button class="btn-danger" type="button">Excluir</button>';
                },
                cellClick: function (e, cell) {
                    var row = cell.getRow().getData();
                    if (e.target && e.target.classList && e.target.classList.contains("btn-primary")) {
                        e.preventDefault();
                        window.location.href = row.editar_url;
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("btn-danger")) {
                        submitPost(row.excluir_url, {}, "Excluir produto?");
                    }
                },
            },
        ],
    });

    function aplicarFiltros() {
        var codigo = (filtroCodigo.value || "").toLowerCase().trim();
        var descricao = (filtroDescricao.value || "").toLowerCase().trim();
        tabela.setFilter(function (dataRow) {
            if (codigo && !(dataRow.codigo_produto || "").toLowerCase().includes(codigo)) return false;
            if (descricao && !(dataRow.descricao_produto || "").toLowerCase().includes(descricao)) return false;
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



