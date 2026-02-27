(function () {
    var chartContainer = document.getElementById("carteira-dashboard-chart");
    if (!chartContainer || !window.ApexCharts) return;

    var anoSelect = document.getElementById("filtro-ano-dashboard-carteira");
    var anosDisponiveis = JSON.parse(document.getElementById("dashboard-carteira-anos-disponiveis").textContent || "[]");
    var agregados = JSON.parse(document.getElementById("dashboard-carteira-agregados-ano-mes").textContent || "{}");
    var anoInicial = parseInt(JSON.parse(document.getElementById("dashboard-carteira-ano-inicial").textContent || "0"), 10);
    var anoAtual = parseInt(JSON.parse(document.getElementById("dashboard-carteira-ano-atual").textContent || "0"), 10);
    var mesAtual = parseInt(JSON.parse(document.getElementById("dashboard-carteira-mes-atual").textContent || "1"), 10);
    var nomesMeses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });

    function montarSeriesPorAno(anoSelecionado) {
        var limiteMeses = anoSelecionado < anoAtual ? 12 : (anoSelecionado === anoAtual ? mesAtual : 0);
        var categorias = [];
        var qtdCadastramentos = [];
        var valorFaturado = [];

        for (var mes = 1; mes <= limiteMeses; mes++) {
            categorias.push(nomesMeses[mes - 1]);
            var chave = String(anoSelecionado) + "-" + String(mes).padStart(2, "0");
            var agregado = agregados[chave] || {qtd: 0, valor: 0};
            qtdCadastramentos.push(parseInt(agregado.qtd || 0, 10));
            valorFaturado.push(Number(agregado.valor || 0));
        }

        var yMaxQtd = Math.max.apply(null, qtdCadastramentos.concat([0]));
        var yMaxValor = Math.max.apply(null, valorFaturado.concat([0]));
        if (!Number.isFinite(yMaxQtd) || yMaxQtd <= 0) yMaxQtd = 10;
        if (!Number.isFinite(yMaxValor) || yMaxValor <= 0) yMaxValor = 10;

        return {
            categorias: categorias,
            qtdCadastramentos: qtdCadastramentos,
            valorFaturado: valorFaturado,
            yMaxQtd: yMaxQtd,
            yMaxValor: yMaxValor,
        };
    }

    if (anoSelect && anosDisponiveis.length && !anoSelect.value) {
        anoSelect.value = String(anoInicial || anosDisponiveis[anosDisponiveis.length - 1]);
    }

    var anoSelecionadoInicial = anoSelect && anoSelect.value
        ? parseInt(anoSelect.value, 10)
        : (anoInicial || anoAtual);
    var dadosIniciais = montarSeriesPorAno(anoSelecionadoInicial);

    var chart = new ApexCharts(chartContainer, {
        chart: {
            type: "line",
            height: 360,
            toolbar: {show: true},
        },
        series: [
            {
                name: "Qtd Cadastramentos",
                type: "column",
                data: dadosIniciais.qtdCadastramentos,
            },
            {
                name: "Valor Faturado",
                type: "line",
                data: dadosIniciais.valorFaturado,
            },
        ],
        stroke: {
            width: [0, 3],
        },
        colors: ["#175cd3", "#f38744"],
        plotOptions: {
            bar: {
                columnWidth: "55%",
            },
        },
        dataLabels: {
            enabled: true,
            enabledOnSeries: [0, 1],
            formatter: function (value, opts) {
                if (opts.seriesIndex === 1) {
                    return formatadorMoeda.format(Number(value || 0));
                }
                return Math.round(Number(value || 0));
            },
        },
        labels: dadosIniciais.categorias,
        xaxis: {
            categories: dadosIniciais.categorias,
        },
        yaxis: [
            {
                seriesName: "Qtd Cadastramentos",
                min: 0,
                max: dadosIniciais.yMaxQtd,
                tickAmount: 6,
                forceNiceScale: true,
                labels: {
                    formatter: function (value) {
                        return Math.round(Number(value || 0));
                    },
                },
                title: {
                    text: "Qtd Cadastramentos",
                },
            },
            {
                seriesName: "Valor Faturado",
                opposite: true,
                min: 0,
                max: dadosIniciais.yMaxValor,
                tickAmount: 6,
                forceNiceScale: true,
                labels: {
                    formatter: function (value) {
                        return formatadorMoeda.format(Number(value || 0));
                    },
                },
                title: {
                    text: "Valor Faturado",
                },
            },
        ],
        tooltip: {
            shared: true,
            intersect: false,
            y: {
                formatter: function (value, opts) {
                    if (opts && opts.seriesIndex === 1) {
                        return formatadorMoeda.format(Number(value || 0));
                    }
                    return Math.round(Number(value || 0));
                },
            },
        },
    });

    chart.render();

    if (anoSelect) {
        anoSelect.addEventListener("change", function () {
            var anoSelecionado = parseInt(anoSelect.value, 10);
            var dados = montarSeriesPorAno(anoSelecionado);
            chart.updateOptions({
                labels: dados.categorias,
                xaxis: {categories: dados.categorias},
                yaxis: [
                    {
                        seriesName: "Qtd Cadastramentos",
                        min: 0,
                        max: dados.yMaxQtd,
                        tickAmount: 6,
                        forceNiceScale: true,
                        labels: {
                            formatter: function (value) {
                                return Math.round(Number(value || 0));
                            },
                        },
                        title: {
                            text: "Qtd Cadastramentos",
                        },
                    },
                    {
                        seriesName: "Valor Faturado",
                        opposite: true,
                        min: 0,
                        max: dados.yMaxValor,
                        tickAmount: 6,
                        forceNiceScale: true,
                        labels: {
                            formatter: function (value) {
                                return formatadorMoeda.format(Number(value || 0));
                            },
                        },
                        title: {
                            text: "Valor Faturado",
                        },
                    },
                ],
            });
            chart.updateSeries([
                {name: "Qtd Cadastramentos", type: "column", data: dados.qtdCadastramentos},
                {name: "Valor Faturado", type: "line", data: dados.valorFaturado},
            ]);
        });
    }
})();

