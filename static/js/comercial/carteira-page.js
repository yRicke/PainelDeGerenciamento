(function () {
    var chartContainer = document.getElementById("carteira-dashboard-chart");
    if (!chartContainer || !window.ApexCharts) return;

    var nomesMeses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });

    function parseDataCadastroBr(value) {
        var raw = String(value || "").trim();
        if (!raw) return null;
        var match = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        if (!match) return null;
        var mes = parseInt(match[2], 10);
        var ano = parseInt(match[3], 10);
        if (!ano || mes < 1 || mes > 12) return null;
        return {mes: mes, ano: ano};
    }

    function montarSeriesPorRegistros(registros) {
        var mapa = {};

        (Array.isArray(registros) ? registros : []).forEach(function (item) {
            var dataParts = parseDataCadastroBr(item && item.data_cadastro);
            if (!dataParts) return;

            var chave = String(dataParts.ano) + "-" + String(dataParts.mes).padStart(2, "0");
            if (!mapa[chave]) {
                mapa[chave] = {ano: dataParts.ano, mes: dataParts.mes, qtd: 0, valor: 0};
            }
            mapa[chave].qtd += 1;
            mapa[chave].valor += Number(item && item.valor_faturado || 0);
        });

        var chaves = Object.keys(mapa).sort();
        var categorias = [];
        var qtdCadastramentos = [];
        var valorFaturado = [];

        chaves.forEach(function (chave) {
            var item = mapa[chave];
            categorias.push(nomesMeses[item.mes - 1] + "/" + String(item.ano));
            qtdCadastramentos.push(parseInt(item.qtd || 0, 10));
            valorFaturado.push(Number(item.valor || 0));
        });

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

    function buildYAxis(yMaxQtd, yMaxValor) {
        return [
            {
                seriesName: "Qtd Cadastramentos",
                min: 0,
                max: yMaxQtd,
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
                max: yMaxValor,
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
        ];
    }

    var dadosIniciais = montarSeriesPorRegistros([]);

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
        yaxis: buildYAxis(dadosIniciais.yMaxQtd, dadosIniciais.yMaxValor),
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

    function atualizarGraficoPorRegistros(registros) {
        var dados = montarSeriesPorRegistros(registros);
        chart.updateOptions({
            labels: dados.categorias,
            xaxis: {categories: dados.categorias},
            yaxis: buildYAxis(dados.yMaxQtd, dados.yMaxValor),
        });
        chart.updateSeries([
            {name: "Qtd Cadastramentos", type: "column", data: dados.qtdCadastramentos},
            {name: "Valor Faturado", type: "line", data: dados.valorFaturado},
        ]);
    }

    chart.render();
    window.CarteiraDashboardChart = {
        atualizarPorRegistros: atualizarGraficoPorRegistros,
    };
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

        var replaceCurrentFileMessage = confirmText.replaceCurrentFile || "Ja existe um arquivo na pasta. Deseja substituir o arquivo atual?";
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

    function formatTextoOuVazio(valor) {
        var texto = String(valor || "").trim();
        return texto || "(Vazio)";
    }

    function formatBooleanOuVazio(valor) {
        if (valor === true) return "Sim";
        if (valor === false) return "Nao";
        return "(Vazio)";
    }

    function ordenarTexto(a, b) {
        return String(a.label || "").localeCompare(String(b.label || ""), "pt-BR", {
            sensitivity: "base",
            numeric: true,
        });
    }

    function ordenarBooleanSimNao(a, b) {
        var ordem = {"Sim": 0, "Nao": 1, "(Vazio)": 2};
        var ordemA = Object.prototype.hasOwnProperty.call(ordem, a.label) ? ordem[a.label] : 99;
        var ordemB = Object.prototype.hasOwnProperty.call(ordem, b.label) ? ordem[b.label] : 99;
        if (ordemA !== ordemB) return ordemA - ordemB;
        return ordenarTexto(a, b);
    }

    function classificarIntervaloDiasSemVenda(valorDias) {
        if (typeof valorDias === "string") {
            var texto = valorDias.trim().toLowerCase();
            if (!texto) return "";
            if (texto === "sem venda") return "Sem venda";
            if (texto === "180+" || texto === "180 +" || texto === "180 ou mais") return "180+";
            if (/^\d+\s*a\s*\d+$/.test(texto)) {
                return texto.replace(/\s+/g, " ").replace("a", " a ").replace(/\s+/g, " ").trim();
            }
            var numeroTexto = Number(texto.replace(",", "."));
            if (!Number.isNaN(numeroTexto)) {
                valorDias = numeroTexto;
            } else {
                return "";
            }
        }

        if (typeof valorDias !== "number" || !Number.isFinite(valorDias) || valorDias < 0) {
            return "";
        }
        if (valorDias <= 5) return "0 a 5";
        if (valorDias <= 30) return "6 a 30";
        if (valorDias <= 60) return "31 a 60";
        if (valorDias <= 90) return "61 a 90";
        if (valorDias <= 120) return "91 a 120";
        if (valorDias <= 180) return "121 a 180";
        return "180+";
    }

    function ordenarIntervaloSemVenda(a, b) {
        var ordem = {
            "0 a 5": 0,
            "6 a 30": 1,
            "31 a 60": 2,
            "61 a 90": 3,
            "91 a 120": 4,
            "121 a 180": 5,
            "180+": 6,
            "Sem venda": 7,
            "(Vazio)": 8,
        };
        var ordemA = Object.prototype.hasOwnProperty.call(ordem, a.label) ? ordem[a.label] : 99;
        var ordemB = Object.prototype.hasOwnProperty.call(ordem, b.label) ? ordem[b.label] : 99;
        if (ordemA !== ordemB) return ordemA - ordemB;
        return ordenarTexto(a, b);
    }

    function ensureFilterColumns(section) {
        if (!section) return null;

        var left = section.querySelector('[data-module-filter-column="left"]')
            || section.querySelector("#carteira-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#carteira-filtros-coluna-direita");

        if (left && right) {
            return {left: left, right: right};
        }

        var wrapper = section.querySelector(".module-filter-columns");
        if (!wrapper) {
            wrapper = document.createElement("div");
            wrapper.className = "module-filter-columns";
            section.appendChild(wrapper);
        }

        if (!left) {
            left = document.createElement("div");
            left.className = "module-filter-column";
            left.setAttribute("data-module-filter-column", "left");
            left.id = "carteira-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "carteira-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    function obterLinhasAtivasTabela() {
        var linhasAtivas = tabela.getData("active");
        if (!Array.isArray(linhasAtivas)) {
            linhasAtivas = tabela.getData();
        }
        if (!Array.isArray(linhasAtivas)) {
            linhasAtivas = data;
        }
        return linhasAtivas;
    }

    function atualizarDashboardComDadosVisiveis() {
        var linhasAtivas = obterLinhasAtivasTabela();
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
        if (
            window.CarteiraDashboardChart
            && typeof window.CarteiraDashboardChart.atualizarPorRegistros === "function"
        ) {
            window.CarteiraDashboardChart.atualizarPorRegistros(linhasAtivas);
        }
    }

    var colunas = [
        {title: "Regiao", field: "regiao_codigo", headerFilter: "input"},
        {title: "Nome da Regiao", field: "regiao_nome", headerFilter: "input"},
        {title: "Nome da Cidade", field: "cidade_nome", headerFilter: "input"},
        {
            title: "Valor Faturado",
            field: "valor_faturado",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2},
        },
        {
            title: "Limite de Credito",
            field: "limite_credito",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2},
        },
        {title: "Ultima Venda", field: "ultima_venda", headerFilter: "input"},
        {title: "Dias sem Venda", field: "qtd_dias_sem_venda", hozAlign: "center", headerFilter: "input"},
        {title: "Intervalo", field: "intervalo"},
        {
            title: "Ano de Cadastro",
            field: "ano_cadastro",
            headerFilter: "input",
            visible: false,
            externalFilter: true,
        },
        {title: "Data de Cadastro", field: "data_cadastro", headerFilter: "input"},
        {title: "Gerente", field: "gerente", headerFilter: "input"},
        {title: "Apelido (Vendedor)", field: "vendedor", headerFilter: "input"},
        {title: "Descricao do Perfil", field: "descricao_perfil", headerFilter: "input"},
        {title: "Nome do Parceiro", field: "nome_parceiro", headerFilter: "input"},
        {title: "Ativo", field: "ativo_indicador", hozAlign: "center", headerFilter: "tickCross", formatter: "tickCross"},
        {title: "Cliente", field: "cliente_indicador", hozAlign: "center", headerFilter: "tickCross", formatter: "tickCross"},
        {title: "Fornecedor", field: "fornecedor_indicador", hozAlign: "center", headerFilter: "tickCross", formatter: "tickCross"},
        {title: "Transportadora", field: "transporte_indicador", hozAlign: "center", headerFilter: "tickCross", formatter: "tickCross"},
        {title: "Codigo da Cidade", field: "cidade_codigo", headerFilter: "input"},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data);

    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros) {
        secFiltros.dataset.moduleFiltersAuto = "off";
    }

    var tabela = window.TabulatorDefaults.create("#carteira-tabulator", {
        data: data,
        columns: colunas,
    });
    var filtrosExternos = null;

    if (window.ModuleFilterCore && secFiltros) {
        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholderFiltros = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholderFiltros) placeholderFiltros.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (filtroColumns && filtroColumns.left && filtroColumns.right) {
            filtrosExternos = window.ModuleFilterCore.create({
                data: data,
                definitions: [
                    {
                        key: "gerente",
                        label: "Gerente",
                        singleSelect: true,
                        extractValue: function (rowData) { return rowData ? rowData.gerente : ""; },
                        formatValue: formatTextoOuVazio,
                        sortOptions: ordenarTexto,
                    },
                    {
                        key: "vendedor",
                        label: "Vendedor",
                        singleSelect: true,
                        extractValue: function (rowData) { return rowData ? rowData.vendedor : ""; },
                        formatValue: formatTextoOuVazio,
                        sortOptions: ordenarTexto,
                    },
                    {
                        key: "ativo_indicador",
                        label: "Ativo",
                        singleSelect: true,
                        extractValue: function (rowData) { return rowData ? rowData.ativo_indicador : ""; },
                        formatValue: formatBooleanOuVazio,
                        sortOptions: ordenarBooleanSimNao,
                    },
                    {
                        key: "cliente_indicador",
                        label: "Cliente",
                        singleSelect: true,
                        extractValue: function (rowData) { return rowData ? rowData.cliente_indicador : ""; },
                        formatValue: formatBooleanOuVazio,
                        sortOptions: ordenarBooleanSimNao,
                    },
                    {
                        key: "fornecedor_indicador",
                        label: "Fornecedor",
                        singleSelect: true,
                        extractValue: function (rowData) { return rowData ? rowData.fornecedor_indicador : ""; },
                        formatValue: formatBooleanOuVazio,
                        sortOptions: ordenarBooleanSimNao,
                    },
                    {
                        key: "transporte_indicador",
                        label: "Transportadora",
                        singleSelect: true,
                        extractValue: function (rowData) { return rowData ? rowData.transporte_indicador : ""; },
                        formatValue: formatBooleanOuVazio,
                        sortOptions: ordenarBooleanSimNao,
                    },
                    {
                        key: "intervalo",
                        label: "Intervalo",
                        singleSelect: true,
                        extractValue: function (rowData) {
                            if (!rowData) return "";
                            if (rowData.intervalo) return classificarIntervaloDiasSemVenda(rowData.intervalo);
                            return classificarIntervaloDiasSemVenda(rowData.qtd_dias_sem_venda);
                        },
                        formatValue: formatTextoOuVazio,
                        sortOptions: ordenarIntervaloSemVenda,
                    },
                    {
                        key: "descricao_perfil",
                        label: "Descricao (Perfil)",
                        singleSelect: true,
                        extractValue: function (rowData) { return rowData ? rowData.descricao_perfil : ""; },
                        formatValue: formatTextoOuVazio,
                        sortOptions: ordenarTexto,
                    },
                    {
                        key: "ano_cadastro",
                        label: "Ano Cadastro",
                        singleSelect: true,
                        extractValue: function (rowData) { return rowData ? rowData.ano_cadastro : ""; },
                        formatValue: formatTextoOuVazio,
                        sortOptions: function (a, b) {
                            return Number(b.value || 0) - Number(a.value || 0);
                        },
                    },
                ],
                leftColumn: filtroColumns.left,
                rightColumn: filtroColumns.right,
                onChange: function () {
                    if (typeof tabela.refreshFilter === "function") {
                        tabela.refreshFilter();
                    }
                },
            });

            tabela.addFilter(function (rowData) {
                return filtrosExternos.matchesRecord(rowData);
            });
        }
    }

    function limparTodosFiltros() {
        if (filtrosExternos && typeof filtrosExternos.clearAllFilters === "function") {
            filtrosExternos.clearAllFilters();
        }
        if (typeof tabela.clearHeaderFilter === "function") {
            tabela.clearHeaderFilter();
        }
        if (typeof tabela.refreshFilter === "function") {
            tabela.refreshFilter();
        }
    }

    var limparFiltrosSidebarBtn = secFiltros ? secFiltros.querySelector(".module-filters-clear-all") : null;
    var limparFiltrosToolbarBtn = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
    if (limparFiltrosSidebarBtn) {
        limparFiltrosSidebarBtn.addEventListener("click", limparTodosFiltros);
    }
    if (limparFiltrosToolbarBtn) {
        limparFiltrosToolbarBtn.addEventListener("click", limparTodosFiltros);
    }

    ["tableBuilt", "dataLoaded", "renderComplete", "dataFiltered"].forEach(function (eventName) {
        tabela.on(eventName, atualizarDashboardComDadosVisiveis);
    });
    setTimeout(atualizarDashboardComDadosVisiveis, 0);
})();
