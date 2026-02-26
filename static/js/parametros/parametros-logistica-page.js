(function () {
    var dataElement = document.getElementById("parametros-logistica-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var filtroParametro = document.getElementById("filtro-parametros-logistica-parametro");
    var filtroCriterio = document.getElementById("filtro-parametros-logistica-criterio");
    var filtroRemuneracao = document.getElementById("filtro-parametros-logistica-remuneracao");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-parametros-logistica");

    function toFieldValue(value) {
        if (value === null || value === undefined) return "";
        return String(value);
    }

    function parseDecimalInput(texto) {
        var t = String(texto || "").trim();
        if (!t) return 0;
        t = t.replace(/R\$/g, "").replace(/\s/g, "");
        if (t.indexOf(",") >= 0) {
            t = t.replace(/\./g, "").replace(",", ".");
        } else if ((t.match(/\./g) || []).length > 1 && t.toLowerCase().indexOf("e") < 0) {
            t = t.replace(/\./g, "");
        }
        var numero = Number(t);
        if (!Number.isFinite(numero)) return 0;
        return numero;
    }

    function formatMoney(value) {
        var numero = parseDecimalInput(value);
        if (!Number.isFinite(numero)) numero = 0;
        return "R$ " + numero.toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 4,
        });
    }

    var tabela = window.TabulatorDefaults.create("#parametros-logistica-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Parametro", field: "parametro", editor: "input"},
            {title: "Criterio", field: "criterio", editor: "input"},
            {
                title: "Remuneracao (R$)",
                field: "remuneracao_rs",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
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
                            remuneracao_rs: toFieldValue(row.remuneracao_rs),
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
            var remuneracaoRaw = toFieldValue(rowData.remuneracao_rs).toLowerCase();
            var remuneracaoFmt = formatMoney(rowData.remuneracao_rs).toLowerCase();

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
