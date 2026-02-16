(function () {
    var form = document.getElementById("upload-vendas-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-vendas");
    var input = document.getElementById("arquivos-vendas-input");
    var statusArquivos = document.getElementById("nome-arquivos-vendas-selecionados");
    var loadingStatus = document.getElementById("vendas-loading-status");

    function iniciarCarregamento() {
        form.classList.add("is-loading");
        loadingStatus.classList.add("is-visible");
    }

    function coletarArquivosXls(files) {
        if (!files || !files.length) return [];
        return Array.from(files).filter(function (file) {
            return file && file.name && file.name.toLowerCase().endsWith(".xls");
        });
    }

    function atualizarStatus(filesXls) {
        if (!filesXls.length) {
            statusArquivos.textContent = "";
            return;
        }
        statusArquivos.textContent = filesXls.length + " arquivo(s) .xls selecionado(s).";
    }

    function atribuirArquivosNoInput(filesXls) {
        var dt = new DataTransfer();
        filesXls.forEach(function (file) { dt.items.add(file); });
        input.files = dt.files;
    }

    function selecionarArquivos(files) {
        var arquivosXls = coletarArquivosXls(files);
        if (!arquivosXls.length) {
            window.alert("Nenhum arquivo .xls encontrado.");
            input.value = "";
            atualizarStatus([]);
            return;
        }
        atribuirArquivosNoInput(arquivosXls);
        atualizarStatus(arquivosXls);
    }

    dropzone.addEventListener("click", function () {
        input.click();
    });

    dropzone.addEventListener("dragover", function (event) {
        event.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", function () {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", function (event) {
        event.preventDefault();
        dropzone.classList.remove("dragover");
        selecionarArquivos(event.dataTransfer.files);
    });

    input.addEventListener("change", function () {
        selecionarArquivos(input.files);
    });

    form.addEventListener("submit", function (event) {
        var arquivosXls = coletarArquivosXls(input.files);
        if (!arquivosXls.length) {
            event.preventDefault();
            window.alert("Selecione uma pasta com arquivos .xls para continuar.");
            return;
        }
        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("vendas-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var situacaoMargemSelect = document.getElementById("filtro-situacao-margem");
    var anoVendaSelect = document.getElementById("filtro-ano-venda");
    var mesVendaSelect = document.getElementById("filtro-mes-venda");
    var limparBtn = document.getElementById("limpar-filtros-vendas");
    var nomeMes = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Marco",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro"
    };

    function preencherSelect(select, valores, labelFn) {
        valores.forEach(function (valor) {
            var option = document.createElement("option");
            option.value = String(valor);
            option.textContent = labelFn ? labelFn(valor) : String(valor);
            select.appendChild(option);
        });
    }

    var anosVenda = Array.from(new Set(data.map(function (item) { return item.ano_venda; }).filter(Boolean))).sort(function (a, b) { return b - a; });
    var mesesVenda = Array.from(new Set(data.map(function (item) { return item.mes_venda; }).filter(Boolean))).sort(function (a, b) { return a - b; });

    preencherSelect(anoVendaSelect, anosVenda);
    preencherSelect(mesVendaSelect, mesesVenda, function (valor) {
        return (nomeMes[valor] || valor) + " (" + String(valor).padStart(2, "0") + ")";
    });

    var tabela = new Tabulator("#vendas-tabulator", {
        data: data,
        layout: "fitDataStretch",
        pagination: true,
        paginationSize: 10,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center", headerFilter: "input"},
            {title: "Codigo", field: "codigo", headerFilter: "input"},
            {title: "Descricao", field: "descricao", headerFilter: "input"},
            {
                title: "Valor venda",
                field: "valor_venda",
                hozAlign: "right",
                headerFilter: "input",
                formatter: "money",
                formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2}
            },
            {title: "Qtd notas", field: "qtd_notas", hozAlign: "center", headerFilter: "input"},
            {
                title: "Custo medio ICMS CMV",
                field: "custo_medio_icms_cmv",
                hozAlign: "right",
                headerFilter: "input",
                formatter: "money",
                formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2}
            },
            {
                title: "Lucro",
                field: "lucro",
                hozAlign: "right",
                headerFilter: "input",
                formatter: "money",
                formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2}
            },
            {
                title: "Peso bruto",
                field: "peso_bruto",
                hozAlign: "right",
                headerFilter: "input",
                formatter: "money",
                formatterParams: {decimal: ",", thousand: ".", symbol: "", symbolAfter: false, precision: 2}
            },
            {
                title: "Peso liquido",
                field: "peso_liquido",
                hozAlign: "right",
                headerFilter: "input",
                formatter: "money",
                formatterParams: {decimal: ",", thousand: ".", symbol: "", symbolAfter: false, precision: 2}
            },
            {
                title: "Margem",
                field: "margem",
                hozAlign: "right",
                headerFilter: "input",
                formatter: function (cell) {
                    return Number(cell.getValue() || 0).toLocaleString("pt-BR", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    }) + "%";
                }
            },
            {title: "Situacao margem", field: "margem_situacao", headerFilter: "input"},
            {title: "Ano venda", field: "ano_venda", hozAlign: "center", headerFilter: "input"},
            {title: "Mes venda", field: "mes_venda", hozAlign: "center", headerFilter: "input"},
            {
                title: "Data venda",
                field: "data_venda",
                headerFilter: "input",
                sorter: function (a, b, aRow, bRow) {
                    var dataA = aRow.getData().data_venda_iso || "";
                    var dataB = bRow.getData().data_venda_iso || "";
                    if (dataA === dataB) return 0;
                    return dataA > dataB ? 1 : -1;
                }
            },
            {
                title: "Acoes",
                field: "editar_url",
                formatter: function (cell) {
                    var url = cell.getValue();
                    return '<a class="btn-primary" href="' + url + '">Editar</a>';
                },
                hozAlign: "center"
            }
        ]
    });

    function aplicarFiltros() {
        var situacaoMargem = situacaoMargemSelect.value || "";
        var anoVenda = anoVendaSelect.value || "";
        var mesVenda = mesVendaSelect.value || "";

        tabela.setFilter(function (dataRow) {
            if (situacaoMargem && dataRow.margem_situacao !== situacaoMargem) return false;
            if (anoVenda && String(dataRow.ano_venda) !== String(anoVenda)) return false;
            if (mesVenda && String(dataRow.mes_venda) !== String(mesVenda)) return false;
            return true;
        });
    }

    [situacaoMargemSelect, anoVendaSelect, mesVendaSelect].forEach(function (element) {
        element.addEventListener("change", aplicarFiltros);
        element.addEventListener("input", aplicarFiltros);
    });

    limparBtn.addEventListener("click", function () {
        situacaoMargemSelect.value = "";
        anoVendaSelect.value = "";
        mesVendaSelect.value = "";
        tabela.clearFilter(true);
        tabela.clearHeaderFilter();
    });
})();
