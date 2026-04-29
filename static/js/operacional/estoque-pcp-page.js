(function () {
    function vincularParametrosProdutoNoFormulario(formulario) {
        if (!formulario) return;
        var selectProduto = formulario.querySelector('select[name="produto_id"]');
        var inputPacote = formulario.querySelector('input[name="pacote_por_fardo"]');
        var inputMinimo = formulario.querySelector('input[name="estoque_minimo"]');
        var inputFd = formulario.querySelector('input[name="producao_por_dia_fd"]');
        if (!selectProduto || !inputPacote || !inputMinimo || !inputFd) return;

        function aplicarParametrosDaOpcaoSelecionada() {
            var opcao = selectProduto.options[selectProduto.selectedIndex];
            if (!opcao || !opcao.value) {
                inputPacote.value = "0";
                inputMinimo.value = "0";
                inputFd.value = "0";
                return;
            }
            inputPacote.value = opcao.dataset.pacotePorFardo || "0";
            inputFd.value = opcao.dataset.producaoPorDiaFd || "0";
            var parametrizado = (opcao.dataset.produtoParametrizado || "0") === "1";
            inputMinimo.value = parametrizado ? (opcao.dataset.estoqueMinimo || "0") : "12000";
        }

        selectProduto.addEventListener("change", aplicarParametrosDaOpcaoSelecionada);
        aplicarParametrosDaOpcaoSelecionada();
    }

    vincularParametrosProdutoNoFormulario(document.getElementById("criar-estoque-form"));

    var form = document.getElementById("upload-estoque-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-estoque");
    var input = document.getElementById("arquivos-estoque-input");
    var fileStatus = document.getElementById("nome-arquivos-estoque-selecionado");
    var loadingStatus = document.getElementById("estoque-loading-status");
    if (!dropzone || !input || !fileStatus || !loadingStatus) return;

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

    function contarPorTipo(arquivosXls) {
        var totais = {posicao: 0, reservado: 0};
        arquivosXls.forEach(function (file) {
            var caminho = String(file.webkitRelativePath || file.name || "").toLowerCase();
            var caminhoNormalizado = caminho;
            if (typeof caminhoNormalizado.normalize === "function") {
                caminhoNormalizado = caminhoNormalizado
                    .normalize("NFD")
                    .replace(/[\u0300-\u036f]/g, "");
            }
            if (caminhoNormalizado.indexOf("posicao") >= 0) totais.posicao += 1;
            if (caminho.indexOf("reservado") >= 0) totais.reservado += 1;
        });
        return totais;
    }

    function atualizarStatus(filesXls) {
        if (!filesXls.length) {
            fileStatus.textContent = "";
            return;
        }
        var totais = contarPorTipo(filesXls);
        fileStatus.textContent = (
            filesXls.length
            + " arquivo(s) .xls selecionado(s) - posição: "
            + totais.posicao
            + ", reservado: "
            + totais.reservado
            + "."
        );
    }

    function atribuirArquivosNoInput(filesXls) {
        var dt = new DataTransfer();
        filesXls.forEach(function (file) { dt.items.add(file); });
        input.files = dt.files;
    }

    function selecionarArquivos(files) {
        var arquivosXls = coletarArquivosXls(files);
        if (arquivosXls.length < 2) {
            window.alert("Selecione a pasta ESTOQUE com as subpastas de posição e reservado.");
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
        if (arquivosXls.length < 2) {
            event.preventDefault();
            window.alert("Selecione a pasta ESTOQUE com arquivos .xls das duas subpastas.");
            return;
        }
        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("estoque-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var POSICAO_ULTIMA = "ultima_posicao";
    var POSICAO_PENULTIMA = "penultima_posicao";
    var POSICAO_ANTERIORES = "anteriores_posicao";

    var data = JSON.parse(dataElement.textContent || "[]");
    var dadosOriginais = Array.isArray(data) ? data.slice() : [];
    var kpiValor = document.getElementById("kpi-estoque-valor");
    var kpiDataRecente = document.getElementById("kpi-estoque-data-recente");

    function formatMoeda(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            style: "currency",
            currency: "BRL",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function formatNumeroPtBr(valor, casasDecimais) {
        var numero = Number(valor || 0);
        if (!Number.isFinite(numero)) return "-";
        return numero.toLocaleString("pt-BR", {
            minimumFractionDigits: casasDecimais,
            maximumFractionDigits: casasDecimais,
        });
    }

    function formatDataIsoParaBr(iso) {
        if (!iso) return "-";
        var p = String(iso).split("-");
        if (p.length !== 3) return "-";
        return p[2] + "/" + p[1] + "/" + p[0];
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
            left.id = "estoque-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "estoque-filtros-coluna-direita";
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

    function formatarMes(mes) {
        var numero = Number(mes);
        if (!Number.isFinite(numero) || numero < 1 || numero > 12) return "(Vazio)";
        var nomes = [
            "Janeiro", "Fevereiro", "Mar\u00e7o", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ];
        return nomes[numero - 1];
    }

    function extrairDatasContagemOrdenadas(registros) {
        var unicas = Array.from(new Set(
            (Array.isArray(registros) ? registros : [])
                .map(function (item) { return item ? String(item.data_contagem_iso || "") : ""; })
                .filter(function (iso) { return iso; })
        ));
        unicas.sort(function (a, b) {
            return b.localeCompare(a);
        });
        return unicas;
    }

    function criarContextoPosicao(registros) {
        var datas = extrairDatasContagemOrdenadas(registros);
        return {
            ultima: datas[0] || "",
            penultima: datas[1] || "",
        };
    }

    function extrairPosicaoPorLinha(rowData, contextoPosicao) {
        if (!rowData) return "";
        var dataContagemIso = String(rowData.data_contagem_iso || "");
        if (!dataContagemIso) return "";
        if (contextoPosicao && dataContagemIso === contextoPosicao.ultima) return POSICAO_ULTIMA;
        if (contextoPosicao && dataContagemIso === contextoPosicao.penultima) return POSICAO_PENULTIMA;
        return POSICAO_ANTERIORES;
    }

    function formatarPosicao(token) {
        if (token === POSICAO_ULTIMA) return "\u00daltima Posi\u00e7\u00e3o";
        if (token === POSICAO_PENULTIMA) return "Pen\u00faltima Posi\u00e7\u00e3o";
        if (token === POSICAO_ANTERIORES) return "Anteriores";
        return "(Vazio)";
    }

    function ordenarPosicao(a, b) {
        var ordem = {};
        ordem[POSICAO_ULTIMA] = 0;
        ordem[POSICAO_PENULTIMA] = 1;
        ordem[POSICAO_ANTERIORES] = 2;
        var ao = ordem.hasOwnProperty(a.value) ? ordem[a.value] : 99;
        var bo = ordem.hasOwnProperty(b.value) ? ordem[b.value] : 99;
        return ao - bo;
    }

    function criarDefinicoesFiltrosEstoque(contextoPosicao) {
        return [
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
                key: "ano_contagem",
                label: "Ano",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.ano_contagem : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: function (a, b) {
                    return Number(b.value || 0) - Number(a.value || 0);
                },
            },
            {
                key: "mes_contagem",
                label: "M\u00eas",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.mes_contagem : "";
                },
                formatValue: function (valor) {
                    return formatarMes(valor);
                },
                sortOptions: function (a, b) {
                    return Number(a.value || 0) - Number(b.value || 0);
                },
            },
            {
                key: "posicao_contagem",
                label: "Posi\u00e7\u00e3o",
                singleSelect: false,
                extractValue: function (rowData) {
                    return extrairPosicaoPorLinha(rowData, contextoPosicao);
                },
                formatValue: function (valor) {
                    return formatarPosicao(valor);
                },
                sortOptions: ordenarPosicao,
            },
        ];
    }

    function aplicarRegraEspecialPosicao(filtrosExternos, keyPosicao) {
        if (!filtrosExternos || typeof filtrosExternos.toggleOption !== "function") return;
        if (typeof filtrosExternos.selectAllFilter !== "function") return;

        var toggleOriginal = filtrosExternos.toggleOption.bind(filtrosExternos);
        var selectAllOriginal = filtrosExternos.selectAllFilter.bind(filtrosExternos);

        filtrosExternos.toggleOption = function (filterKey, token) {
            if (filterKey !== keyPosicao) {
                return toggleOriginal(filterKey, token);
            }
            if (token !== POSICAO_ULTIMA && token !== POSICAO_PENULTIMA && token !== POSICAO_ANTERIORES) {
                return toggleOriginal(filterKey, token);
            }

            var atual = filtrosExternos.selectedTokensByKey[filterKey] || new Set();
            var proximo = new Set(atual);

            if (token === POSICAO_ANTERIORES) {
                proximo = proximo.has(POSICAO_ANTERIORES) ? new Set() : new Set([POSICAO_ANTERIORES]);
            } else {
                if (proximo.has(token)) {
                    proximo.delete(token);
                } else {
                    proximo.add(token);
                }
                proximo.delete(POSICAO_ANTERIORES);
            }

            filtrosExternos.selectedTokensByKey[filterKey] = proximo;
            filtrosExternos.render();
            if (typeof filtrosExternos._emitChange === "function") {
                filtrosExternos._emitChange({ type: "toggle-option", filterKey: filterKey, token: token });
            }
        };

        filtrosExternos.selectAllFilter = function (filterKey, shouldEmit) {
            if (filterKey !== keyPosicao) {
                return selectAllOriginal(filterKey, shouldEmit);
            }

            var options = filtrosExternos.optionsByKey[filterKey] || [];
            var tokens = new Set(options.map(function (item) { return item.token; }));
            var proximo = new Set();
            if (tokens.has(POSICAO_ULTIMA)) proximo.add(POSICAO_ULTIMA);
            if (tokens.has(POSICAO_PENULTIMA)) proximo.add(POSICAO_PENULTIMA);
            if (!proximo.size && tokens.has(POSICAO_ANTERIORES)) proximo.add(POSICAO_ANTERIORES);

            filtrosExternos.selectedTokensByKey[filterKey] = proximo;
            if (shouldEmit !== false) {
                filtrosExternos.render();
                if (typeof filtrosExternos._emitChange === "function") {
                    filtrosExternos._emitChange({ type: "select-all", filterKey: filterKey });
                }
            }
        };
    }

    function configurarFiltrosExternos(tabelaRef, registros, secFiltros, contextoPosicao) {
        if (!secFiltros || !window.ModuleFilterCore) return null;

        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholderFiltros = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholderFiltros) placeholderFiltros.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (!filtroColumns || !filtroColumns.left || !filtroColumns.right) return null;

        var filtrosExternos = window.ModuleFilterCore.create({
            data: registros,
            definitions: criarDefinicoesFiltrosEstoque(contextoPosicao),
            leftColumn: filtroColumns.left,
            rightColumn: filtroColumns.right,
            onChange: function () {
                if (typeof tabelaRef.refreshFilter === "function") {
                    tabelaRef.refreshFilter();
                }
            },
        });

        aplicarRegraEspecialPosicao(filtrosExternos, "posicao_contagem");

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
            {
                title: "Origem",
                field: "nome_origem",
                sorter: function (a, b, aRow, bRow) {
                    var aIso = (aRow.getData().nome_origem_iso || "");
                    var bIso = (bRow.getData().nome_origem_iso || "");
                    return aIso.localeCompare(bIso);
                },
            },
            {
                title: "Data de Contagem",
                field: "data_contagem",
                sorter: function (a, b, aRow, bRow) {
                    var aIso = (aRow.getData().data_contagem_iso || "");
                    var bIso = (bRow.getData().data_contagem_iso || "");
                    return aIso.localeCompare(bIso);
                },
            },
            {title: "Status", field: "status"},
            {title: "Código da Empresa", field: "codigo_empresa"},
            {title: "Código do Produto", field: "produto_codigo"},
            {title: "Descrição do Produto", field: "produto_descricao"},
            {title: "Quantidade em Estoque", field: "qtd_estoque", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Giro Mensal", field: "giro_mensal", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Lead Time de Fornecimento", field: "lead_time_fornecimento", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Código da Unidade de Volume", field: "codigo_volume"},
            {title: "Custo Total", field: "custo_total", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Reservado", field: "reservado", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Pacote por Fardo", field: "pacote_por_fardo", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "SubTotal", field: "sub_total_est_pen", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {title: "Estoque Mínimo", field: "estoque_minimo", hozAlign: "right", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
            {
                title: "PCP",
                cssClass: "pcp-group",
                headerHozAlign: "center",
                columns: [
                    {title: "Produção por Dia (FD)", field: "producao_por_dia_fd", hozAlign: "right", cssClass: "pcp-col", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
                    {title: "Total PCP Pacote", field: "total_pcp_pacote", hozAlign: "right", cssClass: "pcp-col", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
                    {title: "Total PCP Fardo", field: "total_pcp_fardo", hozAlign: "right", cssClass: "pcp-col", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 3); }},
                    {title: "Dia de Produção", field: "dia_de_producao", hozAlign: "right", cssClass: "pcp-col", formatter: function (cell) { return formatNumeroPtBr(cell.getValue(), 6); }},
                    {title: "Código do Local", field: "codigo_local", cssClass: "pcp-col"},
                ],
            },
        ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, dadosOriginais);
    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros) {
        secFiltros.dataset.moduleFiltersAuto = "off";
    }

    var tabela = window.TabulatorDefaults.create("#estoque-tabulator", {
        data: dadosOriginais,
        columns: colunas,
    });
    var contextoPosicao = criarContextoPosicao(dadosOriginais);
    var configFiltros = configurarFiltrosExternos(tabela, dadosOriginais, secFiltros, contextoPosicao);
    if (configFiltros) {
        registrarAcaoLimparFiltros(tabela, configFiltros.secFiltros, configFiltros.filtrosExternos);
    }

    function atualizarDashboardComLinhas(linhas) {
        if (!kpiValor || !kpiDataRecente) return;
        var custoTotal = 0;
        var dataMaisRecente = "";

        linhas.forEach(function (item) {
            custoTotal += Number(item.custo_total || 0);
            var iso = item.data_contagem_iso || "";
            if (iso && (!dataMaisRecente || iso > dataMaisRecente)) {
                dataMaisRecente = iso;
            }
        });

        kpiValor.textContent = formatMoeda(custoTotal);
        kpiDataRecente.textContent = formatDataIsoParaBr(dataMaisRecente);
    }

    tabela.on("dataFiltered", function (_filters, rows) {
        var dadosFiltrados = rows.map(function (row) { return row.getData(); });
        atualizarDashboardComLinhas(dadosFiltrados);
    });

    tabela.setLocale("pt-br");
    atualizarDashboardComLinhas(dadosOriginais);
})();
