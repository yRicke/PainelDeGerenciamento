(function () {
    var form = document.getElementById("upload-vendas-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-vendas");
    var input = document.getElementById("arquivos-vendas-input");
    var statusArquivos = document.getElementById("nome-arquivos-vendas-selecionados");
    var loadingStatus = document.getElementById("vendas-loading-status");
    if (!dropzone || !input) return;
    var frontendText = window.FrontendText || {};
    var uploadText = frontendText.upload || {};
    var arquivoXlsLabel = ".xls";

    function mensagemNenhumArquivoEncontrado() {
        if (typeof uploadText.noFileFound === "function") {
            return uploadText.noFileFound(arquivoXlsLabel);
        }
        return "Nenhum arquivo .xls encontrado.";
    }

    function mensagemSelecionarPastaParaContinuar() {
        if (typeof uploadText.selectFolderToContinue === "function") {
            return uploadText.selectFolderToContinue(arquivoXlsLabel);
        }
        return "Selecione uma pasta com arquivos .xls para continuar.";
    }

    function iniciarCarregamento() {
        form.classList.add("is-loading");
        if (loadingStatus) loadingStatus.classList.add("is-visible");
    }

    function coletarArquivosXls(files) {
        if (!files || !files.length) return [];
        return Array.from(files).filter(function (file) {
            return file && file.name && file.name.toLowerCase().endsWith(".xls");
        });
    }

    function atualizarStatus(filesXls) {
        if (!statusArquivos) return;
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
            window.alert(mensagemNenhumArquivoEncontrado());
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
            window.alert(mensagemSelecionarPastaParaContinuar());
            return;
        }
        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("vendas-tabulator-data");
    if (!dataElement) return;
    if (!window.Tabulator || !window.TabulatorDefaults) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    if (!document.getElementById("vendas-tabulator")) return;

    var kpiVendasEl = document.getElementById("dashboard-kpi-vendas");
    var kpiCmvEl = document.getElementById("dashboard-kpi-cmv");
    var kpiLucroEl = document.getElementById("dashboard-kpi-lucro");
    var kpiMargemEl = document.getElementById("dashboard-kpi-margem");

    var limparFiltrosBtn = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
    var limparFiltrosSidebarBtn = document.getElementById("vendas-limpar-filtros-sidebar");
    var filtroColunaEsquerda = document.getElementById("vendas-filtros-coluna-esquerda");
    var filtroColunaDireita = document.getElementById("vendas-filtros-coluna-direita");

    var nomeMes = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
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

    function fmtMoeda(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            style: "currency",
            currency: "BRL",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function fmtNumero(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function fmtPercent(valor) {
        return fmtNumero(valor) + "%";
    }

    function normalizarSituacaoMargem(valor) {
        return String(valor || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();
    }

    function obterCorMargemPorSituacao(situacaoMargem) {
        var situacao = normalizarSituacaoMargem(situacaoMargem);
        if (situacao === "roxo") return "#8e24aa";
        if (situacao === "vermelho") return "#e74c3c";
        if (situacao === "amarelo") return "#b37f00";
        if (situacao === "verde") return "#2f9e44";
        return "";
    }

    function isoParaDataBr(iso) {
        var texto = String(iso || "").trim();
        if (!texto) return "(Vazio)";
        var partes = texto.split("-");
        if (partes.length !== 3) return texto;
        return partes[2] + "/" + partes[1] + "/" + partes[0];
    }

    function removerTagsHtml(valor) {
        return String(valor || "").replace(/<[^>]+>/g, "").trim();
    }

    function isCurrencyField(field) {
        return (
            field.indexOf("valor_") === 0
            || field.indexOf("custo_") === 0
            || field.indexOf("remuneracao") === 0
            || field === "lucro"
        );
    }

    function isPercentField(field) {
        return field === "margem";
    }

    function formatarFiltroPorCampo(field, value) {
        if (value === null || value === undefined || value === "") return "(Vazio)";

        if (field === "mes_venda") {
            var mesNumero = Number(value || 0);
            return nomeMes[mesNumero] || String(value);
        }

        if (field === "data_venda_iso") {
            return isoParaDataBr(value);
        }

        if (field === "ano_venda") {
            return String(value);
        }

        if (typeof value === "number" && Number.isFinite(value)) {
            if (isPercentField(field)) return fmtPercent(value);
            if (isCurrencyField(field)) return fmtMoeda(value);
            return fmtNumero(value);
        }

        return String(value);
    }

    function criarDefinicoesFiltro(colunasTabulator) {
        var definicoes = [
            {
                key: "ano_venda",
                label: "Ano da Venda",
                formatValue: function (value) {
                    return formatarFiltroPorCampo("ano_venda", value);
                },
                sortOptions: function (a, b) {
                    return Number(b.value || 0) - Number(a.value || 0);
                }
            },
            {
                key: "mes_venda",
                label: "Mês da Venda",
                formatValue: function (value) {
                    return formatarFiltroPorCampo("mes_venda", value);
                },
                sortOptions: function (a, b) {
                    return Number(a.value || 0) - Number(b.value || 0);
                }
            },
            {
                key: "data_venda_iso",
                label: "Data da Venda",
                formatValue: function (value) {
                    return formatarFiltroPorCampo("data_venda_iso", value);
                }
            },
            {
                key: "margem_situacao",
                label: "Situação da Margem",
                formatValue: function (value) {
                    return formatarFiltroPorCampo("margem_situacao", value);
                }
            }
        ];

        var camposJaIncluidos = new Set(definicoes.map(function (definicao) { return definicao.key; }));

        (colunasTabulator || []).forEach(function (coluna) {
            if (!coluna || !coluna.field) return;
            var field = String(coluna.field || "").trim();
            if (!field || field.indexOf("_url") >= 0) return;
            if (camposJaIncluidos.has(field)) return;

            var titulo = removerTagsHtml(coluna.title || field);
            definicoes.push({
                key: field,
                label: titulo || field,
                formatValue: function (value) {
                    return formatarFiltroPorCampo(field, value);
                }
            });
            camposJaIncluidos.add(field);
        });

        return definicoes;
    }

    function agruparPorDia(registros) {
        var mapa = {};
        registros.forEach(function (item) {
            var dia = item.data_venda_iso || "";
            if (!dia) return;
            if (!mapa[dia]) {
                mapa[dia] = {vendas: 0, cmv: 0, lucro: 0};
            }
            mapa[dia].vendas += Number(item.valor_venda || 0);
            mapa[dia].cmv += Number(item.custo_medio_icms_cmv || 0);
            mapa[dia].lucro += Number(item.lucro || 0);
        });

        var dias = Object.keys(mapa).sort();
        return {
            categorias: dias.map(function (iso) {
                var p = iso.split("-");
                return (p[2] || "") + "/" + (p[1] || "");
            }),
            vendas: dias.map(function (iso) { return Number(mapa[iso].vendas.toFixed(2)); }),
            cmv: dias.map(function (iso) { return Number(mapa[iso].cmv.toFixed(2)); }),
            lucro: dias.map(function (iso) { return Number(mapa[iso].lucro.toFixed(2)); }),
            meta: dias.map(function (iso) { return Number((mapa[iso].vendas * 0.14).toFixed(2)); })
        };
    }

    function agruparPorMes(registros) {
        var mapa = {};
        registros.forEach(function (item) {
            var mes = Number(item.mes_venda || 0);
            if (!mes) return;
            if (!mapa[mes]) mapa[mes] = 0;
            mapa[mes] += Number(item.valor_venda || 0);
        });

        var meses = Object.keys(mapa).map(Number).sort(function (a, b) { return a - b; });
        return {
            categorias: meses.map(function (mes) { return nomeMes[mes] || String(mes); }),
            valores: meses.map(function (mes) { return Number(mapa[mes].toFixed(2)); })
        };
    }

    function top10Produtos(registros) {
        var mapa = {};
        registros.forEach(function (item) {
            var desc = (item.descricao || "").trim() || ("Código " + (item.codigo || "-"));
            if (!mapa[desc]) mapa[desc] = 0;
            mapa[desc] += Number(item.valor_venda || 0);
        });

        var ranking = Object.keys(mapa)
            .map(function (nome) {
                return {nome: nome, valor: mapa[nome]};
            })
            .sort(function (a, b) { return b.valor - a.valor; })
            .slice(0, 10);

        return {
            categorias: ranking.map(function (item) { return item.nome; }),
            valores: ranking.map(function (item) { return Number(item.valor.toFixed(2)); })
        };
    }

    function distribuicaoMargens(registros) {
        var contagem = {Roxo: 0, Vermelho: 0, Amarelo: 0, Verde: 0};
        registros.forEach(function (item) {
            var margem = Number(item.margem || 0);
            if (margem < 10) contagem.Roxo += 1;
            else if (margem < 12) contagem.Vermelho += 1;
            else if (margem < 14) contagem.Amarelo += 1;
            else contagem.Verde += 1;
        });
        return [contagem.Amarelo, contagem.Roxo, contagem.Verde, contagem.Vermelho];
    }

    var colunas = [
        {
            title: "Data da Venda",
            field: "data_venda",
            headerFilter: "input",
            sorter: function (a, b, aRow, bRow) {
                var dataA = aRow.getData().data_venda_iso || "";
                var dataB = bRow.getData().data_venda_iso || "";
                if (dataA === dataB) return 0;
                return dataA > dataB ? 1 : -1;
            }
        },
        {title: "Código", field: "codigo", headerFilter: "input"},
        {title: "Descrição", field: "descricao", headerFilter: "input"},
        {
            title: "Valor de Vendas",
            field: "valor_venda",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2}
        },
        {title: "Quantidade de Notas", field: "qtd_notas", hozAlign: "center", headerFilter: "input"},
        {
            title: "Custo Médio com ICMS (CMV)",
            field: "custo_medio_icms_cmv",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2}
        },
        {
            title: "Margem",
            field: "margem",
            hozAlign: "right",
            headerFilter: "input",
            formatter: function (cell) {
                var valorFormatado = Number(cell.getValue() || 0).toLocaleString("pt-BR", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                }) + "%";
                var rowData = cell.getRow() ? cell.getRow().getData() : null;
                var situacaoMargem = rowData ? rowData.margem_situacao : "";
                var cor = obterCorMargemPorSituacao(situacaoMargem);
                if (!cor) return valorFormatado;
                return '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:' + cor + ';color:#fff;font-weight:600;">' + valorFormatado + "</span>";
            }
        },
        {
            title: "Peso Bruto",
            field: "peso_bruto",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "", symbolAfter: false, precision: 2}
        },
        {
            title: "Peso Líquido",
            field: "peso_liquido",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "", symbolAfter: false, precision: 2}
        },
        {
            title: "KG",
            field: "kg",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "", symbolAfter: false, precision: 3}
        },
        {
            title: "Remuneração por Fardo",
            field: "remuneracao_por_fardo",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 3}
        },
        {
            title: "Quantidade de Fardos",
            field: "quantidade_fardos",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "", symbolAfter: false, precision: 3}
        },
        {
            title: "Remuneração Total",
            field: "remuneracao_total",
            hozAlign: "right",
            headerFilter: "input",
            formatter: "money",
            formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2}
        }
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data);

    var tabela = window.TabulatorDefaults.create("#vendas-tabulator", {
        data: data,
        columns: colunas
    });

    var filtrosExternos = null;
    if (window.ModuleFilterCore && filtroColunaEsquerda && filtroColunaDireita) {
        var definicoesFiltro = criarDefinicoesFiltro(colunas);
        filtrosExternos = window.ModuleFilterCore.create({
            data: data,
            definitions: definicoesFiltro,
            leftColumn: filtroColunaEsquerda,
            rightColumn: filtroColunaDireita,
            onChange: function () {
                if (typeof tabela.refreshFilter === "function") {
                    tabela.refreshFilter();
                }
                atualizarDashboardComTabela();
            }
        });

        tabela.addFilter(function (rowData) {
            return filtrosExternos.matchesRecord(rowData);
        });
    }

    var chartDia = null;
    var chartMes = null;
    var chartTop10 = null;
    var chartMargens = null;

    if (window.ApexCharts) {
        chartDia = new ApexCharts(document.getElementById("dashboard-vendas-dia-chart"), {
            chart: {type: "line", height: 320, toolbar: {show: true}},
            series: [],
            stroke: {curve: "smooth", width: [3, 3, 3, 2]},
            colors: ["#176087", "#ef8636", "#2f9e44", "#748ffc"],
            xaxis: {categories: []},
            yaxis: {labels: {formatter: function (v) { return fmtMoeda(v); }}},
            tooltip: {shared: true, intersect: false, y: {formatter: function (v) { return fmtMoeda(v); }}}
        });
        chartDia.render();

        chartMes = new ApexCharts(document.getElementById("dashboard-vendas-mes-chart"), {
            chart: {type: "bar", height: 300, toolbar: {show: false}},
            series: [{name: "Vendas", data: []}],
            plotOptions: {bar: {borderRadius: 6, columnWidth: "48%"}},
            colors: ["#176087"],
            dataLabels: {
                enabled: true,
                formatter: function (v) { return fmtMoeda(v); },
                style: {fontSize: "11px"}
            },
            xaxis: {categories: []},
            yaxis: {labels: {formatter: function (v) { return fmtMoeda(v); }}},
            tooltip: {y: {formatter: function (v) { return fmtMoeda(v); }}}
        });
        chartMes.render();

        chartTop10 = new ApexCharts(document.getElementById("dashboard-vendas-top10-chart"), {
            chart: {type: "bar", height: 360, toolbar: {show: false}},
            series: [{name: "Vendas", data: []}],
            plotOptions: {bar: {horizontal: true, borderRadius: 4}},
            colors: ["#0b7285"],
            dataLabels: {
                enabled: true,
                formatter: function (v) { return fmtMoeda(v); },
                style: {fontSize: "11px"}
            },
            xaxis: {labels: {formatter: function (v) { return fmtMoeda(v); }}},
            tooltip: {y: {formatter: function (v) { return fmtMoeda(v); }}}
        });
        chartTop10.render();

        chartMargens = new ApexCharts(document.getElementById("dashboard-vendas-margens-chart"), {
            chart: {type: "donut", height: 320},
            series: [0, 0, 0, 0],
            labels: ["Amarelo (12-13,99%)", "Roxo (< 10%)", "Verde (>= 14%)", "Vermelho (10-11,99%)"],
            colors: ["#f4b000", "#8e24aa", "#2f9e44", "#e74c3c"],
            legend: {position: "bottom"},
            tooltip: {y: {formatter: function (v) { return String(v) + " registros"; }}}
        });
        chartMargens.render();
    }

    function obterRegistrosAtivos() {
        var linhas = tabela.getData("active");
        if (!Array.isArray(linhas) || !linhas.length) {
            linhas = tabela.getData() || [];
        }
        return linhas;
    }

    function atualizarDashboardComTabela() {
        var registros = obterRegistrosAtivos();

        var totalVendas = registros.reduce(function (acc, item) { return acc + Number(item.valor_venda || 0); }, 0);
        var totalCmv = registros.reduce(function (acc, item) { return acc + Number(item.custo_medio_icms_cmv || 0); }, 0);
        var totalLucro = registros.reduce(function (acc, item) { return acc + Number(item.lucro || 0); }, 0);
        var margemGeral = totalVendas > 0 ? (totalLucro / totalVendas) * 100 : 0;

        if (kpiVendasEl) kpiVendasEl.textContent = fmtMoeda(totalVendas);
        if (kpiCmvEl) kpiCmvEl.textContent = fmtMoeda(totalCmv);
        if (kpiLucroEl) kpiLucroEl.textContent = fmtMoeda(totalLucro);
        if (kpiMargemEl) kpiMargemEl.textContent = fmtPercent(margemGeral);

        var dia = agruparPorDia(registros);
        if (chartDia) {
            chartDia.updateOptions({xaxis: {categories: dia.categorias}});
            chartDia.updateSeries([
                {name: "Valor de Vendas", data: dia.vendas},
                {name: "Valor de CMV (Custo Médio com ICMS)", data: dia.cmv},
                {name: "Valor de Lucro Bruto", data: dia.lucro},
                {name: "Linha de Meta", data: dia.meta}
            ]);
        }

        var mes = agruparPorMes(registros);
        if (chartMes) {
            chartMes.updateOptions({xaxis: {categories: mes.categorias}});
            chartMes.updateSeries([{name: "Vendas", data: mes.valores}]);
        }

        var top10 = top10Produtos(registros);
        if (chartTop10) {
            chartTop10.updateOptions({xaxis: {categories: top10.categorias}});
            chartTop10.updateSeries([{name: "Vendas", data: top10.valores}]);
        }

        if (chartMargens) {
            chartMargens.updateSeries(distribuicaoMargens(registros));
        }
    }

    function limparTodosFiltrosExternos() {
        if (!filtrosExternos) return;
        filtrosExternos.clearAllFilters();
        if (typeof tabela.refreshFilter === "function") {
            tabela.refreshFilter();
        }
        atualizarDashboardComTabela();
    }

    if (limparFiltrosBtn) {
        limparFiltrosBtn.addEventListener("click", limparTodosFiltrosExternos);
    }
    if (limparFiltrosSidebarBtn) {
        limparFiltrosSidebarBtn.addEventListener("click", limparTodosFiltrosExternos);
    }

    tabela.on("tableBuilt", atualizarDashboardComTabela);
    tabela.on("dataLoaded", atualizarDashboardComTabela);
    tabela.on("renderComplete", atualizarDashboardComTabela);
    tabela.on("dataFiltered", atualizarDashboardComTabela);
    setTimeout(atualizarDashboardComTabela, 0);
})();
