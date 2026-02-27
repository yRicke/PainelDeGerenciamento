(function () {
    var dataElement = document.getElementById("naturezas-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var colunas = [
        {title: "ID", field: "id", width: 80, hozAlign: "center"},
        {title: "Codigo", field: "codigo"},
        {title: "Descricao", field: "descricao"},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data);

    var tabela = window.TabulatorDefaults.create("#naturezas-tabulator", {
        data: data,
        columns: colunas,
    });

})();
