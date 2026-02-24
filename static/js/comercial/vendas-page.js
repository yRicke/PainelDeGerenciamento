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
    if (!dataElement || !window.ApexCharts) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    if (!data.length) return;

    var anosContainer = document.getElementById("dashboard-vendas-ano-container");
    var mesesContainer = document.getElementById("dashboard-vendas-mes-container");
    var diasContainer = document.getElementById("dashboard-vendas-dia-container");
    var limparFiltrosDashboardBtn = document.getElementById("dashboard-vendas-limpar-filtros");
    if (!anosContainer || !mesesContainer || !diasContainer) return;

    var kpiVendasEl = document.getElementById("dashboard-kpi-vendas");
    var kpiCmvEl = document.getElementById("dashboard-kpi-cmv");
    var kpiLucroEl = document.getElementById("dashboard-kpi-lucro");
    var kpiMargemEl = document.getElementById("dashboard-kpi-margem");

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

    var estado = {
        anoSelecionado: null,
        mesesSelecionados: [],
        diasSelecionados: []
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

    function obterAnosDisponiveis() {
        return Array.from(new Set(data.map(function (item) { return item.ano_venda; }).filter(Boolean))).sort(function (a, b) { return b - a; });
    }

    function obterMesesDoAno(ano) {
        if (ano === null || ano === undefined || ano === "") {
            return Array.from(
                new Set(
                    data
                        .map(function (item) { return item.mes_venda; })
                        .filter(Boolean)
                )
            ).sort(function (a, b) { return a - b; });
        }
        return Array.from(
            new Set(
                data
                    .filter(function (item) { return Number(item.ano_venda) === Number(ano); })
                    .map(function (item) { return item.mes_venda; })
                    .filter(Boolean)
            )
        ).sort(function (a, b) { return a - b; });
    }

    function obterDiasFiltrados(ano, mesesSelecionados) {
        var conjuntoMes = new Set(mesesSelecionados.map(Number));
        return Array.from(
            new Set(
                data
                    .filter(function (item) {
                        var bateAno = (ano === null || ano === undefined || ano === "")
                            ? true
                            : Number(item.ano_venda) === Number(ano);
                        return bateAno && conjuntoMes.has(Number(item.mes_venda));
                    })
                    .map(function (item) { return item.data_venda_iso || ""; })
                    .filter(Boolean)
            )
        ).sort();
    }

    function criarChip(label, ativo, onClick) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "dashboard-chip" + (ativo ? " is-active" : "");
        btn.textContent = label;
        btn.addEventListener("click", onClick);
        return btn;
    }

    function renderAnos() {
        var anos = obterAnosDisponiveis();
        if (!anos.length) return;

        if (estado.anoSelecionado !== null && anos.indexOf(Number(estado.anoSelecionado)) < 0) {
            estado.anoSelecionado = null;
        }

        anosContainer.innerHTML = "";
        anosContainer.appendChild(criarChip("Todos", estado.anoSelecionado === null, function () {
            estado.anoSelecionado = null;
            estado.mesesSelecionados = obterMesesDoAno(estado.anoSelecionado);
            estado.diasSelecionados = obterDiasFiltrados(estado.anoSelecionado, estado.mesesSelecionados);
            renderTudo();
        }));

        anos.forEach(function (ano) {
            anosContainer.appendChild(criarChip(String(ano), Number(estado.anoSelecionado) === Number(ano), function () {
                estado.anoSelecionado = ano;
                var mesesAno = obterMesesDoAno(estado.anoSelecionado);
                estado.mesesSelecionados = mesesAno.slice();
                var dias = obterDiasFiltrados(estado.anoSelecionado, estado.mesesSelecionados);
                estado.diasSelecionados = dias.slice();
                renderTudo();
            }));
        });
    }

    function renderMeses() {
        var mesesAno = obterMesesDoAno(estado.anoSelecionado);
        if (!estado.mesesSelecionados.length) {
            estado.mesesSelecionados = mesesAno.slice();
        }
        estado.mesesSelecionados = estado.mesesSelecionados.filter(function (mes) { return mesesAno.indexOf(Number(mes)) >= 0; });
        if (!estado.mesesSelecionados.length && mesesAno.length) {
            estado.mesesSelecionados = mesesAno.slice();
        }

        mesesContainer.innerHTML = "";
        mesesAno.forEach(function (mes) {
            var ativo = estado.mesesSelecionados.indexOf(Number(mes)) >= 0;
            mesesContainer.appendChild(criarChip(nomeMes[mes] || String(mes), ativo, function () {
                if (ativo && estado.mesesSelecionados.length > 1) {
                    estado.mesesSelecionados = estado.mesesSelecionados.filter(function (m) { return Number(m) !== Number(mes); });
                } else if (!ativo) {
                    estado.mesesSelecionados.push(Number(mes));
                    estado.mesesSelecionados.sort(function (a, b) { return a - b; });
                }
                var diasAtualizados = obterDiasFiltrados(estado.anoSelecionado, estado.mesesSelecionados);
                estado.diasSelecionados = estado.diasSelecionados.filter(function (dia) { return diasAtualizados.indexOf(dia) >= 0; });
                if (!estado.diasSelecionados.length) {
                    estado.diasSelecionados = diasAtualizados.slice();
                }
                renderTudo();
            }));
        });
    }

    function renderDias() {
        var diasDisponiveis = obterDiasFiltrados(estado.anoSelecionado, estado.mesesSelecionados);
        if (!estado.diasSelecionados.length) {
            estado.diasSelecionados = diasDisponiveis.slice();
        }
        estado.diasSelecionados = estado.diasSelecionados.filter(function (dia) { return diasDisponiveis.indexOf(dia) >= 0; });
        if (!estado.diasSelecionados.length && diasDisponiveis.length) {
            estado.diasSelecionados = diasDisponiveis.slice();
        }

        diasContainer.innerHTML = "";
        diasDisponiveis.forEach(function (diaIso) {
            var partes = diaIso.split("-");
            var rotulo = (partes[2] || "") + "/" + (partes[1] || "");
            var ativo = estado.diasSelecionados.indexOf(diaIso) >= 0;
            diasContainer.appendChild(criarChip(rotulo, ativo, function () {
                if (ativo && estado.diasSelecionados.length > 1) {
                    estado.diasSelecionados = estado.diasSelecionados.filter(function (dia) { return dia !== diaIso; });
                } else if (!ativo) {
                    estado.diasSelecionados.push(diaIso);
                    estado.diasSelecionados.sort();
                }
                renderTudo();
            }));
        });
    }

    function filtrarRegistros() {
        var conjuntoMes = new Set(estado.mesesSelecionados.map(Number));
        var conjuntoDia = new Set(estado.diasSelecionados);
        return data.filter(function (item) {
            var bateAno = (estado.anoSelecionado === null || estado.anoSelecionado === undefined || estado.anoSelecionado === "")
                ? true
                : Number(item.ano_venda) === Number(estado.anoSelecionado);
            return bateAno
                && conjuntoMes.has(Number(item.mes_venda))
                && conjuntoDia.has(item.data_venda_iso || "");
        });
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
            var desc = (item.descricao || "").trim() || ("Codigo " + (item.codigo || "-"));
            if (!mapa[desc]) mapa[desc] = 0;
            mapa[desc] += Number(item.valor_venda || 0);
        });
        var ranking = Object.keys(mapa).map(function (nome) {
            return {nome: nome, valor: mapa[nome]};
        }).sort(function (a, b) { return b.valor - a.valor; }).slice(0, 10);
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

    var chartDia = new ApexCharts(document.getElementById("dashboard-vendas-dia-chart"), {
        chart: {type: "line", height: 320, toolbar: {show: true}},
        series: [],
        stroke: {curve: "smooth", width: [3, 3, 3, 2]},
        colors: ["#176087", "#ef8636", "#2f9e44", "#748ffc"],
        xaxis: {categories: []},
        yaxis: {labels: {formatter: function (v) { return fmtMoeda(v); }}},
        tooltip: {shared: true, intersect: false, y: {formatter: function (v) { return fmtMoeda(v); }}}
    });
    chartDia.render();

    var chartMes = new ApexCharts(document.getElementById("dashboard-vendas-mes-chart"), {
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

    var chartTop10 = new ApexCharts(document.getElementById("dashboard-vendas-top10-chart"), {
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

    var chartMargens = new ApexCharts(document.getElementById("dashboard-vendas-margens-chart"), {
        chart: {type: "donut", height: 320},
        series: [0, 0, 0, 0],
        labels: ["Amarelo (12-13,99%)", "Roxo (< 10%)", "Verde (>= 14%)", "Vermelho (10-11,99%)"],
        colors: ["#f4b000", "#8e24aa", "#2f9e44", "#e74c3c"],
        legend: {position: "bottom"},
        tooltip: {y: {formatter: function (v) { return String(v) + " registros"; }}}
    });
    chartMargens.render();

    function atualizarDashboard() {
        var registros = filtrarRegistros();

        var totalVendas = registros.reduce(function (acc, item) { return acc + Number(item.valor_venda || 0); }, 0);
        var totalCmv = registros.reduce(function (acc, item) { return acc + Number(item.custo_medio_icms_cmv || 0); }, 0);
        var totalLucro = registros.reduce(function (acc, item) { return acc + Number(item.lucro || 0); }, 0);
        var margemGeral = totalVendas > 0 ? (totalLucro / totalVendas) * 100 : 0;

        kpiVendasEl.textContent = fmtMoeda(totalVendas);
        kpiCmvEl.textContent = fmtMoeda(totalCmv);
        kpiLucroEl.textContent = fmtMoeda(totalLucro);
        kpiMargemEl.textContent = fmtPercent(margemGeral);

        var dia = agruparPorDia(registros);
        chartDia.updateOptions({xaxis: {categories: dia.categorias}});
        chartDia.updateSeries([
            {name: "Vlr Vendas", data: dia.vendas},
            {name: "Vlr Custo Med Com ICMS (CMV)", data: dia.cmv},
            {name: "Vlr Lucro Bruto", data: dia.lucro},
            {name: "Linha de Meta", data: dia.meta}
        ]);

        var mes = agruparPorMes(registros);
        chartMes.updateOptions({xaxis: {categories: mes.categorias}});
        chartMes.updateSeries([{name: "Vendas", data: mes.valores}]);

        var top10 = top10Produtos(registros);
        chartTop10.updateOptions({xaxis: {categories: top10.categorias}});
        chartTop10.updateSeries([{name: "Vendas", data: top10.valores}]);

        chartMargens.updateSeries(distribuicaoMargens(registros));
    }

    function renderTudo() {
        renderAnos();
        renderMeses();
        renderDias();
        atualizarDashboard();
    }

    function resetarFiltrosDashboard() {
        estado.anoSelecionado = null;
        estado.mesesSelecionados = obterMesesDoAno(estado.anoSelecionado);
        estado.diasSelecionados = obterDiasFiltrados(estado.anoSelecionado, estado.mesesSelecionados);
        renderTudo();
    }

    if (limparFiltrosDashboardBtn) {
        limparFiltrosDashboardBtn.addEventListener("click", function () {
            resetarFiltrosDashboard();
        });
    }

    estado.anoSelecionado = null;
    estado.mesesSelecionados = obterMesesDoAno(estado.anoSelecionado);
    estado.diasSelecionados = obterDiasFiltrados(estado.anoSelecionado, estado.mesesSelecionados);
    renderTudo();
})();

(function () {
    var dataElement = document.getElementById("vendas-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var situacaoMargemSelect = document.getElementById("filtro-situacao-margem-tabela");
    var anoVendaSelect = document.getElementById("filtro-ano-venda-tabela");
    var mesVendaSelect = document.getElementById("filtro-mes-venda-tabela");
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

    var colunas = [
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
    ];

    if (data.some(function (item) { return Boolean(item.editar_url); })) {
        colunas.push({
            title: "Acoes",
            field: "editar_url",
            formatter: function (cell) {
                var url = cell.getValue();
                return url ? '<a class="btn-primary" href="' + url + '">Editar</a>' : "";
            },
            hozAlign: "center"
        });
    }

    var tabela = window.TabulatorDefaults.create("#vendas-tabulator", {
        data: data,
        layout: "fitDataTable",
        pagination: true,
        paginationSize: 100,
        columns: colunas
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


