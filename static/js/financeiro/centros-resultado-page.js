(function () {
    var dataElement = document.getElementById("centros-resultado-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var colunas = [
        {title: "ID", field: "id", width: 80, hozAlign: "center"},
        {title: "Descricao", field: "descricao"},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data);

    var tabela = window.TabulatorDefaults.create("#centros-resultado-tabulator", {
        data: data,
        columns: colunas,
    });

})();
