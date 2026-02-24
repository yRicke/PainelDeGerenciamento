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

    var data = JSON.parse(dataElement.textContent || "[]");
    var dadosOriginais = Array.isArray(data) ? data.slice() : [];

    var ultimaPosicaoContainer = document.getElementById("filtro-ultima-posicao");
    var statusContainer = document.getElementById("filtro-status-estoque");
    var anoContainer = document.getElementById("filtro-ano-estoque");
    var mesContainer = document.getElementById("filtro-mes-estoque");
    var limparBtn = document.getElementById("limpar-filtros-estoque");
    var kpiValor = document.getElementById("kpi-estoque-valor");
    var kpiDataRecente = document.getElementById("kpi-estoque-data-recente");

    var mesesLabel = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    };

    var filtros = {
        ultima_posicao: "",
        status: "",
        ano: new Set(),
        mes: new Set(),
    };

    function formatMoeda(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            style: "currency",
            currency: "BRL",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function formatDataIsoParaBr(iso) {
        if (!iso) return "-";
        var p = String(iso).split("-");
        if (p.length !== 3) return "-";
        return p[2] + "/" + p[1] + "/" + p[0];
    }

    function normalizarTexto(valor, vazioLabel) {
        var texto = (valor || "").toString().trim();
        return texto || vazioLabel;
    }

    function valoresUnicosOrdenados(campo, vazioLabel, sorter) {
        var setValores = new Set();
        dadosOriginais.forEach(function (item) {
            setValores.add(normalizarTexto(item[campo], vazioLabel));
        });
        var arr = Array.from(setValores);
        return arr.sort(sorter || function (a, b) { return String(a).localeCompare(String(b), "pt-BR"); });
    }

    function criarBotaoFiltro(valor, onToggle) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "carteira-filtro-btn";
        btn.textContent = valor;
        btn.addEventListener("click", function () {
            onToggle(btn, valor);
            aplicarFiltros();
        });
        return btn;
    }

    function montarFiltroUnico(container, valores, chave) {
        if (!container) return;
        container.innerHTML = "";
        valores.forEach(function (valor) {
            var btn = criarBotaoFiltro(valor, function (elemento, token) {
                var ativo = elemento.classList.contains("is-active");
                Array.from(container.querySelectorAll(".carteira-filtro-btn")).forEach(function (b) {
                    b.classList.remove("is-active");
                });
                if (!ativo) {
                    elemento.classList.add("is-active");
                    filtros[chave] = token;
                } else {
                    filtros[chave] = "";
                }
            });
            container.appendChild(btn);
        });
    }

    function montarFiltroMultiplo(container, valores, chave, formatLabel) {
        if (!container) return;
        container.innerHTML = "";
        valores.forEach(function (valor) {
            var label = formatLabel ? formatLabel(valor) : valor;
            var btn = criarBotaoFiltro(label, function (elemento) {
                var token = String(valor);
                if (elemento.classList.contains("is-active")) {
                    elemento.classList.remove("is-active");
                    filtros[chave].delete(token);
                } else {
                    elemento.classList.add("is-active");
                    filtros[chave].add(token);
                }
            });
            container.appendChild(btn);
        });
    }

    var dataContagemMaisRecente = "";
    dadosOriginais.forEach(function (item) {
        var iso = item.data_contagem_iso || "";
        if (iso && (!dataContagemMaisRecente || iso > dataContagemMaisRecente)) {
            dataContagemMaisRecente = iso;
        }
    });
    var dataContagemAnteriorMaisRecente = "";
    dadosOriginais.forEach(function (item) {
        var iso = item.data_contagem_iso || "";
        if (!iso || iso >= dataContagemMaisRecente) return;
        if (!dataContagemAnteriorMaisRecente || iso > dataContagemAnteriorMaisRecente) {
            dataContagemAnteriorMaisRecente = iso;
        }
    });

    var statusValores = valoresUnicosOrdenados("status", "<SEM STATUS>");
    var anosValores = valoresUnicosOrdenados("ano_contagem", "<SEM ANO>", function (a, b) {
        return Number(b) - Number(a);
    });
    var mesesValores = valoresUnicosOrdenados("mes_contagem", "<SEM MES>", function (a, b) {
        return Number(a) - Number(b);
    });

    montarFiltroUnico(ultimaPosicaoContainer, ["Última posição", "Anterior"], "ultima_posicao");
    montarFiltroUnico(statusContainer, statusValores, "status");
    montarFiltroMultiplo(anoContainer, anosValores, "ano");
    montarFiltroMultiplo(mesContainer, mesesValores, "mes", function (v) {
        return mesesLabel[Number(v)] || String(v);
    });

    var tabela = window.TabulatorDefaults.create("#estoque-tabulator", {
        data: dadosOriginais,
        layout: "fitDataTable",
        movableColumns: true,
        pagination: "local",
        paginationSize: 100,
        initialSort: [
            {column: "data_contagem", dir: "desc"},
            {column: "id", dir: "desc"},
        ],
        locale: true,
        langs: {
            "pt-br": {
                pagination: {
                    first: "Primeira",
                    first_title: "Primeira página",
                    last: "Última",
                    last_title: "Última página",
                    prev: "Anterior",
                    prev_title: "Página anterior",
                    next: "Próxima",
                    next_title: "Próxima página"
                }
            }
        },
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {
                title: "Nome Origem",
                field: "nome_origem",
                sorter: function (a, b, aRow, bRow) {
                    var aIso = (aRow.getData().nome_origem_iso || "");
                    var bIso = (bRow.getData().nome_origem_iso || "");
                    return aIso.localeCompare(bIso);
                },
            },
            {
                title: "Dt. Contagem",
                field: "data_contagem",
                sorter: function (a, b, aRow, bRow) {
                    var aIso = (aRow.getData().data_contagem_iso || "");
                    var bIso = (bRow.getData().data_contagem_iso || "");
                    return aIso.localeCompare(bIso);
                },
            },
            {title: "Status", field: "status"},
            {title: "Cód. Empresa", field: "codigo_empresa"},
            {title: "Cód. Produto", field: "produto_codigo"},
            {title: "Desc. Produto", field: "produto_descricao"},
            {title: "Qtd. Estoque", field: "qtd_estoque", hozAlign: "right"},
            {title: "Giro Mensal", field: "giro_mensal", hozAlign: "right"},
            {title: "Lead Time Fornecimento", field: "lead_time_fornecimento", hozAlign: "right"},
            {title: "Cód. Volume", field: "codigo_voume"},
            {title: "Custo Total", field: "custo_total", hozAlign: "right"},
            {title: "Reservado", field: "reservado", hozAlign: "right"},
            {title: "Pacote por Fardo", field: "pacote_por_fardo", hozAlign: "right"},
            {title: "SubTotal (Est-Pen)", field: "sub_total_est_pen", hozAlign: "right"},
            {title: "Estoque Mínimo", field: "estoque_minimo", hozAlign: "right"},
            {
                title: "PCP",
                cssClass: "pcp-group",
                headerHozAlign: "center",
                columns: [
                    {title: "Produção por Dia (FD)", field: "producao_por_dia_fd", hozAlign: "right", cssClass: "pcp-col"},
                    {title: "Total PCP Pacote", field: "total_pcp_pacote", hozAlign: "right", cssClass: "pcp-col"},
                    {title: "Total PCP Fardo", field: "total_pcp_fardo", hozAlign: "right", cssClass: "pcp-col"},
                    {title: "Dia de Produção", field: "dia_de_producao", hozAlign: "right", cssClass: "pcp-col"},
                    {title: "Cód. Local", field: "codigo_local", cssClass: "pcp-col"},
                ],
            },
            {
                title: "Acoes",
                field: "editar_url",
                formatter: function (cell) {
                    var url = cell.getValue();
                    return url ? '<a class="btn-primary" href="' + url + '">Editar</a>' : "";
                },
                hozAlign: "center",
            },
        ],
    });

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
        if (!filtros.ultima_posicao) {
            kpiDataRecente.textContent = "Nenhuma selecionada";
            return;
        }
        kpiDataRecente.textContent = formatDataIsoParaBr(dataMaisRecente);
    }

    function aplicarFiltros() {
        tabela.setFilter(function (row) {
            var statusValor = normalizarTexto(row.status, "<SEM STATUS>");
            var anoValor = String(row.ano_contagem || "");
            var mesValor = String(row.mes_contagem || "");
            var dataContagemIso = row.data_contagem_iso || "";

            if (filtros.status && filtros.status !== statusValor) return false;
            if (filtros.ano.size && !filtros.ano.has(anoValor)) return false;
            if (filtros.mes.size && !filtros.mes.has(mesValor)) return false;
            if (filtros.ultima_posicao === "Última posição") return dataContagemIso === dataContagemMaisRecente;
            if (filtros.ultima_posicao === "Anterior") {
                if (!dataContagemAnteriorMaisRecente) return false;
                return dataContagemIso === dataContagemAnteriorMaisRecente;
            }

            return true;
        });
    }

    if (limparBtn) {
        limparBtn.addEventListener("click", function () {
            filtros = {
                ultima_posicao: "",
                status: "",
                ano: new Set(),
                mes: new Set(),
            };
            document.querySelectorAll(".carteira-filtro-btn.is-active").forEach(function (btn) {
                btn.classList.remove("is-active");
            });
            tabela.clearFilter(true);
            tabela.clearHeaderFilter();
            atualizarDashboardComLinhas(dadosOriginais);
        });
    }

    tabela.on("dataFiltered", function (_filters, rows) {
        var dadosFiltrados = rows.map(function (row) { return row.getData(); });
        atualizarDashboardComLinhas(dadosFiltrados);
    });

    tabela.setLocale("pt-br");
    atualizarDashboardComLinhas(dadosOriginais);
})();


