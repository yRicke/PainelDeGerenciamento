(function () {
    var form = document.getElementById("upload-producao-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-producao");
    var input = document.getElementById("arquivos-producao-input");
    var fileStatus = document.getElementById("nome-arquivos-producao-selecionado");
    var loadingStatus = document.getElementById("producao-loading-status");

    function iniciarCarregamento() {
        form.classList.add("is-loading");
        loadingStatus.classList.add("is-visible");
    }

    function coletarArquivosXls(files) {
        if (!files || !files.length) return [];
        return Array.from(files).filter(function (file) {
            return file && file.name.toLowerCase().endsWith(".xls");
        });
    }

    function atualizarStatus(filesXls) {
        if (!filesXls.length) {
            fileStatus.textContent = "";
            return;
        }
        fileStatus.textContent = filesXls.length + " arquivo(s) .xls selecionado(s).";
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
    var dataElement = document.getElementById("producao-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var dadosOriginais = Array.isArray(data) ? data.slice() : [];

    var filtroSituacaoContainer = document.getElementById("filtro-situacao-chips");
    var filtroAnoContainer = document.getElementById("filtro-ano-chips");
    var filtroMesContainer = document.getElementById("filtro-mes-chips");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-producao");

    var MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"];
    var METAS = {
        x30x1: 141120,
        x15x2: 141120,
        x6x5: 420000,
        total: 702240,
    };

    var filtrosSelecionados = {
        situacao: new Set(),
        ano: new Set(),
        mes: new Set(),
    };

    function formatNumero(valor) {
        var numero = Number(valor || 0);
        return numero.toLocaleString("pt-BR", {maximumFractionDigits: 0});
    }

    function paraTexto(valor) {
        return String(valor || "").toLowerCase().trim();
    }

    function parseNumeroLote(valor) {
        var texto = String(valor || "").trim();
        if (!texto) return 0;
        texto = texto.replace(/\s/g, "");
        if (texto.indexOf(",") >= 0) {
            texto = texto.replace(/\./g, "").replace(/,/g, ".");
        }
        var num = Number(texto);
        return Number.isFinite(num) ? num : 0;
    }

    function valoresUnicos(campo, parser) {
        var set = new Set();
        dadosOriginais.forEach(function (item) {
            var valor = item[campo];
            if (parser) valor = parser(valor);
            if (valor !== "" && valor !== null && valor !== undefined) {
                set.add(valor);
            }
        });
        return Array.from(set);
    }

    function criarChips(container, valores, chaveFiltro, formatter) {
        if (!container) return;
        container.innerHTML = "";

        valores.forEach(function (valor) {
            var btn = document.createElement("button");
            btn.type = "button";
            btn.className = "filtro-chip is-active";
            btn.dataset.value = String(valor);
            btn.textContent = formatter ? formatter(valor) : String(valor);

            filtrosSelecionados[chaveFiltro].add(String(valor));

            btn.addEventListener("click", function () {
                var token = String(valor);
                if (filtrosSelecionados[chaveFiltro].has(token)) {
                    filtrosSelecionados[chaveFiltro].delete(token);
                    btn.classList.remove("is-active");
                } else {
                    filtrosSelecionados[chaveFiltro].add(token);
                    btn.classList.add("is-active");
                }
                aplicarFiltrosTabela();
            });

            container.appendChild(btn);
        });
    }

    var opcoesSituacao = valoresUnicos("situacao", function (v) { return String(v || "").trim(); })
        .sort(function (a, b) { return a.localeCompare(b, "pt-BR"); });
    var opcoesAno = valoresUnicos("ano_atividade", function (v) { return Number(v || 0); })
        .filter(function (v) { return v > 0; })
        .sort(function (a, b) { return a - b; });
    var opcoesMes = valoresUnicos("mes_atividade", function (v) { return Number(v || 0); })
        .filter(function (v) { return v >= 1 && v <= 12; })
        .sort(function (a, b) { return a - b; });

    criarChips(filtroSituacaoContainer, opcoesSituacao, "situacao");
    criarChips(filtroAnoContainer, opcoesAno, "ano");
    criarChips(filtroMesContainer, opcoesMes, "mes", function (m) { return MESES[m - 1] || String(m); });

    var tabela = new Tabulator("#producao-tabulator", {
        data: dadosOriginais,
        layout: "fitDataTable",
        movableColumns: true,
        pagination: "local",
        paginationSize: 100,
        locale: true,
        langs: {
            "pt-br": {
                pagination: {
                    first: "Primeira",
                    first_title: "Primeira pagina",
                    last: "Ultima",
                    last_title: "Ultima pagina",
                    prev: "Anterior",
                    prev_title: "Pagina anterior",
                    next: "Proxima",
                    next_title: "Proxima pagina"
                }
            }
        },
        columns: [
            { title: "Data Origem", field: "data_origem" },
            { title: "N. Operacao", field: "numero_operacao", hozAlign: "right" },
            { title: "Situacao", field: "situacao" },
            { title: "Cod Produto", field: "produto_codigo" },
            { title: "Desc Produto", field: "produto_descricao" },
            { title: "Tamanho Lote", field: "tamanho_lote" },
            { title: "Numero Lote", field: "numero_lote" },
            { title: "Entrada Atividade", field: "data_hora_entrada_atividade" },
            { title: "Aceite Atividade", field: "data_hora_aceite_atividade" },
            { title: "Inicio Atividade", field: "data_hora_inicio_atividade" },
            { title: "Fim Atividade", field: "data_hora_fim_atividade" },
            { title: "Kg", field: "kg", hozAlign: "right" },
            { title: "Producao Dia (FD)", field: "producao_por_dia", hozAlign: "right" },
            { title: "Kg por Lote", field: "kg_por_lote", hozAlign: "right" },
            {
                title: "Acoes",
                field: "editar_url",
                formatter: function (cell) {
                    var url = cell.getValue();
                    return '<a class="btn-primary" href="' + url + '">Editar</a>';
                },
                hozAlign: "center"
            }
        ]
    });

    function dentroFiltro(setValores, valor) {
        if (!setValores || setValores.size === 0) return true;
        return setValores.has(String(valor));
    }

    function aplicarFiltrosTabela() {
        tabela.setFilter(function (item) {
            var situacaoOk = dentroFiltro(filtrosSelecionados.situacao, String(item.situacao || "").trim());
            var anoOk = dentroFiltro(filtrosSelecionados.ano, Number(item.ano_atividade || 0));
            var mesOk = dentroFiltro(filtrosSelecionados.mes, Number(item.mes_atividade || 0));
            return situacaoOk && anoOk && mesOk;
        });
    }

    if (limparFiltrosBtn) {
        limparFiltrosBtn.addEventListener("click", function () {
            ["situacao", "ano", "mes"].forEach(function (chave) {
                filtrosSelecionados[chave].clear();
            });

            document.querySelectorAll(".filtro-chip").forEach(function (chip) {
                chip.classList.remove("is-active");
            });

            tabela.clearFilter(true);
        });
    }

    function obterCategoriaProduto(desc) {
        var texto = paraTexto(desc).replace(/\s+/g, "");
        if (texto.indexOf("30x1") >= 0) return "x30x1";
        if (texto.indexOf("15x2") >= 0) return "x15x2";
        if (texto.indexOf("6x5") >= 0) return "x6x5";
        return "outras";
    }

    function construirGauge(elementId, meta) {
        if (!window.ApexCharts) return null;
        var el = document.getElementById(elementId);
        if (!el) return null;

        var options = {
            chart: {
                type: "radialBar",
                height: 200,
                sparkline: {enabled: true}
            },
            series: [0],
            plotOptions: {
                radialBar: {
                    startAngle: -90,
                    endAngle: 90,
                    hollow: {size: "55%"},
                    track: {
                        background: "#e8edf2",
                        strokeWidth: "100%"
                    },
                    dataLabels: {
                        name: {show: false},
                        value: {
                            offsetY: -2,
                            fontSize: "22px",
                            formatter: function (val) {
                                return Math.round(val) + "%";
                            }
                        }
                    }
                }
            },
            fill: {
                type: "gradient",
                gradient: {
                    shade: "light",
                    type: "horizontal",
                    shadeIntensity: 0.4,
                    gradientToColors: ["#1f9d55"],
                    inverseColors: false,
                    stops: [0, 35, 70, 100],
                }
            },
            colors: ["#e03131"],
            labels: ["Atingimento"],
            annotations: {
                xaxis: [{
                    x: 50,
                    borderColor: "#333",
                    label: {text: "META " + formatNumero(meta)}
                }]
            }
        };

        var chart = new ApexCharts(el, options);
        chart.render();
        return chart;
    }

    var gauges = {
        x30x1: construirGauge("gauge-producao-30x1", METAS.x30x1),
        x15x2: construirGauge("gauge-producao-15x2", METAS.x15x2),
        x6x5: construirGauge("gauge-producao-6x5", METAS.x6x5),
        total: construirGauge("gauge-producao-total", METAS.total),
    };

    function atualizarLinha(meta, real, ids, gauge) {
        var pct = meta > 0 ? (real / meta) * 100 : 0;
        var pctLimitado = Math.max(0, Math.min(100, pct));

        var realEl = document.getElementById(ids.real);
        var pctEl = document.getElementById(ids.pct);
        if (realEl) realEl.textContent = formatNumero(real);
        if (pctEl) pctEl.textContent = pct.toFixed(2).replace(".", ",") + "%";

        if (gauge) {
            gauge.updateSeries([pctLimitado]);
        }
    }

    function atualizarDashboard(dados) {
        var acumulado = {
            x30x1: 0,
            x15x2: 0,
            x6x5: 0,
            total: 0,
        };

        dados.forEach(function (item) {
            var valorLote = parseNumeroLote(item.tamanho_lote);
            var cat = obterCategoriaProduto(item.produto_descricao);
            if (cat === "x30x1") acumulado.x30x1 += valorLote;
            if (cat === "x15x2") acumulado.x15x2 += valorLote;
            if (cat === "x6x5") acumulado.x6x5 += valorLote;
            acumulado.total += valorLote;
        });

        atualizarLinha(METAS.x30x1, acumulado.x30x1, {real: "real-30x1", pct: "pct-30x1"}, gauges.x30x1);
        atualizarLinha(METAS.x15x2, acumulado.x15x2, {real: "real-15x2", pct: "pct-15x2"}, gauges.x15x2);
        atualizarLinha(METAS.x6x5, acumulado.x6x5, {real: "real-6x5", pct: "pct-6x5"}, gauges.x6x5);
        atualizarLinha(METAS.total, acumulado.total, {real: "real-total", pct: "pct-total"}, gauges.total);
    }

    tabela.on("dataFiltered", function (_filters, rows) {
        var dadosFiltrados = rows.map(function (row) { return row.getData(); });
        atualizarDashboard(dadosFiltrados);
    });

    tabela.setLocale("pt-br");
    atualizarDashboard(dadosOriginais);
})();
