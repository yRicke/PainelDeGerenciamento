(function () {
    var dataElement = document.getElementById("parceiros-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var colunas = [
        {title: "ID", field: "id", width: 80, hozAlign: "center"},
        {title: "Nome", field: "nome"},
        {title: "Código", field: "codigo"},
        {title: "Cidade", field: "cidade_nome"},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data);

    var tabela = window.TabulatorDefaults.create("#parceiros-tabulator", {
        data: data,
        columns: colunas,
    });

})();
