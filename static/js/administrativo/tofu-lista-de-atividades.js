(function () {
    var INDICADOR_VARIANTS = ["atrasado", "alerta", "concluido", "a-fazer", "desconhecido"];

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function formatTextoOuVazio(value) {
        return toText(value) || "(Vazio)";
    }

    function normalizeText(value) {
        return toText(value)
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    function ordenarTexto(a, b) {
        return String(a.label || "").localeCompare(String(b.label || ""), "pt-BR", {
            sensitivity: "base",
            numeric: true,
        });
    }

    function ensureFilterColumns(section) {
        if (!section) return null;

        var left = section.querySelector('[data-module-filter-column="left"]')
            || section.querySelector("#tofu-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#tofu-filtros-coluna-direita");

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
            left.id = "tofu-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "tofu-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    function indicadorUi(value) {
        var indicador = normalizeText(value);
        if (indicador === "atrasado") return {variant: "atrasado", emoji: "\uD83D\uDD34", label: "Atrasado"};
        if (indicador === "alerta") return {variant: "alerta", emoji: "\uD83D\uDFE1", label: "Alerta"};
        if (indicador === "concluido") return {variant: "concluido", emoji: "\uD83D\uDFE2", label: "Conclu\u00eddo"};
        if (indicador === "a fazer" || indicador === "a_fazer") {
            return {variant: "a-fazer", emoji: "\uD83D\uDD35", label: "A Fazer"};
        }
        return {variant: "desconhecido", emoji: "\u26AA", label: formatTextoOuVazio(value)};
    }

    function formatadorIndicador(cell) {
        var ui = indicadorUi(cell.getValue());
        var cellEl = cell.getElement();

        cellEl.classList.add("tofu-indicador-cell");
        INDICADOR_VARIANTS.forEach(function (variant) {
            cellEl.classList.remove("tofu-indicador-cell--" + variant);
        });
        cellEl.classList.add("tofu-indicador-cell--" + ui.variant);

        var chip = document.createElement("span");
        chip.className = "tofu-indicador-chip tofu-indicador-chip--" + ui.variant;
        chip.title = ui.label;

        var emoji = document.createElement("span");
        emoji.className = "tofu-indicador-emoji";
        emoji.setAttribute("role", "img");
        emoji.setAttribute("aria-label", ui.label);
        emoji.textContent = ui.emoji;

        chip.appendChild(emoji);
        return chip;
    }

    function ordemIndicador(value) {
        var normalized = normalizeText(value);
        if (normalized === "atrasado") return 0;
        if (normalized === "alerta") return 1;
        if (normalized === "a fazer" || normalized === "a_fazer") return 2;
        if (normalized === "concluido") return 3;
        return 9;
    }

    function criarDefinicoesFiltrosTofu() {
        return [
            {
                key: "codigo_projeto",
                label: "C\u00f3digo Projeto",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.codigo_projeto : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "gestor",
                label: "Gestor",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.gestor : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "responsavel",
                label: "Respons\u00e1vel",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.responsavel : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "indicador",
                label: "Indicadores",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.indicador : "";
                },
                formatValue: function (value) {
                    var ui = indicadorUi(value);
                    return ui.emoji + " " + ui.label;
                },
                sortOptions: function (a, b) {
                    var ordemA = ordemIndicador(a.value);
                    var ordemB = ordemIndicador(b.value);
                    if (ordemA !== ordemB) return ordemA - ordemB;
                    return ordenarTexto(a, b);
                },
            },
        ];
    }

    function configurarFiltrosExternos(tabela, registros, secFiltros) {
        if (!secFiltros || !window.ModuleFilterCore) return null;

        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholderFiltros = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholderFiltros) placeholderFiltros.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (!filtroColumns || !filtroColumns.left || !filtroColumns.right) return null;

        var filtrosExternos = window.ModuleFilterCore.create({
            data: registros,
            definitions: criarDefinicoesFiltrosTofu(),
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

        return {secFiltros: secFiltros, filtrosExternos: filtrosExternos};
    }

    function registrarAcaoLimparFiltros(tabela, secFiltros, filtrosExternos) {
        if (!tabela || !secFiltros || !filtrosExternos) return;

        function limparTodosFiltros() {
            if (typeof filtrosExternos.clearAllFilters === "function") {
                filtrosExternos.clearAllFilters();
            }
            if (typeof tabela.clearHeaderFilter === "function") {
                tabela.clearHeaderFilter();
            }
            if (typeof tabela.refreshFilter === "function") {
                tabela.refreshFilter();
            }
        }

        var limparFiltrosSidebarBtn = secFiltros.querySelector(".module-filters-clear-all");
        var limparFiltrosToolbarBtn = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
        if (limparFiltrosSidebarBtn) {
            limparFiltrosSidebarBtn.addEventListener("click", limparTodosFiltros);
        }
        if (limparFiltrosToolbarBtn) {
            limparFiltrosToolbarBtn.addEventListener("click", limparTodosFiltros);
        }
    }

    function paraNumero(value) {
        var numero = Number(value);
        return Number.isFinite(numero) ? numero : 0;
    }

    function parseDateBr(value) {
        var texto = toText(value);
        if (!texto || texto === "-") return null;
        var partes = texto.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        if (!partes) return null;

        var dia = Number(partes[1]);
        var mes = Number(partes[2]);
        var ano = Number(partes[3]);
        if (!(ano > 0 && mes >= 1 && mes <= 12 && dia >= 1 && dia <= 31)) return null;

        var data = new Date(ano, mes - 1, dia);
        if (isNaN(data.getTime())) return null;
        data.setHours(0, 0, 0, 0);
        return data;
    }

    function addDays(date, days) {
        var proxima = new Date(date.getFullYear(), date.getMonth(), date.getDate());
        proxima.setDate(proxima.getDate() + Number(days || 0));
        proxima.setHours(0, 0, 0, 0);
        return proxima;
    }

    function getStartOfWeek(date) {
        var base = new Date(date.getFullYear(), date.getMonth(), date.getDate());
        var day = base.getDay();
        var diffToMonday = day === 0 ? -6 : 1 - day;
        base.setDate(base.getDate() + diffToMonday);
        base.setHours(0, 0, 0, 0);
        return base;
    }

    function calcPercent(value, total) {
        if (total <= 0) return 0;
        return Math.round(((value * 100) / total) * 10) / 10;
    }

    function formatPercent(value) {
        return paraNumero(value).toLocaleString("pt-BR", {
            minimumFractionDigits: 1,
            maximumFractionDigits: 1,
        }) + "%";
    }

    function calcularDashboardTofu(registros) {
        var dados = Array.isArray(registros) ? registros : [];
        var hoje = new Date();
        hoje.setHours(0, 0, 0, 0);

        var inicioSemanaAtual = getStartOfWeek(hoje);
        var fimSemanaAtual = addDays(inicioSemanaAtual, 6);
        var inicioProximaSemana = addDays(inicioSemanaAtual, 7);
        var fimProximaSemana = addDays(inicioSemanaAtual, 13);
        var inicioDuasSemanasApos = addDays(inicioSemanaAtual, 14);

        var dashboard = {
            total_atividades: dados.length,
            atrasados: {total: 0, parados: 0, em_andamento: 0, percentual: 0},
            alertas: {total: 0, semana_atual: 0, proxima_semana: 0, percentual: 0},
            concluidos: {total: 0, no_prazo: 0, fora_do_prazo: 0, percentual: 0},
            a_fazer: {total: 0, parados: 0, em_andamento: 0, percentual: 0},
        };

        dados.forEach(function (item) {
            var progresso = paraNumero(item && item.progresso);
            var dataPrevisaoInicio = parseDateBr(item && item.data_previsao_inicio);
            var dataPrevisaoTermino = parseDateBr(item && item.data_previsao_termino);
            var dataFinalizada = parseDateBr(item && item.data_finalizada);

            var ehConcluido = progresso >= 100;
            var ehAtrasado = progresso < 100 && dataPrevisaoTermino && dataPrevisaoTermino < hoje;
            var ehAlerta = (
                progresso < 100
                && dataPrevisaoTermino
                && dataPrevisaoTermino >= hoje
                && dataPrevisaoTermino <= fimProximaSemana
            );
            var ehAFazer = (
                progresso < 100
                && dataPrevisaoTermino
                && dataPrevisaoTermino >= inicioDuasSemanasApos
            );

            if (ehAtrasado) {
                dashboard.atrasados.total += 1;
                if (progresso === 0) {
                    dashboard.atrasados.parados += 1;
                } else if (progresso > 0) {
                    dashboard.atrasados.em_andamento += 1;
                }
            }

            if (ehAlerta) {
                dashboard.alertas.total += 1;
                if (dataPrevisaoTermino >= inicioSemanaAtual && dataPrevisaoTermino <= fimSemanaAtual) {
                    dashboard.alertas.semana_atual += 1;
                }
                if (dataPrevisaoTermino >= inicioProximaSemana && dataPrevisaoTermino <= fimProximaSemana) {
                    dashboard.alertas.proxima_semana += 1;
                }
            }

            if (ehConcluido) {
                dashboard.concluidos.total += 1;

                var noPrazo = (
                    dataFinalizada
                    && dataPrevisaoInicio
                    && dataPrevisaoTermino
                    && dataFinalizada >= dataPrevisaoInicio
                    && dataFinalizada <= dataPrevisaoTermino
                );
                if (noPrazo) {
                    dashboard.concluidos.no_prazo += 1;
                }

                var foraPrazo = (
                    dataFinalizada
                    && dataPrevisaoTermino
                    && dataFinalizada > dataPrevisaoTermino
                );
                if (foraPrazo) {
                    dashboard.concluidos.fora_do_prazo += 1;
                }
            }

            if (ehAFazer) {
                dashboard.a_fazer.total += 1;
                if (progresso === 0) {
                    dashboard.a_fazer.parados += 1;
                } else if (progresso > 0) {
                    dashboard.a_fazer.em_andamento += 1;
                }
            }
        });

        dashboard.atrasados.percentual = calcPercent(dashboard.atrasados.total, dashboard.total_atividades);
        dashboard.alertas.percentual = calcPercent(dashboard.alertas.total, dashboard.total_atividades);
        dashboard.concluidos.percentual = calcPercent(dashboard.concluidos.total, dashboard.total_atividades);
        dashboard.a_fazer.percentual = calcPercent(dashboard.a_fazer.total, dashboard.total_atividades);
        return dashboard;
    }

    function setTextById(id, value) {
        var element = document.getElementById(id);
        if (!element) return;
        element.textContent = String(value);
    }

    function preencherDashboard(metricas) {
        setTextById("dashboard-total-atividades", metricas.total_atividades);

        setTextById("dashboard-atrasados-total", metricas.atrasados.total);
        setTextById("dashboard-atrasados-parados", metricas.atrasados.parados);
        setTextById("dashboard-atrasados-em-andamento", metricas.atrasados.em_andamento);
        setTextById("dashboard-atrasados-percentual", formatPercent(metricas.atrasados.percentual));

        setTextById("dashboard-alertas-total", metricas.alertas.total);
        setTextById("dashboard-alertas-semana-atual", metricas.alertas.semana_atual);
        setTextById("dashboard-alertas-proxima-semana", metricas.alertas.proxima_semana);
        setTextById("dashboard-alertas-percentual", formatPercent(metricas.alertas.percentual));

        setTextById("dashboard-concluidos-total", metricas.concluidos.total);
        setTextById("dashboard-concluidos-no-prazo", metricas.concluidos.no_prazo);
        setTextById("dashboard-concluidos-fora-do-prazo", metricas.concluidos.fora_do_prazo);
        setTextById("dashboard-concluidos-percentual", formatPercent(metricas.concluidos.percentual));

        setTextById("dashboard-a-fazer-total", metricas.a_fazer.total);
        setTextById("dashboard-a-fazer-parados", metricas.a_fazer.parados);
        setTextById("dashboard-a-fazer-em-andamento", metricas.a_fazer.em_andamento);
        setTextById("dashboard-a-fazer-percentual", formatPercent(metricas.a_fazer.percentual));
    }

    function obterRegistrosAtivosTabela(tabela, fallbackData) {
        if (!tabela) return Array.isArray(fallbackData) ? fallbackData : [];

        var ativos = typeof tabela.getData === "function" ? tabela.getData("active") : null;
        if (Array.isArray(ativos)) return ativos;

        var todos = typeof tabela.getData === "function" ? tabela.getData() : null;
        if (Array.isArray(todos)) return todos;

        return Array.isArray(fallbackData) ? fallbackData : [];
    }

    function atualizarDashboardComDadosVisiveis(tabela, registros) {
        var ativos = obterRegistrosAtivosTabela(tabela, registros);
        var metricas = calcularDashboardTofu(ativos);
        preencherDashboard(metricas);
    }

    function criarColunasTofu() {
        return [
            {title: "ID", field: "id", width: 70, hozAlign: "center"},
            {title: "Projeto", field: "projeto"},
            {title: "C\u00f3digo", field: "codigo_projeto"},
            {title: "Criada por", field: "criada_por"},
            {title: "Gestor", field: "gestor"},
            {title: "Respons\u00e1vel", field: "responsavel"},
            {title: "Interlocutor", field: "interlocutor"},
            {title: "Prazo (semana)", field: "semana_de_prazo", hozAlign: "center"},
            {title: "Prev. In\u00edcio", field: "data_previsao_inicio"},
            {title: "Prev. T\u00e9rmino", field: "data_previsao_termino"},
            {title: "Finalizada", field: "data_finalizada"},
            {title: "Indicador", field: "indicador", hozAlign: "center", width: 118, formatter: formatadorIndicador},
            {title: "Hist\u00f3rico", field: "historico"},
            {title: "Tarefa", field: "tarefa"},
            {title: "Progresso (%)", field: "progresso", hozAlign: "center"},
        ];
    }

    function initTofuTabela() {
        var dataElement = document.getElementById("atividades-tabulator-data");
        if (!dataElement || !window.Tabulator) return;

        var registros = JSON.parse(dataElement.textContent || "[]");
        var secFiltros = document.getElementById("sec-filtros");
        if (secFiltros) {
            secFiltros.dataset.moduleFiltersAuto = "off";
        }
        var colunas = criarColunasTofu();
        window.TabulatorDefaults.addEditActionColumnIfAny(colunas, registros);

        var tabela = window.TabulatorDefaults.create("#atividades-tabulator", {
            data: registros,
            columns: colunas,
        });

        var filtrosConfig = configurarFiltrosExternos(tabela, registros, secFiltros);
        if (filtrosConfig) {
            registrarAcaoLimparFiltros(tabela, filtrosConfig.secFiltros, filtrosConfig.filtrosExternos);
        }

        ["tableBuilt", "dataLoaded", "renderComplete", "dataFiltered"].forEach(function (eventName) {
            tabela.on(eventName, function () {
                atualizarDashboardComDadosVisiveis(tabela, registros);
            });
        });
        setTimeout(function () {
            atualizarDashboardComDadosVisiveis(tabela, registros);
        }, 0);

        tabela.setLocale("pt-br");
    }

    initTofuTabela();
})();
