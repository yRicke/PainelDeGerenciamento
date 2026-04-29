(function () {
    var form = document.getElementById("upload-pedidos-pendentes-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-pedidos-pendentes");
    var input = document.getElementById("arquivo-pedidos-pendentes-input");
    var confirmInput = document.getElementById("confirmar-substituicao-input");
    var fileStatus = document.getElementById("nome-arquivo-pedidos-pendentes-selecionado");
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
        if (!window.confirm(replaceCurrentFileMessage)) return false;
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
        if (!files || !files.length) return;
        if (!validarExtensaoXlsx(files[0])) {
            window.alert(mensagemApenasArquivoPermitido());
            return;
        }
        input.files = files;
        atualizarNomeArquivo();
    });

    input.addEventListener("change", function () {
        if (!input.files || !input.files.length) return;
        if (!validarExtensaoXlsx(input.files[0])) {
            window.alert(mensagemApenasArquivoPermitido());
            input.value = "";
        }
        atualizarNomeArquivo();
    });

    form.addEventListener("submit", function (event) {
        if (!input.files || !input.files.length) {
            event.preventDefault();
            window.alert(mensagemSelecionarArquivoParaContinuar());
            return;
        }
        if (!validarExtensaoXlsx(input.files[0])) {
            event.preventDefault();
            window.alert(mensagemApenasArquivoPermitido());
            return;
        }
        if (temArquivoExistente && confirmInput.value !== "1" && !confirmarSubstituicaoSeNecessario()) {
            event.preventDefault();
        }
    });
})();

