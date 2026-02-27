(function () {
    var dataElement = document.getElementById("operacoes-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var colunas = [
        {title: "ID", field: "id", width: 80, hozAlign: "center"},
        {title: "Codigo", field: "tipo_operacao_codigo"},
        {title: "Descricao Receita/Despesa", field: "descricao_receita_despesa"},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data);

    var tabela = window.TabulatorDefaults.create("#operacoes-tabulator", {
        data: data,
        columns: colunas,
    });

})();
