(function () {
    var dataElement = document.getElementById("contratos-redes-mascara-data");
    if (!dataElement || !window.Tabulator) return;

    var contratos = JSON.parse(dataElement.textContent || "[]");
    var inputNumeroContrato = document.getElementById("mascara-numero-contrato");
    var inputValorTitulo = document.getElementById("mascara-valor-titulo");
    var checkboxCalcularInativos = document.getElementById("mascara-calcular-inativos");
    var outputDataInicio = document.getElementById("mascara-data-inicio");
    var outputDataEncerramento = document.getElementById("mascara-data-encerramento");
    var outputStatus = document.getElementById("mascara-status");
    var outputTotalDescontos = document.getElementById("mascara-total-descontos");
    var outputValorLiquido = document.getElementById("mascara-valor-liquido");

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function normalizeText(value) {
        return toText(value)
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    var contratosPorNumero = contratos.reduce(function (mapa, item) {
        var chave = normalizeText(item && item.numero_contrato);
        if (!chave) return mapa;
        if (!mapa[chave]) {
            mapa[chave] = [];
        }
        mapa[chave].push(item);
        return mapa;
    }, {});

    function formatMoedaBr(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            style: "currency",
            currency: "BRL",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function formatNumeroBr(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function formatPercentFromRatio(ratio) {
        return (Number(ratio || 0) * 100).toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }) + "%";
    }

    function parseMoedaInput(texto) {
        var t = toText(texto);
        if (!t) return 0;
        t = t.replace(/R\$/gi, "").replace(/\s/g, "");
        if (t.indexOf(",") >= 0) {
            t = t.replace(/\./g, "").replace(",", ".");
        } else if ((t.match(/\./g) || []).length > 1) {
            var parts = t.split(".");
            var decimal = parts.pop();
            t = parts.join("") + "." + decimal;
        }
        t = t.replace(/[^0-9.-]/g, "");
        var numero = Number(t);
        return Number.isFinite(numero) ? numero : 0;
    }

    function formatDateBr(isoDate) {
        var texto = toText(isoDate);
        if (!texto) return "-";
        var match = texto.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (!match) return texto;
        return match[3] + "/" + match[2] + "/" + match[1];
    }

    function filtrarPorNumeroContrato(numeroContrato) {
        var chave = normalizeText(numeroContrato);
        if (!chave) return [];
        return contratosPorNumero[chave] || [];
    }

    function atualizarInfosContrato(linhas) {
        if (!linhas.length) {
            outputDataInicio.value = "-";
            outputDataEncerramento.value = "-";
            outputStatus.value = "-";
            return;
        }

        var datasInicio = linhas
            .map(function (item) { return toText(item.data_inicio_iso); })
            .filter(Boolean)
            .sort();
        var datasEncerramento = linhas
            .map(function (item) { return toText(item.data_encerramento_iso); })
            .filter(Boolean)
            .sort();
        var statusUnicos = Array.from(
            new Set(
                linhas
                    .map(function (item) { return toText(item.status_contrato); })
                    .filter(Boolean)
            )
        );

        outputDataInicio.value = datasInicio.length ? formatDateBr(datasInicio[0]) : "-";
        outputDataEncerramento.value = datasEncerramento.length ? formatDateBr(datasEncerramento[datasEncerramento.length - 1]) : "-";
        outputStatus.value = statusUnicos.length === 1 ? statusUnicos[0] : "Misto";
    }

    function montarLinhasTabela(linhasContrato, valorTitulo, calcularInativos) {
        return linhasContrato.map(function (item) {
            var status = toText(item.status_contrato) || "Ativo";
            var inativo = normalizeText(status) === "inativo";
            var valorAcordo = Number(item.valor_acordo || 0);
            var valorCalculado = valorTitulo * valorAcordo;
            if (!calcularInativos && inativo) {
                valorCalculado = 0;
            }

            return {
                parceiro_descricao: toText(item.parceiro_descricao) || "Sem parceiro",
                descricao_acordos: toText(item.descricao_acordos),
                valor_acordo: valorAcordo,
                valor_calculado: valorCalculado,
                status_contrato: status,
            };
        });
    }

    var tabela = window.TabulatorDefaults
        ? window.TabulatorDefaults.create("#mascara-contrato-tabulator", {
            data: [],
            columns: [
                {title: "Descrição Parceiro", field: "parceiro_descricao"},
                {title: "Descrição dos Acordos", field: "descricao_acordos"},
                {
                    title: "Valor do Acordo (%)",
                    field: "valor_acordo",
                    hozAlign: "right",
                    formatter: function (cell) {
                        return formatPercentFromRatio(cell.getValue());
                    },
                },
                {
                    title: "Valor Calculado",
                    field: "valor_calculado",
                    hozAlign: "right",
                    formatter: function (cell) {
                        return formatMoedaBr(cell.getValue());
                    },
                },
                {title: "Status do Contrato", field: "status_contrato"},
            ],
        })
        : new window.Tabulator("#mascara-contrato-tabulator", {
            data: [],
            layout: "fitDataStretch",
            maxHeight: "62vh",
            columns: [
                {title: "Descrição Parceiro", field: "parceiro_descricao"},
                {title: "Descrição dos Acordos", field: "descricao_acordos"},
                {title: "Valor do Acordo (%)", field: "valor_acordo"},
                {title: "Valor Calculado", field: "valor_calculado"},
                {title: "Status do Contrato", field: "status_contrato"},
            ],
        });

    function atualizarTela() {
        var numeroContrato = toText(inputNumeroContrato && inputNumeroContrato.value);
        var valorTitulo = parseMoedaInput(inputValorTitulo && inputValorTitulo.value);
        var calcularInativos = Boolean(checkboxCalcularInativos && checkboxCalcularInativos.checked);

        var linhasContrato = filtrarPorNumeroContrato(numeroContrato);
        atualizarInfosContrato(linhasContrato);

        var linhasTabela = montarLinhasTabela(linhasContrato, valorTitulo, calcularInativos);
        tabela.setData(linhasTabela);

        var totalDescontos = linhasTabela.reduce(function (acc, item) {
            return acc + Number(item.valor_calculado || 0);
        }, 0);
        var valorLiquido = valorTitulo - totalDescontos;

        outputTotalDescontos.value = formatMoedaBr(totalDescontos);
        outputValorLiquido.value = formatMoedaBr(valorLiquido);
    }

    if (inputNumeroContrato) {
        inputNumeroContrato.addEventListener("input", atualizarTela);
    }
    if (inputValorTitulo) {
        inputValorTitulo.addEventListener("input", atualizarTela);
        inputValorTitulo.addEventListener("blur", function () {
            inputValorTitulo.value = formatNumeroBr(parseMoedaInput(inputValorTitulo.value));
            atualizarTela();
        });
    }
    if (checkboxCalcularInativos) {
        checkboxCalcularInativos.addEventListener("change", atualizarTela);
    }

    if (inputValorTitulo) {
        inputValorTitulo.value = formatNumeroBr(parseMoedaInput(inputValorTitulo.value));
    }
    atualizarTela();
})();
