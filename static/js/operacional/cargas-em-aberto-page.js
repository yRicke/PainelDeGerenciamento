(function () {
    var formCriacao = document.getElementById("criar-carga-form");
    if (!formCriacao) return;

    var dataInicio = formCriacao.querySelector('input[name="data_inicio"]');
    var dataPrevistaSaida = document.getElementById("data-prevista-saida-criar");
    var dataChegada = document.getElementById("data-chegada-criar");
    var dataFinalizacao = document.getElementById("data-finalizacao-criar");
    if (!dataInicio || !dataPrevistaSaida || !dataChegada || !dataFinalizacao) return;

    function atualizarEncadeamentoDatas() {
        var valorInicio = dataInicio.value || "";
        dataPrevistaSaida.disabled = !valorInicio;
        dataPrevistaSaida.min = valorInicio || "";
        if (!valorInicio) {
            dataPrevistaSaida.value = "";
            dataChegada.value = "";
            dataFinalizacao.value = "";
        }
        if (valorInicio && dataPrevistaSaida.value && dataPrevistaSaida.value < valorInicio) {
            dataPrevistaSaida.value = "";
            dataChegada.value = "";
            dataFinalizacao.value = "";
        }

        var valorSaida = dataPrevistaSaida.value || "";
        dataChegada.disabled = !valorSaida;
        dataChegada.min = valorSaida || "";
        if (!valorSaida) {
            dataChegada.value = "";
            dataFinalizacao.value = "";
        }
        if (valorSaida && dataChegada.value && dataChegada.value < valorSaida) {
            dataChegada.value = "";
            dataFinalizacao.value = "";
        }

        var valorChegada = dataChegada.value || "";
        dataFinalizacao.disabled = !valorChegada;
        dataFinalizacao.min = valorChegada || "";
        if (!valorChegada) {
            dataFinalizacao.value = "";
        }
        if (valorChegada && dataFinalizacao.value && dataFinalizacao.value < valorChegada) {
            dataFinalizacao.value = "";
        }
    }

    [dataInicio, dataPrevistaSaida, dataChegada, dataFinalizacao].forEach(function (input) {
        input.addEventListener("change", atualizarEncadeamentoDatas);
        input.addEventListener("input", atualizarEncadeamentoDatas);
    });
    atualizarEncadeamentoDatas();
})();

