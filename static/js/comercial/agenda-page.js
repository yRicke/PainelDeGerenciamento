(function () {
    var dataElement = document.getElementById("agenda-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;

    function formatDateIsoToBr(value) {
        var iso = String(value || "").trim();
        if (!iso) return "";
        var parts = iso.split("-");
        if (parts.length !== 3) return iso;
        return parts[2] + "/" + parts[1] + "/" + parts[0];
    }

    function buildOptionsFromSelect(name) {
        var select = document.querySelector('form select[name="' + name + '"]');
        if (!select) return [];
        return Array.from(select.options || [])
            .map(function (opt) {
                return {
                    value: String(opt.value || ""),
                    label: String(opt.textContent || "").trim(),
                };
            })
            .filter(function (opt) { return Boolean(opt.value); });
    }

    function toEditorValues(options) {
        var values = {};
        options.forEach(function (opt) {
            values[opt.value] = opt.label;
        });
        return values;
    }

    function toLabelMap(options) {
        var map = {};
        options.forEach(function (opt) {
            map[String(opt.value)] = opt.label;
        });
        return map;
    }

    var motoristasOptions = buildOptionsFromSelect("motorista_id");
    var transportadorasOptions = buildOptionsFromSelect("transportadora_id");
    var motoristasValues = toEditorValues(motoristasOptions);
    var transportadorasValues = toEditorValues(transportadorasOptions);
    var motoristasLabelMap = toLabelMap(motoristasOptions);
    var transportadorasLabelMap = toLabelMap(transportadorasOptions);

    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                data_registro: row.data_registro_iso || "",
                numero_unico: row.numero_unico || "",
                previsao_carregamento: row.previsao_carregamento_iso || "",
                motorista_id: row.motorista_id || "",
                transportadora_id: row.transportadora_id || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir agenda?",
    });

    var tabela = window.TabulatorDefaults.create("#agenda-tabulator", {
        data: data,
        columns: [
            {
                title: "Data Registro",
                field: "data_registro_iso",
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
            },
            {title: "Número Único", field: "numero_unico", editor: "input"},
            {
                title: "Previsão de Carregamento",
                field: "previsao_carregamento_iso",
                editor: "input",
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
            },
            {
                title: "Motorista",
                field: "motorista_id",
                editor: "list",
                editorParams: {
                    values: motoristasValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var id = String(cell.getValue() || "");
                    return motoristasLabelMap[id] || row.motorista_nome || "";
                },
            },
            {
                title: "Transportadora",
                field: "transportadora_id",
                editor: "list",
                editorParams: {
                    values: transportadorasValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var id = String(cell.getValue() || "");
                    return transportadorasLabelMap[id] || row.transportadora_nome || "";
                },
            },
            colunaAcoes,
        ],
    });

})();
