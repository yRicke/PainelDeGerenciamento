(function () {
    var dataElement = document.getElementById("parametros-vendas-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroParametro = document.getElementById("filtro-parametros-vendas-parametro");
    var filtroCriterio = document.getElementById("filtro-parametros-vendas-criterio");
    var filtroRemuneracao = document.getElementById("filtro-parametros-vendas-remuneracao");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-parametros-vendas");

    function toFieldValue(value) {
        if (value === null || value === undefined) return "";
        return String(value);
    }

    function parseRatioInput(texto) {
        var t = String(texto || "").trim();
        if (!t) return 0;
        var temPercentual = t.indexOf("%") >= 0;
        t = t.replace(/%/g, "").replace(/\s/g, "");
        if (t.indexOf(",") >= 0) {
            t = t.replace(/\./g, "").replace(",", ".");
        } else if ((t.match(/\./g) || []).length > 1 && t.toLowerCase().indexOf("e") < 0) {
            t = t.replace(/\./g, "");
        }
        var numero = Number(t);
        if (!Number.isFinite(numero)) return 0;
        if (temPercentual) return numero / 100;
        if (Math.abs(numero) > 1) return numero / 100;
        return numero;
    }

    function formatPercentFromRatio(value) {
        var percentual = parseRatioInput(value) * 100;
        if (!Number.isFinite(percentual)) percentual = 0;
        return percentual.toLocaleString("pt-BR", {
            minimumFractionDigits: 4,
            maximumFractionDigits: 4,
        }) + "%";
    }

    var tabela = window.TabulatorDefaults.create("#parametros-vendas-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Parametro", field: "parametro", editor: "input"},
            {title: "Criterio", field: "criterio", editor: "input"},
            {
                title: "Remuneracao (%)",
                field: "remuneracao_percentual",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatPercentFromRatio(cell.getValue());
                },
            },
            {
                title: "Acoes",
                hozAlign: "center",
                formatter: function () {
                    return '<button class="btn-primary" type="button">Salvar</button> <button class="btn-danger" type="button">Excluir</button>';
                },
                cellClick: function (e, cell) {
                    var row = cell.getRow().getData();
                    if (!row || !row.acao_url) return;

                    if (e.target && e.target.classList && e.target.classList.contains("btn-primary")) {
                        submitPost(row.acao_url, {
                            acao: "editar",
                            item_id: row.id,
                            parametro: toFieldValue(row.parametro),
                            criterio: toFieldValue(row.criterio),
                            remuneracao_percentual: toFieldValue(row.remuneracao_percentual),
                        });
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("btn-danger")) {
                        submitPost(row.acao_url, {
                            acao: "excluir",
                            item_id: row.id,
                        }, "Excluir parametro?");
                    }
                },
            },
        ],
    });

    function aplicarFiltros() {
        var parametro = (filtroParametro && filtroParametro.value ? filtroParametro.value : "").toLowerCase().trim();
        var criterio = (filtroCriterio && filtroCriterio.value ? filtroCriterio.value : "").toLowerCase().trim();
        var remuneracao = (filtroRemuneracao && filtroRemuneracao.value ? filtroRemuneracao.value : "").toLowerCase().trim();

        tabela.setFilter(function (rowData) {
            var parametroRow = toFieldValue(rowData.parametro).toLowerCase();
            var criterioRow = toFieldValue(rowData.criterio).toLowerCase();
            var remuneracaoRaw = toFieldValue(rowData.remuneracao_percentual).toLowerCase();
            var remuneracaoFmt = formatPercentFromRatio(rowData.remuneracao_percentual).toLowerCase();

            if (parametro && parametroRow.indexOf(parametro) < 0) return false;
            if (criterio && criterioRow.indexOf(criterio) < 0) return false;
            if (remuneracao && remuneracaoRaw.indexOf(remuneracao) < 0 && remuneracaoFmt.indexOf(remuneracao) < 0) return false;
            return true;
        });
    }

    [filtroParametro, filtroCriterio, filtroRemuneracao].forEach(function (el) {
        if (!el) return;
        el.addEventListener("input", aplicarFiltros);
    });

    if (limparFiltrosBtn) {
        limparFiltrosBtn.addEventListener("click", function () {
            if (filtroParametro) filtroParametro.value = "";
            if (filtroCriterio) filtroCriterio.value = "";
            if (filtroRemuneracao) filtroRemuneracao.value = "";
            tabela.clearFilter(true);
        });
    }
})();
