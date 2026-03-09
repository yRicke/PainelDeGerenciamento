(function () {
    var form = document.getElementById("upload-faturamento-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-faturamento");
    var input = document.getElementById("arquivo-faturamento-input");
    var fileStatus = document.getElementById("nome-arquivo-faturamento-selecionado");
    var loadingStatus = document.getElementById("faturamento-loading-status");
    var temArquivoExistente = form.dataset.temArquivoExistente === "1";

    function isArquivoVisivel(file) {
        if (!file) return false;
        var caminho = String(file.webkitRelativePath || file.name || "").replace(/\\/g, "/");
        if (!caminho) return false;

        var partes = caminho.split("/").filter(Boolean);
        if (!partes.length) return false;
        var nome = partes[partes.length - 1];
        if (!nome || nome.startsWith("~$") || nome.startsWith(".")) return false;
        for (var i = 0; i < partes.length; i += 1) {
            if (partes[i].startsWith(".")) return false;
        }
        return true;
    }

    function coletarArquivosXlsx(files) {
        if (!files || !files.length) return [];
        return Array.from(files).filter(function (file) {
            return isArquivoVisivel(file) && String(file.name || "").toLowerCase().endsWith(".xlsx");
        });
    }

    function atualizarStatus() {
        var arquivosXlsx = coletarArquivosXlsx(input.files);
        if (!arquivosXlsx.length) {
            fileStatus.textContent = "";
            return;
        }
        fileStatus.textContent = arquivosXlsx.length + " arquivo(s) .xlsx selecionado(s).";
    }

    function confirmarSubstituicaoSeNecessario() {
        if (!temArquivoExistente) return true;
        return window.confirm("Ja existe lote na pasta de importacao. Deseja substituir o lote atual?");
    }

    function iniciarCarregamento() {
        form.classList.add("is-loading");
        if (loadingStatus) loadingStatus.classList.add("is-visible");
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
        if (!event.dataTransfer || !event.dataTransfer.files || !event.dataTransfer.files.length) return;
        input.files = event.dataTransfer.files;
        atualizarStatus();
    });

    input.addEventListener("change", atualizarStatus);

    form.addEventListener("submit", function (event) {
        var arquivosXlsx = coletarArquivosXlsx(input.files);
        if (!arquivosXlsx.length) {
            event.preventDefault();
            window.alert("Selecione uma pasta com arquivos .xlsx para continuar.");
            return;
        }
        if (!confirmarSubstituicaoSeNecessario()) {
            event.preventDefault();
            return;
        }

        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("faturamento-tabulator-data");
    if (!dataElement) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var metaConfigElement = document.getElementById("faturamento-meta-config-data");
    var pedidosPendentesElement = document.getElementById("faturamento-pedidos-pendentes-data");
    var metaConfig = metaConfigElement ? JSON.parse(metaConfigElement.textContent || "{}") : {};
    var pedidosPendentesData = pedidosPendentesElement ? JSON.parse(pedidosPendentesElement.textContent || "[]") : [];
    var tabelaTarget = document.getElementById("faturamento-tabulator");
    var kpiValorFaturamentoEl = document.getElementById("faturamento-kpi-valor-faturamento");
    var kpiMetaGeralEl = document.getElementById("faturamento-kpi-meta-geral");
    var kpiGapFaturamentoEl = document.getElementById("faturamento-kpi-gap-faturamento");
    var kpiPrazoMedioEl = document.getElementById("faturamento-kpi-prazo-medio");
    var kpiDiasUteisEl = document.getElementById("faturamento-kpi-dias-uteis");
    var kpiMetaDiariaEl = document.getElementById("faturamento-kpi-meta-diaria");
    var kpiTotalPedidosPendentesEl = document.getElementById("faturamento-kpi-total-pedidos-pendentes");
    var kpiQtdClientesEl = document.getElementById("faturamento-kpi-qtd-clientes");
    var kpiParticipacaoVendaGeralEl = document.getElementById("faturamento-kpi-participacao-venda-geral");
    var incluirPedidosPendentesEl = document.getElementById("faturamento-kpi-meta-diaria-incluir-pendentes");
    var relogioMetaEl = document.getElementById("faturamento-reloginho-meta");
    var relogioRealEl = document.getElementById("faturamento-reloginho-real");
    var relogioPctEl = document.getElementById("faturamento-reloginho-pct");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});
    var nomesMeses = [
        "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ];

    function toText(valor) {
        if (valor === null || valor === undefined) return "";
        return String(valor).trim();
    }

    function formatTextoOuVazio(valor) {
        return toText(valor) || "(Vazio)";
    }

    function normalizeText(valor) {
        return toText(valor)
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    function gerenteToken(valor) {
        var token = normalizeText(valor).replace(/\s+/g, " ").trim();
        if (
            token === "sem gerente"
            || token === "<sem gerente>"
            || token === "sem vendedor"
            || token === "<sem vendedor>"
        ) {
            return "";
        }
        return token;
    }

    function gerenteEhMpOuLuciano(valor) {
        var token = gerenteToken(valor);
        if (!token) return false;
        if (token.indexOf("luciano") >= 0) return true;
        return /(^| )ger(ente)? ?mp($| )/.test(token) || token === "mp";
    }

    function chaveMes(item) {
        var ano = Number(item && item.ano_faturamento ? item.ano_faturamento : 0);
        var mes = Number(item && item.mes_faturamento ? item.mes_faturamento : 0);
        if (!ano || !mes || mes < 1 || mes > 12) return "";
        return String(ano) + "-" + String(mes);
    }

    function chaveNotaFiscal(item) {
        var numeroNota = toText(item ? item.numero_nota : "");
        if (numeroNota) return numeroNota;
        return "row|" + toText(item ? item.id : "");
    }

    function consolidarNotasUnicas(registros) {
        var itens = Array.isArray(registros) ? registros : [];
        var notasMap = new Map();

        itens.forEach(function (item) {
            var chave = chaveNotaFiscal(item);
            var valorNota = Number(item && item.valor_nota ? item.valor_nota : 0);
            var valorUnico = Number(item && item.valor_nota_unico ? item.valor_nota_unico : 0);
            var atual = notasMap.get(chave);

            if (!atual) {
                notasMap.set(chave, {
                    valorNotaReferencia: valorNota,
                    valorUnicoMaximo: valorUnico,
                });
                return;
            }

            if (!atual.valorNotaReferencia && valorNota) {
                atual.valorNotaReferencia = valorNota;
            }
            if (Math.abs(valorUnico) > Math.abs(atual.valorUnicoMaximo)) {
                atual.valorUnicoMaximo = valorUnico;
            }
        });

        var total = 0;
        notasMap.forEach(function (nota) {
            var valorConsolidado = Number(nota.valorUnicoMaximo || 0);
            if (!valorConsolidado) {
                valorConsolidado = Number(nota.valorNotaReferencia || 0);
            }
            total += valorConsolidado;
        });

        return {
            totalValorNota: total,
            quantidadeNotasUnicas: notasMap.size,
        };
    }

    function chaveClienteEmpresa(item) {
        var parceiroId = toText(item ? item.parceiro_id : "");
        var parceiroLabel = toText(item ? item.parceiro_label : "");
        var nomeEmpresa = toText(item ? item.nome_empresa : "");
        var clienteBase = parceiroId || parceiroLabel || ("row|" + toText(item ? item.id : ""));
        return [clienteBase, nomeEmpresa].join("|");
    }

    function contarClientesDistintos(registros) {
        var itens = Array.isArray(registros) ? registros : [];
        var clientes = new Set();
        itens.forEach(function (item) {
            clientes.add(chaveClienteEmpresa(item));
        });
        return clientes.size;
    }

    function contarDiasUteisEntre(inicio, fim) {
        if (!inicio || !fim) return 0;
        if (inicio > fim) return 0;

        var cursor = new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate());
        var limite = new Date(fim.getFullYear(), fim.getMonth(), fim.getDate());
        var total = 0;

        while (cursor <= limite) {
            var diaSemana = cursor.getDay();
            if (diaSemana !== 0 && diaSemana !== 6) total += 1;
            cursor.setDate(cursor.getDate() + 1);
        }

        return total;
    }

    function calcularDiasUteisRestantesMesAtual() {
        var hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        var inicio = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
        var fim = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
        return contarDiasUteisEntre(inicio, fim);
    }

    function valorParaAngulo(valor, maximo) {
        if (maximo <= 0) return -90;
        var relacao = Math.max(0, Math.min(1, valor / maximo));
        return -90 + (relacao * 180);
    }

    function setRotacaoPonteiro(id, angulo) {
        var el = document.getElementById(id);
        if (!el) return;
        el.style.transform = "rotate(" + angulo + "deg)";
    }

    function atualizarReloginho(metaGeral, valorFaturamento) {
        var meta = Number(metaGeral || 0);
        var real = Number(valorFaturamento || 0);
        var percentual = meta > 0 ? (real / meta) * 100 : 0;
        var referencia = meta > 0 ? meta : Math.max(real, 1);

        if (relogioMetaEl) relogioMetaEl.textContent = formatadorMoeda.format(meta);
        if (relogioRealEl) relogioRealEl.textContent = formatadorMoeda.format(real);
        if (relogioPctEl) relogioPctEl.textContent = percentual.toFixed(2).replace(".", ",") + "%";

        setRotacaoPonteiro("faturamento-reloginho-ponteiro-meta", valorParaAngulo(referencia, referencia));
        setRotacaoPonteiro("faturamento-reloginho-ponteiro-real", valorParaAngulo(real, referencia));
    }

    function criarMapaPedidosPendentesPorGerente() {
        var mapa = {};
        if (!Array.isArray(pedidosPendentesData)) return mapa;

        pedidosPendentesData.forEach(function (item) {
            var token = gerenteToken(item ? item.gerente : "");
            var valor = Number(item ? item.total_vlr_nota : 0);
            if (!mapa[token]) mapa[token] = 0;
            mapa[token] += valor;
        });

        return mapa;
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
            || section.querySelector("#faturamento-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#faturamento-filtros-coluna-direita");

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
            left.id = "faturamento-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "faturamento-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    function mesLabel(valor) {
        var mes = Number(valor || 0);
        if (!mes || mes < 1 || mes > 12) return "(Vazio)";
        return nomesMeses[mes - 1];
    }

    function formatPercentual(valor, casas) {
        var decimais = Number(casas || 3);
        var numero = Number(valor || 0);
        var texto = numero.toFixed(decimais).replace(".", ",");
        return texto + "%";
    }

    function formatMoedaCell(cell) {
        return formatadorMoeda.format(Number(cell.getValue() || 0));
    }

    function formatPercentualCell(cell) {
        return formatPercentual(cell.getValue(), 3);
    }

    function formatPercentualClienteCell(cell) {
        return formatPercentual(cell.getValue(), 2);
    }

    var pedidosPendentesPorGerente = criarMapaPedidosPendentesPorGerente();

    function calcularMetricasDashboard(linhas) {
        var itens = Array.isArray(linhas) ? linhas : [];
        var somaPrazoMedio = 0;
        var qtdPrazoMedio = 0;
        var mesesSelecionadosSet = new Set();
        var gruposGerenteSet = new Set();
        var gerentesAtivosSet = new Set();
        var consolidadoNotasFiltradas = consolidarNotasUnicas(itens);
        var qtdClientesDistintos = contarClientesDistintos(itens);

        itens.forEach(function (item) {
            var prazoMedio = Number(item.prazo_medio || 0);
            var tokenGerente = gerenteToken(item.gerente);
            var mes = chaveMes(item);

            if (!Number.isNaN(prazoMedio)) {
                somaPrazoMedio += prazoMedio;
                qtdPrazoMedio += 1;
            }
            if (mes) mesesSelecionadosSet.add(mes);
            gerentesAtivosSet.add(tokenGerente);
            gruposGerenteSet.add(gerenteEhMpOuLuciano(item.gerente) ? "mp_luciano" : "pa_outros");
        });
        var valorFaturamento = consolidadoNotasFiltradas.totalValorNota;

        var mesesSelecionados = mesesSelecionadosSet.size;
        if (!mesesSelecionados && itens.length) mesesSelecionados = 1;

        var compromisso = Number(metaConfig.compromisso || 0);
        var gerentePaOutros = Number(metaConfig.gerente_pa_e_outros || 0);
        var gerenteMpLuciano = Number(metaConfig.gerente_mp_e_gerente_luciano || 0);
        var metaBase = 0;
        if (itens.length) {
            if (gruposGerenteSet.has("pa_outros") && gruposGerenteSet.has("mp_luciano")) {
                metaBase = compromisso;
            } else if (gruposGerenteSet.has("mp_luciano")) {
                metaBase = gerenteMpLuciano;
            } else {
                metaBase = gerentePaOutros;
            }
        }
        var metaGeral = metaBase * mesesSelecionados;
        var gapFaturamento = metaGeral - valorFaturamento;
        var prazoMedioArredondado = qtdPrazoMedio > 0 ? Math.round(somaPrazoMedio / qtdPrazoMedio) : 0;
        var diasUteisRestantes = calcularDiasUteisRestantesMesAtual();

        var totalPedidosPendentes = 0;
        gerentesAtivosSet.forEach(function (gerenteAtual) {
            totalPedidosPendentes += Number(pedidosPendentesPorGerente[gerenteAtual] || 0);
        });

        var incluirPendentes = incluirPedidosPendentesEl ? incluirPedidosPendentesEl.checked : false;
        var numeradorMetaDiaria = gapFaturamento + (incluirPendentes ? totalPedidosPendentes : 0);
        var metaDiaria = diasUteisRestantes > 0 ? (numeradorMetaDiaria / diasUteisRestantes) : 0;

        var totalMesSelecionado = 0;
        if (mesesSelecionadosSet.size) {
            var registrosMesSelecionado = [];
            data.forEach(function (item) {
                if (mesesSelecionadosSet.has(chaveMes(item))) {
                    registrosMesSelecionado.push(item);
                }
            });
            totalMesSelecionado = consolidarNotasUnicas(registrosMesSelecionado).totalValorNota;
        } else if (itens.length) {
            totalMesSelecionado = valorFaturamento;
        }
        var participacaoVendaGeral = totalMesSelecionado > 0 ? (valorFaturamento / totalMesSelecionado) : 0;

        return {
            valorFaturamento: valorFaturamento,
            metaGeral: metaGeral,
            gapFaturamento: gapFaturamento,
            prazoMedioArredondado: prazoMedioArredondado,
            diasUteisRestantes: diasUteisRestantes,
            totalPedidosPendentes: totalPedidosPendentes,
            metaDiaria: metaDiaria,
            qtdClientes: qtdClientesDistintos,
            participacaoVendaGeral: participacaoVendaGeral,
        };
    }

    function atualizarDashboard(linhas) {
        var metricas = calcularMetricasDashboard(linhas);

        if (kpiValorFaturamentoEl) kpiValorFaturamentoEl.textContent = formatadorMoeda.format(metricas.valorFaturamento);
        if (kpiMetaGeralEl) kpiMetaGeralEl.textContent = formatadorMoeda.format(metricas.metaGeral);
        if (kpiGapFaturamentoEl) kpiGapFaturamentoEl.textContent = formatadorMoeda.format(metricas.gapFaturamento);
        if (kpiPrazoMedioEl) kpiPrazoMedioEl.textContent = String(metricas.prazoMedioArredondado);
        if (kpiDiasUteisEl) kpiDiasUteisEl.textContent = String(metricas.diasUteisRestantes);
        if (kpiMetaDiariaEl) kpiMetaDiariaEl.textContent = formatadorMoeda.format(metricas.metaDiaria);
        if (kpiTotalPedidosPendentesEl) {
            kpiTotalPedidosPendentesEl.textContent = (
                formatadorMoeda.format(metricas.totalPedidosPendentes)
                + " / "
                + String(metricas.diasUteisRestantes)
                + " dias uteis"
            );
        }
        if (kpiQtdClientesEl) kpiQtdClientesEl.textContent = String(metricas.qtdClientes);
        if (kpiParticipacaoVendaGeralEl) {
            kpiParticipacaoVendaGeralEl.textContent = formatPercentual(metricas.participacaoVendaGeral * 100, 2);
        }
        atualizarReloginho(metricas.metaGeral, metricas.valorFaturamento);
    }

    function criarDefinicoesFiltrosFaturamento() {
        return [
            {
                key: "nome_empresa",
                label: "Empresa",
                singleSelect: true,
                extractValue: function (rowData) { return rowData ? rowData.nome_empresa : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "ano_faturamento",
                label: "Ano",
                singleSelect: true,
                extractValue: function (rowData) { return rowData ? rowData.ano_faturamento : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: function (a, b) { return Number(b.value || 0) - Number(a.value || 0); },
            },
            {
                key: "mes_faturamento",
                label: "Mes",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.mes_faturamento : ""; },
                formatValue: mesLabel,
                sortOptions: function (a, b) { return Number(a.value || 0) - Number(b.value || 0); },
            },
            {
                key: "data_faturamento_iso",
                label: "Data do Faturamento",
                singleSelect: true,
                extractValue: function (rowData) { return rowData ? rowData.data_faturamento_iso : ""; },
                formatValue: function (valor) {
                    var texto = toText(valor);
                    if (!texto) return "(Vazio)";
                    var partes = texto.split("-");
                    if (partes.length !== 3) return texto;
                    return partes[2] + "/" + partes[1] + "/" + partes[0];
                },
                sortOptions: function (a, b) { return String(a.value || "").localeCompare(String(b.value || "")); },
            },
            {
                key: "status_nfe",
                label: "Status NF-e",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.status_nfe : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "tipo_venda",
                label: "Tipo da Venda",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.tipo_venda : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "operacao_descricao",
                label: "Descricao (Tipo de Operacao)",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.operacao_descricao : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "cidade_parceiro",
                label: "Cidade Parceiro",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.cidade_parceiro : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "gerente",
                label: "Gerente",
                singleSelect: false,
                extractValue: function (rowData) {
                    var valor = rowData ? rowData.gerente : "";
                    if (!gerenteToken(valor)) {
                        return "";
                    }
                    return valor;
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "tipo_movimento",
                label: "Tipo de Movimentacao",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.tipo_movimento : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "descricao_perfil",
                label: "Descricao Perfil",
                singleSelect: false,
                extractValue: function (rowData) { return rowData ? rowData.descricao_perfil : ""; },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
        ];
    }

    function configurarFiltrosExternos(tabela, registros, secFiltros) {
        if (!tabela || !secFiltros || !window.ModuleFilterCore) return null;

        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholderFiltros = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholderFiltros) placeholderFiltros.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (!filtroColumns || !filtroColumns.left || !filtroColumns.right) return null;

        var filtrosExternos = window.ModuleFilterCore.create({
            data: registros,
            definitions: criarDefinicoesFiltrosFaturamento(),
            leftColumn: filtroColumns.left,
            rightColumn: filtroColumns.right,
            onChange: function () {
                if (typeof tabela.refreshFilter === "function") tabela.refreshFilter();
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
            if (typeof filtrosExternos.clearAllFilters === "function") filtrosExternos.clearAllFilters();
            if (typeof tabela.clearHeaderFilter === "function") tabela.clearHeaderFilter();
            if (typeof tabela.refreshFilter === "function") tabela.refreshFilter();
        }

        var limparFiltrosSidebarBtn = secFiltros.querySelector(".module-filters-clear-all");
        var limparFiltrosToolbarBtn = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
        if (limparFiltrosSidebarBtn) limparFiltrosSidebarBtn.addEventListener("click", limparTodosFiltros);
        if (limparFiltrosToolbarBtn) limparFiltrosToolbarBtn.addEventListener("click", limparTodosFiltros);
    }

    if (!tabelaTarget || !window.Tabulator || !window.TabulatorDefaults) {
        atualizarDashboard(data);
        if (incluirPedidosPendentesEl) {
            incluirPedidosPendentesEl.addEventListener("change", function () {
                atualizarDashboard(data);
            });
        }
        return;
    }

    var colunas = [
        {title: "Nome Origem", field: "nome_origem"},
        {title: "Dt. do Faturamento", field: "data_faturamento"},
        {title: "Nome Empresa", field: "nome_empresa"},
        {title: "Parceiro", field: "parceiro_label"},
        {title: "Nro. Nota", field: "numero_nota"},
        {title: "Vlr. Nota", field: "valor_nota", formatter: formatMoedaCell},
        {title: "%Part. Venda Geral", field: "participacao_venda_geral", formatter: formatPercentualCell},
        {title: "%Part. Venda Cliente", field: "participacao_venda_cliente", formatter: formatPercentualClienteCell},
        {title: "Vlr. Nota (Unico)", field: "valor_nota_unico", formatter: formatMoedaCell},
        {title: "Peso Bruto (Unico)", field: "peso_bruto_unico"},
        {title: "Qtd. Volumes", field: "quantidade_volumes"},
        {title: "Qtd. Saida", field: "quantidade_saida"},
        {title: "Status NF-e", field: "status_nfe"},
        {title: "Apelido (Vendedor)", field: "apelido_vendedor"},
        {title: "Descricao (Tipo de Operacao)", field: "operacao_descricao"},
        {title: "Descricao (Natureza)", field: "natureza_descricao"},
        {title: "Descricao (Centro de Resultado)", field: "centro_resultado_descricao"},
        {title: "Tipo de Movimento", field: "tipo_movimento"},
        {title: "Prazo Medio", field: "prazo_medio"},
        {title: "Media (Unica)", field: "media_unica"},
        {title: "Tipo da Venda", field: "tipo_venda"},
        {title: "Produto", field: "produto_label"},
        {title: "Cidade Parceiro [SAFIA]", field: "cidade_parceiro"},
        {title: "Gerente", field: "gerente"},
        {title: "Descricao (Perfil)", field: "descricao_perfil"},
        {title: "Valor Frete", field: "valor_frete", formatter: formatMoedaCell},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data, {
        width: 110,
        formatter: function (cell) {
            var url = cell.getValue();
            if (!url) return "";
            return '<button type="button" class="btn-primary js-editar-faturamento">Editar</button>';
        },
        cellClick: function (e, cell) {
            var row = cell.getRow().getData();
            var target = e.target && e.target.closest ? e.target.closest(".js-editar-faturamento") : null;
            if (!target || !row.editar_url) return;
            window.location.href = row.editar_url;
        },
    });

    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros) secFiltros.dataset.moduleFiltersAuto = "off";

    var tabela = window.TabulatorDefaults.create("#faturamento-tabulator", {
        data: data,
        columns: colunas,
        freezeUX: {
            enabled: true,
        },
    });

    var filtrosConfig = configurarFiltrosExternos(tabela, data, secFiltros);
    if (filtrosConfig) {
        registrarAcaoLimparFiltros(tabela, filtrosConfig.secFiltros, filtrosConfig.filtrosExternos);
    }

    function atualizarDashboardComTabela() {
        var linhasAtivas = tabela.getData("active");
        if (!Array.isArray(linhasAtivas)) linhasAtivas = tabela.getData() || [];
        atualizarDashboard(linhasAtivas);
    }

    if (incluirPedidosPendentesEl) {
        incluirPedidosPendentesEl.addEventListener("change", atualizarDashboardComTabela);
    }

    tabela.on("tableBuilt", atualizarDashboardComTabela);
    tabela.on("dataLoaded", atualizarDashboardComTabela);
    tabela.on("dataFiltered", atualizarDashboardComTabela);
    tabela.on("renderComplete", atualizarDashboardComTabela);
    setTimeout(atualizarDashboardComTabela, 0);
})();