(function () {
    var form = document.getElementById("upload-carteira-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-carteira");
    var input = document.getElementById("arquivo-carteira-input");
    var confirmInput = document.getElementById("confirmar-substituicao-input");
    var fileStatus = document.getElementById("nome-arquivo-selecionado");
    var loadingStatus = document.getElementById("carteira-loading-status");
    var temArquivoExistente = form.dataset.temArquivoExistente === "1";
    var frontendText = window.FrontendText || {};
    var commonText = frontendText.common || {};
    var uploadText = frontendText.upload || {};
    var confirmText = frontendText.confirm || {};
    var arquivoXlsxLabel = ".xlsx";

    function mensagemApenasArquivoPermitido() {
        if (typeof uploadText.onlyAllowedFile === "function") {
            return uploadText.onlyAllowedFile(arquivoXlsxLabel);
        }
        return "Envie apenas arquivo .xlsx.";
    }

    function mensagemSelecionarArquivoParaContinuar() {
        if (typeof uploadText.selectFileToContinue === "function") {
            return uploadText.selectFileToContinue(arquivoXlsxLabel);
        }
        return "Selecione um arquivo .xlsx para continuar.";
    }

    function iniciarCarregamento() {
        form.classList.add("is-loading");
        loadingStatus.classList.add("is-visible");
    }

    function limparSelecaoArquivo() {
        input.value = "";
        confirmInput.value = "0";
        fileStatus.textContent = "";
        dropzone.classList.remove("dragover");
    }

    function atualizarNomeArquivo() {
        if (!input.files || !input.files.length) {
            fileStatus.textContent = "";
            return;
        }
        var selectedFilePrefix = commonText.selectedFilePrefix || "Arquivo selecionado: ";
        fileStatus.textContent = selectedFilePrefix + input.files[0].name;
    }

    function validarExtensaoXlsx(file) {
        return file && file.name.toLowerCase().endsWith(".xlsx");
    }

    function confirmarSubstituicaoSeNecessario() {
        if (!temArquivoExistente) {
            confirmInput.value = "0";
            return true;
        }

        var replaceCurrentFileMessage = confirmText.replaceCurrentFile || "Já existe um arquivo na pasta. Deseja substituir o arquivo atual?";
        var confirmou = window.confirm(replaceCurrentFileMessage);
        if (!confirmou) {
            return false;
        }

        confirmInput.value = "1";
        return true;
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
        var files = event.dataTransfer.files;
        if (!files || !files.length) {
            return;
        }

        var file = files[0];
        if (!validarExtensaoXlsx(file)) {
            window.alert(mensagemApenasArquivoPermitido());
            return;
        }

        input.files = files;
        atualizarNomeArquivo();
    });

    input.addEventListener("change", function () {
        if (!input.files || !input.files.length) {
            return;
        }

        var file = input.files[0];
        if (!validarExtensaoXlsx(file)) {
            window.alert(mensagemApenasArquivoPermitido());
            input.value = "";
            atualizarNomeArquivo();
            return;
        }

        atualizarNomeArquivo();
    });

    form.addEventListener("submit", function (event) {
        if (!input.files || !input.files.length) {
            event.preventDefault();
            window.alert(mensagemSelecionarArquivoParaContinuar());
            return;
        }

        var file = input.files[0];
        if (!validarExtensaoXlsx(file)) {
            event.preventDefault();
            window.alert(mensagemApenasArquivoPermitido());
            return;
        }

        if (temArquivoExistente && confirmInput.value !== "1") {
            if (!confirmarSubstituicaoSeNecessario()) {
                event.preventDefault();
                limparSelecaoArquivo();
                return;
            }
        }

        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("carteira-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var kpiEls = {
        totalCarteira: {
            qtdTotal: document.getElementById("kpi-total-carteira-qtd-total"),
            positivacao: document.getElementById("kpi-total-carteira-positivacao"),
            limite: document.getElementById("kpi-total-carteira-limite"),
            faturamento: document.getElementById("kpi-total-carteira-faturamento"),
            media: document.getElementById("kpi-total-carteira-media"),
            mediaFaturamento: document.getElementById("kpi-total-carteira-media-faturamento"),
            pulga: document.getElementById("kpi-total-carteira-pulga"),
        },
        totalReal: {
            qtdTotal: document.getElementById("kpi-total-real-qtd-total"),
            positivacao: document.getElementById("kpi-total-real-positivacao"),
            limite: document.getElementById("kpi-total-real-limite"),
            faturamento: document.getElementById("kpi-total-real-faturamento"),
            media: document.getElementById("kpi-total-real-media"),
            mediaFaturamento: document.getElementById("kpi-total-real-media-faturamento"),
            pulga: document.getElementById("kpi-total-real-pulga"),
        },
    };

    function formatNumero(valor, casas) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            minimumFractionDigits: casas,
            maximumFractionDigits: casas,
        });
    }

    function formatMoeda(valor) {
        return "R$ " + formatNumero(valor, 2);
    }

    function formatPercentual(valor) {
        return formatNumero(valor, 2) + "%";
    }

    function dividirOuZero(numerador, denominador) {
        if (!denominador) return 0;
        return numerador / denominador;
    }

    function atualizarDashboardComDadosVisiveis() {
        var linhasAtivas = tabela.getData("active");
        if (!linhasAtivas || !linhasAtivas.length) {
            linhasAtivas = tabela.getData();
        }
        if (!linhasAtivas || !linhasAtivas.length) {
            linhasAtivas = data;
        }
        var qtdTotal = linhasAtivas.length;
        var limiteTotal = 0;
        var faturamentoTotal = 0;
        var qtdReal = 0;
        var limiteTotalReal = 0;
        var faturamentoTotalReal = 0;

        linhasAtivas.forEach(function (item) {
            var limite = Number(item.limite_credito || 0);
            var faturamento = Number(item.valor_faturado || 0);
            limiteTotal += limite;
            faturamentoTotal += faturamento;

            if (faturamento > 0) {
                qtdReal += 1;
                limiteTotalReal += limite;
                faturamentoTotalReal += faturamento;
            }
        });

        var positivacaoReal = dividirOuZero(qtdReal * 100, qtdTotal);
        var positivacaoTotalCarteira = 100 - positivacaoReal;
        var mediaLimiteTotal = dividirOuZero(limiteTotal, qtdTotal);
        var mediaFaturamentoTotal = dividirOuZero(faturamentoTotal, qtdTotal);
        var pulgaTotal = dividirOuZero(faturamentoTotal * 100, limiteTotal);
        var mediaLimiteReal = dividirOuZero(limiteTotalReal, qtdReal);
        var mediaFaturamentoReal = dividirOuZero(faturamentoTotalReal, qtdReal);
        var pulgaReal = dividirOuZero(faturamentoTotalReal * 100, limiteTotalReal);

        kpiEls.totalCarteira.qtdTotal.textContent = formatNumero(qtdTotal, 0);
        kpiEls.totalCarteira.positivacao.textContent = formatPercentual(positivacaoTotalCarteira);
        kpiEls.totalCarteira.limite.textContent = formatMoeda(limiteTotal);
        kpiEls.totalCarteira.faturamento.textContent = formatMoeda(faturamentoTotal);
        kpiEls.totalCarteira.media.textContent = formatMoeda(mediaLimiteTotal);
        kpiEls.totalCarteira.mediaFaturamento.textContent = formatNumero(mediaFaturamentoTotal, 2);
        kpiEls.totalCarteira.pulga.textContent = formatPercentual(pulgaTotal);

        kpiEls.totalReal.qtdTotal.textContent = formatNumero(qtdReal, 0);
        kpiEls.totalReal.positivacao.textContent = formatPercentual(positivacaoReal);
        kpiEls.totalReal.limite.textContent = formatMoeda(limiteTotalReal);
        kpiEls.totalReal.faturamento.textContent = formatMoeda(faturamentoTotalReal);
        kpiEls.totalReal.media.textContent = formatMoeda(mediaLimiteReal);
        kpiEls.totalReal.mediaFaturamento.textContent = formatNumero(mediaFaturamentoReal, 2);
        kpiEls.totalReal.pulga.textContent = formatPercentual(pulgaReal);
    }

    var colunas = [
        {title: "ID", field: "id", width: 75, hozAlign: "center", headerFilter: "input"},
        {title: "Parceiro", field: "nome_parceiro", headerFilter: "input"},
        {title: "Codigo parceiro", field: "codigo_parceiro", headerFilter: "input"},
        {title: "Gerente", field: "gerente", headerFilter: "input"},
        {title: "Vendedor", field: "vendedor", headerFilter: "input"},
        {
            title: "Valor faturado",
            field: "valor_faturado",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2},
        },
        {
            title: "Limite credito",
            field: "limite_credito",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2},
        },
        {title: "Ultima venda", field: "ultima_venda", headerFilter: "input"},
        {title: "Dias sem venda", field: "qtd_dias_sem_venda", hozAlign: "center", headerFilter: "input"},
        {title: "Intervalo", field: "intervalo"},
        {title: "Descricao perfil", field: "descricao_perfil", headerFilter: "input"},
        {title: "Ativo", field: "ativo_indicador", hozAlign: "center", headerFilter: "tickCross", formatter: "tickCross"},
        {title: "Cliente", field: "cliente_indicador", hozAlign: "center", headerFilter: "tickCross", formatter: "tickCross"},
        {title: "Fornecedor", field: "fornecedor_indicador", hozAlign: "center", headerFilter: "tickCross", formatter: "tickCross"},
        {title: "Transportadora", field: "transporte_indicador", hozAlign: "center", headerFilter: "tickCross", formatter: "tickCross"},
        {title: "Ano cadastro", field: "ano_cadastro", hozAlign: "center", headerFilter: "input"},
        {title: "Data cadastro", field: "data_cadastro", headerFilter: "input"},
        {title: "Regiao", field: "regiao_nome", headerFilter: "input"},
        {title: "Codigo regiao", field: "regiao_codigo", headerFilter: "input"},
        {title: "Cidade", field: "cidade_nome", headerFilter: "input"},
        {title: "Codigo cidade", field: "cidade_codigo", headerFilter: "input"},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data);

    var tabela = window.TabulatorDefaults.create("#carteira-tabulator", {
        data: data,
        columns: colunas,
    });

    tabela.on("tableBuilt", atualizarDashboardComDadosVisiveis);
    tabela.on("dataLoaded", atualizarDashboardComDadosVisiveis);
    tabela.on("renderComplete", atualizarDashboardComDadosVisiveis);
    tabela.on("dataFiltered", atualizarDashboardComDadosVisiveis);
    setTimeout(atualizarDashboardComDadosVisiveis, 0);
})();