(function () {
    var dataElement = document.getElementById("pedidos-pendentes-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var possuiEdicao = window.TabulatorDefaults && typeof window.TabulatorDefaults.hasAnyRowAction === "function"
        ? window.TabulatorDefaults.hasAnyRowAction(data, ["editar_url"])
        : data.some(function (item) { return Boolean(item.editar_url); });
    var chartContainer = document.getElementById("pedidos-status-chart");
    var STATUS_LABELS = {
        atrasado: "Atrasado",
        atencao: "Atenção",
        noPrazo: "No Prazo",
        outros: "Outros",
    };

    function normalizarParaComparacao(valor) {
        return String(valor || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();
    }

    var kpis = {
        entrega: {
            pesoBruto: document.getElementById("kpi-entrega-peso-bruto"),
            qtd: document.getElementById("kpi-entrega-qtd"),
            valorNota: document.getElementById("kpi-entrega-valor-nota"),
        },
        vendaBalcao: {
            pesoBruto: document.getElementById("kpi-venda-balcao-peso-bruto"),
            qtd: document.getElementById("kpi-venda-balcao-qtd"),
            valorNota: document.getElementById("kpi-venda-balcao-valor-nota"),
        },
        atencao: {
            pesoBruto: document.getElementById("kpi-atencao-peso-bruto"),
            qtd: document.getElementById("kpi-atencao-qtd"),
            valorNota: document.getElementById("kpi-atencao-valor-nota"),
        },
        noPrazo: {
            pesoBruto: document.getElementById("kpi-no-prazo-peso-bruto"),
            qtd: document.getElementById("kpi-no-prazo-qtd"),
            valorNota: document.getElementById("kpi-no-prazo-valor-nota"),
        },
        totalPedidos: {
            pesoBruto: document.getElementById("kpi-total-pedidos-peso-bruto"),
            qtd: document.getElementById("kpi-total-pedidos-qtd"),
            valorNota: document.getElementById("kpi-total-pedidos-valor-nota"),
        },
    };

    function normalizarStatus(status) {
        var texto = normalizarParaComparacao(status);
        if (texto === "atencao") return STATUS_LABELS.atencao;
        if (texto === "atrasado") return STATUS_LABELS.atrasado;
        if (texto === "no prazo") return STATUS_LABELS.noPrazo;
        return STATUS_LABELS.outros;
    }

    function normalizarTipoVenda(tipoVenda) {
        var texto = normalizarParaComparacao(tipoVenda);
        if (texto.indexOf("venda balcao") >= 0) return "vendaBalcao";
        if (texto.indexOf("entrega") >= 0) return "entrega";
        return "outro";
    }

    function formatarNumero(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        });
    }

    function formatarMoeda(valor) {
        if (!valor) return "R$-";
        return Number(valor || 0).toLocaleString("pt-BR", {
            style: "currency",
            currency: "BRL",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function novoBucket() {
        return {pesoBruto: 0, qtd: 0, valorNota: 0};
    }

    function escreverKpi(bucket, refs) {
        refs.pesoBruto.textContent = formatarNumero(bucket.pesoBruto);
        refs.qtd.textContent = formatarNumero(bucket.qtd);
        refs.valorNota.textContent = formatarMoeda(bucket.valorNota);
    }

    function formatTextoOuVazio(valor) {
        var texto = String(valor || "").trim();
        return texto || "(Vazio)";
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
            || section.querySelector("#pedidos-pendentes-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#pedidos-pendentes-filtros-coluna-direita");

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
            left.id = "pedidos-pendentes-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "pedidos-pendentes-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    function criarDefinicoesFiltrosPedidos() {
        return [
            {
                key: "rota",
                label: "Rota",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.rota : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "regiao",
                label: "Região",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.regiao : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "tipo_venda",
                label: "Tipo de Venda",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.tipo_venda : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "status",
                label: "Status",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.status : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "gerente",
                label: "Gerente",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.gerente : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
        ];
    }

    function configurarFiltrosExternos(tabelaRef, registros) {
        var secFiltros = document.getElementById("sec-filtros");
        if (secFiltros) {
            secFiltros.dataset.moduleFiltersAuto = "off";
        }
        if (!secFiltros || !window.ModuleFilterCore) return null;

        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholderFiltros = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholderFiltros) placeholderFiltros.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (!filtroColumns || !filtroColumns.left || !filtroColumns.right) return null;

        var filtrosExternos = window.ModuleFilterCore.create({
            data: registros,
            definitions: criarDefinicoesFiltrosPedidos(),
            leftColumn: filtroColumns.left,
            rightColumn: filtroColumns.right,
            onChange: function () {
                if (typeof tabelaRef.refreshFilter === "function") {
                    tabelaRef.refreshFilter();
                }
            },
        });

        tabelaRef.addFilter(function (rowData) {
            return filtrosExternos.matchesRecord(rowData);
        });

        return {secFiltros: secFiltros, filtrosExternos: filtrosExternos};
    }

    function registrarAcaoLimparFiltros(tabelaRef, secFiltros, filtrosExternos) {
        if (!secFiltros || !filtrosExternos) return;

        function limparTodosFiltros() {
            if (typeof filtrosExternos.clearAllFilters === "function") {
                filtrosExternos.clearAllFilters();
            }
            if (typeof tabelaRef.clearHeaderFilter === "function") {
                tabelaRef.clearHeaderFilter();
            }
            if (typeof tabelaRef.refreshFilter === "function") {
                tabelaRef.refreshFilter();
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

    var statusChart = null;
    if (chartContainer && window.ApexCharts) {
        statusChart = new window.ApexCharts(chartContainer, {
            chart: {
                type: "donut",
                height: 290,
            },
            labels: [STATUS_LABELS.atrasado, STATUS_LABELS.atencao, STATUS_LABELS.noPrazo, STATUS_LABELS.outros],
            colors: ["#e23b2d", "#f2bf00", "#2f7ec7", "#a53bb7"],
            series: [0, 0, 0, 0],
            legend: {position: "bottom"},
            dataLabels: {
                enabled: true,
                formatter: function (val) {
                    return Math.round(val) + "%";
                },
            },
            tooltip: {
                y: {
                    formatter: function (val) {
                        return val + " pedido(s)";
                    },
                },
            },
        });
        statusChart.render();
    }

    var tabela = window.TabulatorDefaults.create("#pedidos-pendentes-tabulator", {
        data: data,
        columns: [
            {title: "Número Único", field: "numero_unico", headerFilter: "input"},
            {title: "Rota", field: "rota", headerFilter: "input"},
            {title: "Região", field: "regiao", headerFilter: "input"},
            {title: "Valor por Tonelada", field: "valor_tonelada_frete_safia", headerFilter: "input"},
            {title: "Pendente", field: "pendente", headerFilter: "input"},
            {title: "Nome da Cidade (Parceiro - SAFIA)", field: "nome_cidade_parceiro_safia", headerFilter: "input"},
            {title: "Previsão de Entrega", field: "previsao_entrega", headerFilter: "input"},
            {title: "Data Máxima", field: "dt_neg", headerFilter: "input"},
            {title: "Prazo", field: "prazo_maximo", hozAlign: "center", headerFilter: "input"},
            {title: "Dias em Negociação", field: "dias_negociados", hozAlign: "center", headerFilter: "input"},
            {title: "Status", field: "status", headerFilter: "input"},
            {title: "Tipo de Venda", field: "tipo_venda", headerFilter: "input"},
            {title: "Nome da Empresa", field: "nome_empresa", headerFilter: "input"},
            {title: "Código e Nome do Parceiro", field: "cod_nome_parceiro", headerFilter: "input"},
            {
                title: "Valor da Nota",
                field: "vlr_nota",
                hozAlign: "right",
                formatter: "money",
                formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2},
            },
            {title: "Peso Bruto", field: "peso_bruto", hozAlign: "right"},
            {title: "Peso", field: "peso", hozAlign: "right"},
            {title: "Peso Líquido", field: "peso_liq_itens", hozAlign: "right"},
            {title: "Apelido", field: "apelido_vendedor", headerFilter: "input"},
            {title: "Gerente", field: "gerente", headerFilter: "input"},
            {title: "Data para Cálculo", field: "data_para_calculo", headerFilter: "input"},
            {title: "Descrição do Tipo de Negociação", field: "descricao_tipo_negociacao", headerFilter: "input"},
            {title: "Número da Nota", field: "nro_nota", headerFilter: "input"},
            {title: "Previsão de Carregamento", field: "previsao_do_carregamento", headerFilter: "input"},
            {title: "Motorista", field: "motorista", headerFilter: "input"},
            {title: "Transportadora", field: "transportadora", headerFilter: "input"},
            {
                title: "Ações",
                formatter: function () {
                    if (possuiEdicao) {
                        return '<a class="btn-primary js-editar-pedido" href="#">Editar</a> <a class="btn-light js-abrir-agenda" href="#">Abrir Agenda</a>';
                    }
                    return '<a class="btn-light js-abrir-agenda" href="#">Abrir Agenda</a>';
                },
                hozAlign: "center",
                cellClick: function (e, cell) {
                    var row = cell.getRow().getData();
                    if (e.target && e.target.classList && e.target.classList.contains("js-editar-pedido") && row.editar_url) {
                        e.preventDefault();
                        window.location.href = row.editar_url;
                    }
                    if (e.target && e.target.classList && e.target.classList.contains("js-abrir-agenda")) {
                        e.preventDefault();
                        var numeroUnico = row.numero_unico || "";
                        var agendaUrl = row.agenda_base_url + "?numero_unico=" + encodeURIComponent(numeroUnico);
                        window.location.href = agendaUrl;
                    }
                },
            },
        ],
    });

    var filtrosConfig = configurarFiltrosExternos(tabela, data);
    if (filtrosConfig) {
        registrarAcaoLimparFiltros(tabela, filtrosConfig.secFiltros, filtrosConfig.filtrosExternos);
    }

    function atualizarDashboard() {
        var linhas = tabela.getData("active");
        if (!linhas || !linhas.length) {
            linhas = tabela.getData() || [];
        }

        var buckets = {
            entrega: novoBucket(),
            vendaBalcao: novoBucket(),
            atencao: novoBucket(),
            noPrazo: novoBucket(),
            totalPedidos: novoBucket(),
        };

        var statusSeries = {
            "Atrasado": 0,
            "Atenção": 0,
            "No Prazo": 0,
            "Outros": 0,
        };

        linhas.forEach(function (item) {
            var pesoBruto = Number(item.peso_bruto || 0);
            var valorNota = Number(item.vlr_nota || 0);

            buckets.totalPedidos.pesoBruto += pesoBruto;
            buckets.totalPedidos.valorNota += valorNota;
            buckets.totalPedidos.qtd += 1;

            var statusNorm = normalizarStatus(item.status);
            var tipoKey = normalizarTipoVenda(item.tipo_venda);
            if (statusNorm === STATUS_LABELS.atrasado && (tipoKey === "entrega" || tipoKey === "vendaBalcao")) {
                buckets[tipoKey].pesoBruto += pesoBruto;
                buckets[tipoKey].valorNota += valorNota;
                buckets[tipoKey].qtd += 1;
            }
            if (statusNorm === STATUS_LABELS.atencao) {
                buckets.atencao.pesoBruto += pesoBruto;
                buckets.atencao.valorNota += valorNota;
                buckets.atencao.qtd += 1;
            }
            if (statusNorm === STATUS_LABELS.noPrazo) {
                buckets.noPrazo.pesoBruto += pesoBruto;
                buckets.noPrazo.valorNota += valorNota;
                buckets.noPrazo.qtd += 1;
            }
            if (!Object.prototype.hasOwnProperty.call(statusSeries, statusNorm)) {
                statusNorm = STATUS_LABELS.outros;
            }
            statusSeries[statusNorm] += 1;
        });

        escreverKpi(buckets.entrega, kpis.entrega);
        escreverKpi(buckets.vendaBalcao, kpis.vendaBalcao);
        escreverKpi(buckets.atencao, kpis.atencao);
        escreverKpi(buckets.noPrazo, kpis.noPrazo);
        escreverKpi(buckets.totalPedidos, kpis.totalPedidos);

        if (statusChart) {
            statusChart.updateSeries([
                statusSeries[STATUS_LABELS.atrasado],
                statusSeries[STATUS_LABELS.atencao],
                statusSeries[STATUS_LABELS.noPrazo],
                statusSeries[STATUS_LABELS.outros],
            ]);
        }
    }
    tabela.on("tableBuilt", atualizarDashboard);
    tabela.on("dataLoaded", atualizarDashboard);
    tabela.on("dataFiltered", atualizarDashboard);
    tabela.on("renderComplete", atualizarDashboard);
    setTimeout(atualizarDashboard, 0);
})();