(function () {
    var form = document.getElementById("upload-cargas-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-cargas");
    var input = document.getElementById("arquivo-cargas-input");
    var statusArquivo = document.getElementById("nome-arquivo-cargas-selecionado");
    var loadingStatus = document.getElementById("cargas-loading-status");
    var confirmarInput = document.getElementById("confirmar-substituicao-input");
    var temArquivoExistente = form.getAttribute("data-tem-arquivo-existente") === "1";

    function iniciarCarregamento() {
        form.classList.add("is-loading");
        loadingStatus.classList.add("is-visible");
    }

    function obterArquivoXls(files) {
        if (!files || !files.length) return null;
        var arquivo = files[0];
        if (!arquivo || !arquivo.name || !arquivo.name.toLowerCase().endsWith(".xls")) {
            return null;
        }
        return arquivo;
    }

    function atualizarStatus(arquivo) {
        if (!arquivo) {
            statusArquivo.textContent = "";
            return;
        }
        statusArquivo.textContent = "Arquivo selecionado: " + arquivo.name;
    }

    function selecionarArquivo(files) {
        var arquivo = obterArquivoXls(files);
        if (!arquivo) {
            window.alert("Selecione um arquivo .xls válido.");
            input.value = "";
            atualizarStatus(null);
            return;
        }
        atualizarStatus(arquivo);
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
        input.files = event.dataTransfer.files;
        selecionarArquivo(input.files);
    });

    input.addEventListener("change", function () {
        selecionarArquivo(input.files);
    });

    form.addEventListener("submit", function (event) {
        var arquivo = obterArquivoXls(input.files);
        if (!arquivo) {
            event.preventDefault();
            window.alert("Selecione um arquivo .xls para continuar.");
            return;
        }

        if (temArquivoExistente) {
            var confirmou = window.confirm(
                "Já existe arquivo na pasta. Deseja substituir e mover o arquivo antigo para subscritos?"
            );
            if (!confirmou) {
                event.preventDefault();
                return;
            }
            confirmarInput.value = "1";
        }

        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("cargas-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var kpiTotal = document.getElementById("kpi-cargas-em-aberto");
    var kpiNoPrazo = document.getElementById("kpi-cargas-no-prazo");
    var kpiForaPrazo = document.getElementById("kpi-cargas-fora-prazo");

    var data = JSON.parse(dataElement.textContent || "[]");
    var dadosOriginais = Array.isArray(data) ? data.slice() : [];

    function atualizarDashboard(dadosFiltrados) {
        if (!kpiTotal || !kpiNoPrazo || !kpiForaPrazo) return;

        var total = dadosFiltrados.length;
        var foraPrazo = dadosFiltrados.filter(function (item) {
            return Boolean(item.verificacao);
        }).length;

        kpiTotal.textContent = String(total);
        kpiForaPrazo.textContent = String(foraPrazo);
        kpiNoPrazo.textContent = String(total - foraPrazo);
    }

    function ensureFilterColumns(section) {
        if (!section) return null;

        var left = section.querySelector('[data-module-filter-column="left"]');
        var right = section.querySelector('[data-module-filter-column="right"]');
        if (left && right) {
            return { left: left, right: right };
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
            left.id = "cargas-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "cargas-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return { left: left, right: right };
    }

    function formatTextoOuVazio(valor) {
        var texto = String(valor === null || valor === undefined ? "" : valor).trim();
        return texto || "(Vazio)";
    }

    function ordenarTexto(a, b) {
        return String(a.label || "").localeCompare(String(b.label || ""), "pt-BR", {
            sensitivity: "base",
            numeric: true,
        });
    }

    function obterStatusCritico(rowData) {
        return Number((rowData && rowData.critica) || 0) > 0 ? "Fora do Prazo" : "No Prazo";
    }

    function criarDefinicoesFiltrosCargas() {
        return [
            {
                key: "situacao",
                label: "Situa\u00e7\u00e3o",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.situacao : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "status",
                label: "Status",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.status : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "verificacao_texto",
                label: "Verifica\u00e7\u00e3o",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.verificacao_texto : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "status_critico",
                label: "Status Cr\u00edtico",
                singleSelect: true,
                extractValue: function (rowData) {
                    return obterStatusCritico(rowData);
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "nome_fantasia_empresa",
                label: "Nome Empresa",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.nome_fantasia_empresa : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
        ];
    }

    function configurarFiltrosExternos(tabelaRef, registros, secFiltros) {
        if (!secFiltros || !window.ModuleFilterCore) return null;

        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholderFiltros = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholderFiltros) placeholderFiltros.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (!filtroColumns || !filtroColumns.left || !filtroColumns.right) return null;

        var filtrosExternos = window.ModuleFilterCore.create({
            data: registros,
            definitions: criarDefinicoesFiltrosCargas(),
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

        return {
            secFiltros: secFiltros,
            filtrosExternos: filtrosExternos,
        };
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

    var colunas = [
            { title: "Ordem de Carga", field: "ordem_de_carga_codigo", headerFilter: "input" },
            {
                title: "Status Crítico",
                field: "critica",
                hozAlign: "center",
                formatter: function (cell) {
                    return Number(cell.getValue() || 0) > 0 ? "Fora do Prazo" : "No Prazo";
                }
            },
            { title: "Situação", field: "situacao", headerFilter: "input" },
            { title: "Status", field: "status", headerFilter: "input", hozAlign: "center" },
            { title: "Verificação", field: "verificacao_texto", headerFilter: "input", hozAlign: "center" },
            { title: "Prazo Máximo", field: "prazo_maximo_dias", hozAlign: "right" },
            { title: "Idade", field: "idade_dias", hozAlign: "right" },
            { title: "Criticidade", field: "critica", hozAlign: "center" },
            { title: "Nome do Parceiro (Motorista)", field: "nome_motorista", headerFilter: "input" },
            { title: "Data de Início", field: "data_inicio", hozAlign: "center" },
            { title: "Data Prevista para Saída", field: "data_prevista_saida", hozAlign: "center" },
            { title: "Data de Chegada", field: "data_chegada", hozAlign: "center" },
            { title: "Data de Finalização", field: "data_finalizacao", hozAlign: "center" },
            { title: "Nome Fantasia (Empresa)", field: "nome_fantasia_empresa", headerFilter: "input" },
            { title: "Nome Região", field: "regiao_nome", headerFilter: "input" }
        ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, dadosOriginais);
    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros) {
        secFiltros.dataset.moduleFiltersAuto = "off";
    }

    var table = window.TabulatorDefaults.create("#cargas-tabulator", {
        data: dadosOriginais,
        columns: colunas
    });
    var configFiltros = configurarFiltrosExternos(table, dadosOriginais, secFiltros);
    if (configFiltros) {
        registrarAcaoLimparFiltros(table, configFiltros.secFiltros, configFiltros.filtrosExternos);
    }

    table.on("dataFiltered", function (_filters, rows) {
        var dadosFiltrados = rows.map(function (row) {
            return row.getData();
        });
        atualizarDashboard(dadosFiltrados);
    });

    table.setLocale("pt-br");
    atualizarDashboard(dadosOriginais);
})();




