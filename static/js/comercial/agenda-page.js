(function () {
    var dataElement = document.getElementById("agenda-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroNumeroUnico = document.getElementById("filtro-agenda-numero-unico");
    var filtroMotorista = document.getElementById("filtro-agenda-motorista");
    var filtroTransportadora = document.getElementById("filtro-agenda-transportadora");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-agenda");

    var tabela = window.TabulatorDefaults.create("#agenda-tabulator", {
        data: data,
        layout: "fitDataTable",
        pagination: true,
        paginationSize: 100,
        columns: [
            {title: "Data Registro", field: "data_registro"},
            {title: "Número Único", field: "numero_unico"},
            {title: "Previsão de Carregamento", field: "previsao_carregamento"},
            {title: "Motorista", field: "motorista_nome"},
            {title: "Transportadora", field: "transportadora_nome"},
            {
                title: "Ações",
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
                        submitPost(row.excluir_url, {}, "Excluir agenda?");
                    }
                },
            },
        ],
    });

    function aplicarFiltros() {
        var numeroUnico = (filtroNumeroUnico.value || "").toLowerCase().trim();
        var motorista = (filtroMotorista.value || "").toLowerCase().trim();
        var transportadora = (filtroTransportadora.value || "").toLowerCase().trim();
        tabela.setFilter(function (dataRow) {
            if (numeroUnico && !(dataRow.numero_unico || "").toLowerCase().includes(numeroUnico)) return false;
            if (motorista && !(dataRow.motorista_nome || "").toLowerCase().includes(motorista)) return false;
            if (transportadora && !(dataRow.transportadora_nome || "").toLowerCase().includes(transportadora)) return false;
            return true;
        });
    }

    [filtroNumeroUnico, filtroMotorista, filtroTransportadora].forEach(function (el) {
        el.addEventListener("input", aplicarFiltros);
    });

    limparFiltrosBtn.addEventListener("click", function () {
        filtroNumeroUnico.value = "";
        filtroMotorista.value = "";
        filtroTransportadora.value = "";
        tabela.clearFilter(true);
    });
})();
