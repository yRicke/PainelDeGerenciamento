(function () {
    var dataElement = document.getElementById("atividades-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var codigoInput = document.getElementById("filtro-codigo");
    var gestorSelect = document.getElementById("filtro-gestor");
    var responsavelSelect = document.getElementById("filtro-responsavel");
    var indicadorSelect = document.getElementById("filtro-indicador");
    var limparBtn = document.getElementById("limpar-filtros-tabulator");

    function preencherSelect(select, valores) {
        valores.forEach(function (valor) {
            var option = document.createElement("option");
            option.value = valor;
            option.textContent = valor;
            select.appendChild(option);
        });
    }

    var gestores = [...new Set(data.map(function (item) { return item.gestor; }).filter(Boolean))].sort();
    var responsaveis = [...new Set(data.map(function (item) { return item.responsavel; }).filter(Boolean))].sort();
    var indicadores = [...new Set(data.map(function (item) { return item.indicador; }).filter(Boolean))].sort();

    preencherSelect(gestorSelect, gestores);
    preencherSelect(responsavelSelect, responsaveis);
    preencherSelect(indicadorSelect, indicadores);

    var tabela = new Tabulator("#atividades-tabulator", {
        data: data,
        layout: "fitDataStretch",
        pagination: true,
        paginationSize: 10,
        columns: [
            {title: "ID", field: "id", width: 70, hozAlign: "center"},
            {title: "Projeto", field: "projeto"},
            {title: "Codigo", field: "codigo_projeto"},
            {title: "Gestor", field: "gestor"},
            {title: "Responsavel", field: "responsavel"},
            {title: "Interlocutor", field: "interlocutor"},
            {title: "Prazo (semana)", field: "semana_de_prazo", hozAlign: "center"},
            {title: "Prev. Inicio", field: "data_previsao_inicio"},
            {title: "Prev. Termino", field: "data_previsao_termino"},
            {title: "Finalizada", field: "data_finalizada"},
            {title: "Indicador", field: "indicador"},
            {title: "Historico", field: "historico"},
            {title: "Tarefa", field: "tarefa"},
            {title: "Progresso (%)", field: "progresso", hozAlign: "center"},
            {
                title: "Acoes",
                field: "editar_url",
                formatter: function (cell) {
                    var url = cell.getValue();
                    return '<a class="btn-primary" href="' + url + '">Editar</a>';
                },
                hozAlign: "center",
            },
        ],
    });

    function aplicarFiltros() {
        var codigo = (codigoInput.value || "").toLowerCase().trim();
        var gestor = gestorSelect.value || "";
        var responsavel = responsavelSelect.value || "";
        var indicador = indicadorSelect.value || "";

        tabela.setFilter(function (dataRow) {
            if (codigo && !(dataRow.codigo_projeto || "").toLowerCase().includes(codigo)) return false;
            if (gestor && dataRow.gestor !== gestor) return false;
            if (responsavel && dataRow.responsavel !== responsavel) return false;
            if (indicador && dataRow.indicador !== indicador) return false;
            return true;
        });
    }

    [codigoInput, gestorSelect, responsavelSelect, indicadorSelect].forEach(function (el) {
        el.addEventListener("input", aplicarFiltros);
        el.addEventListener("change", aplicarFiltros);
    });

    limparBtn.addEventListener("click", function () {
        codigoInput.value = "";
        gestorSelect.value = "";
        responsavelSelect.value = "";
        indicadorSelect.value = "";
        tabela.clearFilter(true);
    });
})();
