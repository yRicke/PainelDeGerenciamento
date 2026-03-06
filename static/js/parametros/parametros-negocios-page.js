(function () {
    var dataElement = document.getElementById("parametros-negocios-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;

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
            maximumFractionDigits: 2,
        });
    }

    function calcularGerenteMpLuciano(compromisso, gerentePaOutros) {
        return parseDecimalInput(compromisso) - parseDecimalInput(gerentePaOutros);
    }

    function atualizarCampoGerenteMpLuciano(compromissoInput, gerentePaInput, gerenteMpInput) {
        if (!compromissoInput || !gerentePaInput || !gerenteMpInput) return;
        var valor = calcularGerenteMpLuciano(compromissoInput.value, gerentePaInput.value);
        gerenteMpInput.value = formatMoney(valor);
    }

    var compromissoNovo = document.getElementById("compromisso-novo");
    var gerentePaNovo = document.getElementById("gerente-pa-novo");
    var gerenteMpNovo = document.getElementById("gerente-mp-luciano-novo");
    if (compromissoNovo && gerentePaNovo && gerenteMpNovo) {
        atualizarCampoGerenteMpLuciano(compromissoNovo, gerentePaNovo, gerenteMpNovo);
        compromissoNovo.addEventListener("input", function () {
            atualizarCampoGerenteMpLuciano(compromissoNovo, gerentePaNovo, gerenteMpNovo);
        });
        gerentePaNovo.addEventListener("input", function () {
            atualizarCampoGerenteMpLuciano(compromissoNovo, gerentePaNovo, gerenteMpNovo);
        });
    }

    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        submitPost: submitPost,
        getSaveUrl: function (row) {
            return row.acao_url;
        },
        getDeleteUrl: function (row) {
            return row.acao_url;
        },
        getSavePayload: function (row) {
            return {
                acao: "editar",
                item_id: row.id,
                direcao: toFieldValue(row.direcao),
                meta: toFieldValue(row.meta),
                compromisso: toFieldValue(row.compromisso),
                gerente_pa_e_outros: toFieldValue(row.gerente_pa_e_outros),
            };
        },
        getDeletePayload: function (row) {
            return {
                acao: "excluir",
                item_id: row.id,
            };
        },
        deleteConfirm: "Excluir parametro?",
    });

    function atualizarGerenteMpDaLinha(cell) {
        if (!cell || !cell.getRow) return;
        var row = cell.getRow();
        var rowData = row.getData() || {};
        var valor = calcularGerenteMpLuciano(rowData.compromisso, rowData.gerente_pa_e_outros);
        row.update({gerente_mp_e_gerente_luciano: valor});
    }

    var tabela = window.TabulatorDefaults.create("#parametros-negocios-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {
                title: "Direcao",
                field: "direcao",
                editor: "input",
            },
            {
                title: "Meta (R$)",
                field: "meta",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
                },
            },
            {
                title: "Compromisso (R$)",
                field: "compromisso",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
                },
                cellEdited: atualizarGerenteMpDaLinha,
            },
            {
                title: "Gerente PA e Outros (R$)",
                field: "gerente_pa_e_outros",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
                },
                cellEdited: atualizarGerenteMpDaLinha,
            },
            {
                title: "Gerente MP e Gerente Luciano (R$)",
                field: "gerente_mp_e_gerente_luciano",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
                },
            },
            colunaAcoes,
        ],
    });

})();
