(function () {
    var dataElement = document.getElementById("parametros-negocios-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;

    function toFieldValue(value) {
        if (value === null || value === undefined) return "";
        return String(value);
    }

    function normalizeUnit(value) {
        return String(value || "").toLowerCase() === "percentual" ? "percentual" : "valor";
    }

    function parseDecimalInput(texto) {
        var t = String(texto || "").trim();
        if (!t) return 0;
        t = t.replace(/R\$/g, "").replace(/%/g, "").replace(/\s/g, "");
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

    function formatPercent(value) {
        var numero = parseDecimalInput(value);
        if (!Number.isFinite(numero)) numero = 0;
        return numero.toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }) + "%";
    }

    function formatByUnit(value, unit) {
        return normalizeUnit(unit) === "percentual" ? formatPercent(value) : formatMoney(value);
    }

    function calcularGerenteMpLuciano(compromisso, gerentePaOutros) {
        return parseDecimalInput(compromisso) - parseDecimalInput(gerentePaOutros);
    }

    function atualizarCampoGerenteMpLuciano(compromissoInput, compromissoUnitInput, gerentePaInput, gerenteMpInput) {
        if (!compromissoInput || !compromissoUnitInput || !gerentePaInput || !gerenteMpInput) return;
        if (normalizeUnit(compromissoUnitInput.value) !== "valor") {
            gerenteMpInput.value = "--";
            return;
        }
        var valor = calcularGerenteMpLuciano(compromissoInput.value, gerentePaInput.value);
        gerenteMpInput.value = formatMoney(valor);
    }

    var compromissoNovo = document.getElementById("compromisso-novo");
    var compromissoUnidadeNovo = document.getElementById("compromisso-unidade-novo");
    var gerentePaNovo = document.getElementById("gerente-pa-novo");
    var gerenteMpNovo = document.getElementById("gerente-mp-luciano-novo");
    if (compromissoNovo && compromissoUnidadeNovo && gerentePaNovo && gerenteMpNovo) {
        atualizarCampoGerenteMpLuciano(compromissoNovo, compromissoUnidadeNovo, gerentePaNovo, gerenteMpNovo);
        compromissoNovo.addEventListener("input", function () {
            atualizarCampoGerenteMpLuciano(compromissoNovo, compromissoUnidadeNovo, gerentePaNovo, gerenteMpNovo);
        });
        compromissoUnidadeNovo.addEventListener("change", function () {
            atualizarCampoGerenteMpLuciano(compromissoNovo, compromissoUnidadeNovo, gerentePaNovo, gerenteMpNovo);
        });
        gerentePaNovo.addEventListener("input", function () {
            atualizarCampoGerenteMpLuciano(compromissoNovo, compromissoUnidadeNovo, gerentePaNovo, gerenteMpNovo);
        });
    }

    var unidadeValues = {
        valor: "R$",
        percentual: "%",
    };

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
                meta_unidade: normalizeUnit(row.meta_unidade),
                compromisso: toFieldValue(row.compromisso),
                compromisso_unidade: normalizeUnit(row.compromisso_unidade),
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
        if (normalizeUnit(rowData.compromisso_unidade) !== "valor") {
            row.update({gerente_mp_e_gerente_luciano: 0});
            return;
        }
        var valor = calcularGerenteMpLuciano(rowData.compromisso, rowData.gerente_pa_e_outros);
        row.update({gerente_mp_e_gerente_luciano: valor});
    }

    window.TabulatorDefaults.create("#parametros-negocios-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {
                title: "Direcao",
                field: "direcao",
                editor: "input",
            },
            {
                title: "Meta",
                field: "meta",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return formatByUnit(cell.getValue(), row.meta_unidade);
                },
            },
            {
                title: "Unid. Meta",
                field: "meta_unidade",
                editor: "list",
                editorParams: {
                    values: unidadeValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    return unidadeValues[normalizeUnit(cell.getValue())] || "R$";
                },
            },
            {
                title: "Compromisso",
                field: "compromisso",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return formatByUnit(cell.getValue(), row.compromisso_unidade);
                },
                cellEdited: atualizarGerenteMpDaLinha,
            },
            {
                title: "Unid. Compromisso",
                field: "compromisso_unidade",
                editor: "list",
                editorParams: {
                    values: unidadeValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    return unidadeValues[normalizeUnit(cell.getValue())] || "R$";
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
                    var row = cell.getRow().getData() || {};
                    if (normalizeUnit(row.compromisso_unidade) !== "valor") return "--";
                    return formatMoney(cell.getValue());
                },
            },
            colunaAcoes,
        ],
    });
})();
