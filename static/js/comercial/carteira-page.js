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
        fileStatus.textContent = "Arquivo selecionado: " + input.files[0].name;
    }

    function validarExtensaoXlsx(file) {
        return file && file.name.toLowerCase().endsWith(".xlsx");
    }

    function confirmarSubstituicaoSeNecessario() {
        if (!temArquivoExistente) {
            confirmInput.value = "0";
            return true;
        }

        var confirmou = window.confirm("Ja existe um arquivo de carteira. Deseja substituir o arquivo atual?");
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
            window.alert("Envie apenas arquivo .xlsx.");
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
            window.alert("Envie apenas arquivo .xlsx.");
            input.value = "";
            atualizarNomeArquivo();
            return;
        }

        atualizarNomeArquivo();
    });

    form.addEventListener("submit", function (event) {
        if (!input.files || !input.files.length) {
            event.preventDefault();
            window.alert("Selecione um arquivo .xlsx para continuar.");
            return;
        }

        var file = input.files[0];
        if (!validarExtensaoXlsx(file)) {
            event.preventDefault();
            window.alert("Envie apenas arquivo .xlsx.");
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
    var gerenteContainer = document.getElementById("filtro-gerente");
    var ativoContainer = document.getElementById("filtro-ativo");
    var clienteContainer = document.getElementById("filtro-cliente");
    var fornecedorContainer = document.getElementById("filtro-fornecedor");
    var transportadoraContainer = document.getElementById("filtro-transportadora");
    var descricaoPerfilContainer = document.getElementById("filtro-descricao-perfil");
    var anoCadastroContainer = document.getElementById("filtro-ano-cadastro");
    var limparBtn = document.getElementById("limpar-filtros-carteira");
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

    function normalizarTexto(valor, vazioLabel) {
        var texto = (valor || "").toString().trim();
        return texto || vazioLabel;
    }

    function valoresUnicosOrdenados(campo, vazioLabel, sorter) {
        var setValores = new Set();
        data.forEach(function (item) {
            setValores.add(normalizarTexto(item[campo], vazioLabel));
        });
        var valores = Array.from(setValores);
        if (sorter) return valores.sort(sorter);
        return valores.sort(function (a, b) {
            return a.localeCompare(b, "pt-BR");
        });
    }

    function criarEstadoSelecao() {
        return {
            gerente: new Set(),
            ativo: new Set(),
            cliente: new Set(),
            fornecedor: new Set(),
            transportadora: new Set(),
            descricao_perfil: new Set(),
            ano_cadastro: new Set(),
        };
    }

    var filtrosSelecionados = criarEstadoSelecao();

    function criarBotaoFiltro(valor, onToggle) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "carteira-filtro-btn";
        btn.textContent = valor;
        btn.addEventListener("click", function () {
            btn.classList.toggle("is-active");
            onToggle(btn.classList.contains("is-active"), valor);
            aplicarFiltros();
        });
        return btn;
    }

    function montarGrupoFiltros(container, valores, chaveEstado) {
        if (!container) return;
        container.innerHTML = "";
        valores.forEach(function (valor) {
            var btn = criarBotaoFiltro(valor, function (ativo, valorToggle) {
                if (ativo) filtrosSelecionados[chaveEstado].add(valorToggle);
                else filtrosSelecionados[chaveEstado].delete(valorToggle);
            });
            container.appendChild(btn);
        });
    }

    function boolToLabel(valor, trueLabel, falseLabel) {
        return valor ? trueLabel : falseLabel;
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

    if (data.some(function (item) { return Boolean(item.editar_url); })) {
        colunas.push({
            title: "Acoes",
            field: "editar_url",
            formatter: function (cell) {
                var url = cell.getValue();
                return url ? '<a class="btn-primary" href="' + url + '">Editar</a>' : "";
            },
            hozAlign: "center",
        });
    }

    var tabela = window.TabulatorDefaults.create("#carteira-tabulator", {
        data: data,
        layout: "fitDataTable",
        pagination: true,
        paginationSize: 100,
        columns: colunas,
    });

    function aplicarFiltros() {
        tabela.setFilter(function (dataRow) {
            var gerenteValor = normalizarTexto(dataRow.gerente, "<SEM GERENTE>");
            var ativoValor = boolToLabel(Boolean(dataRow.ativo_indicador), "Ativo", "Desativado");
            var clienteValor = boolToLabel(Boolean(dataRow.cliente_indicador), "Cliente", "Nao Cliente");
            var fornecedorValor = boolToLabel(Boolean(dataRow.fornecedor_indicador), "Fornecedor", "Nao Fornecedor");
            var transportadoraValor = boolToLabel(Boolean(dataRow.transporte_indicador), "Transportadora", "Nao Transportadora");
            var descricaoPerfilValor = normalizarTexto(dataRow.descricao_perfil, "<SEM DESCRICAO>");
            var anoCadastroValor = normalizarTexto(dataRow.ano_cadastro, "<SEM ANO>");

            if (filtrosSelecionados.gerente.size && !filtrosSelecionados.gerente.has(gerenteValor)) return false;
            if (filtrosSelecionados.ativo.size && !filtrosSelecionados.ativo.has(ativoValor)) return false;
            if (filtrosSelecionados.cliente.size && !filtrosSelecionados.cliente.has(clienteValor)) return false;
            if (filtrosSelecionados.fornecedor.size && !filtrosSelecionados.fornecedor.has(fornecedorValor)) return false;
            if (filtrosSelecionados.transportadora.size && !filtrosSelecionados.transportadora.has(transportadoraValor)) return false;
            if (filtrosSelecionados.descricao_perfil.size && !filtrosSelecionados.descricao_perfil.has(descricaoPerfilValor)) return false;
            if (filtrosSelecionados.ano_cadastro.size && !filtrosSelecionados.ano_cadastro.has(anoCadastroValor)) return false;
            return true;
        });
    }

    montarGrupoFiltros(gerenteContainer, valoresUnicosOrdenados("gerente", "<SEM GERENTE>"), "gerente");
    montarGrupoFiltros(ativoContainer, ["Ativo", "Desativado"], "ativo");
    montarGrupoFiltros(clienteContainer, ["Cliente", "Nao Cliente"], "cliente");
    montarGrupoFiltros(fornecedorContainer, ["Fornecedor", "Nao Fornecedor"], "fornecedor");
    montarGrupoFiltros(transportadoraContainer, ["Transportadora", "Nao Transportadora"], "transportadora");
    montarGrupoFiltros(descricaoPerfilContainer, valoresUnicosOrdenados("descricao_perfil", "<SEM DESCRICAO>"), "descricao_perfil");
    montarGrupoFiltros(
        anoCadastroContainer,
        valoresUnicosOrdenados("ano_cadastro", "<SEM ANO>", function (a, b) {
            if (a === "<SEM ANO>") return 1;
            if (b === "<SEM ANO>") return -1;
            return Number(b) - Number(a);
        }),
        "ano_cadastro"
    );

    limparBtn.addEventListener("click", function () {
        filtrosSelecionados = criarEstadoSelecao();
        document.querySelectorAll(".carteira-filtro-btn.is-active").forEach(function (btn) {
            btn.classList.remove("is-active");
        });
        tabela.clearFilter(true);
        tabela.clearHeaderFilter();
    });

    tabela.on("tableBuilt", atualizarDashboardComDadosVisiveis);
    tabela.on("dataLoaded", atualizarDashboardComDadosVisiveis);
    tabela.on("renderComplete", atualizarDashboardComDadosVisiveis);
    tabela.on("dataFiltered", atualizarDashboardComDadosVisiveis);
    setTimeout(atualizarDashboardComDadosVisiveis, 0);
})();


