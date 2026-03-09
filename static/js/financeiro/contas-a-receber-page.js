(function () {
    var form = document.getElementById("upload-contas-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-contas");
    var input = document.getElementById("arquivo-contas-input");
    var fileStatus = document.getElementById("nome-arquivo-contas-selecionado");
    var loadingStatus = document.getElementById("contas-loading-status");

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
    var dataElement = document.getElementById("contas-tabulator-data");
    var tabelaTarget = document.getElementById("contas-a-receber-tabulator");
    if (!dataElement || !tabelaTarget || !window.Tabulator || !window.TabulatorDefaults) return;

    var endpoint = String(dataElement.getAttribute("data-endpoint") || "").trim();
    if (!endpoint) return;

    var canEdit = String(dataElement.getAttribute("data-can-edit") || "0") === "1";
    var secFiltros = document.getElementById("sec-filtros");
    var kpiDataMaisRecenteEl = document.getElementById("contas-kpi-data-mais-recente");
    var kpiQuantidadeRecenteEl = document.getElementById("contas-kpi-quantidade-recente");
    var kpiValorRecenteEl = document.getElementById("contas-kpi-valor-recente");
    var kpiFaturamentoRecenteEl = document.getElementById("contas-kpi-faturamento-recente");
    var kpiInadimplenciaEl = document.getElementById("contas-kpi-inadimplencia");
    var kpiDataInicialEl = document.getElementById("contas-kpi-data-inicial");
    var kpiValorInicialEl = document.getElementById("contas-kpi-valor-inicial");
    var kpiDataFinalEl = document.getElementById("contas-kpi-data-final");
    var kpiValorFinalEl = document.getElementById("contas-kpi-valor-final");
    var kpiDiferencaPeriodoEl = document.getElementById("contas-kpi-diferenca-periodo");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});
    var formatadorPercentual = new Intl.NumberFormat("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});

    var FILTER_KEYS = {
        status: "status",
        intervalo: "intervalo",
        dataArquivoIso: "data_arquivo_iso",
        tituloDescricao: "titulo_descricao",
        nomeFantasiaEmpresa: "nome_fantasia_empresa",
        naturezaDescricao: "natureza_descricao",
        posicao: "posicao_contagem"
    };

    var POSICAO_ULTIMA = "ultima_posicao";
    var POSICAO_PENULTIMA = "penultima_posicao";
    var POSICAO_ANTERIORES = "anteriores_posicao";

    var estadoFiltros = {
        status: "",
        intervalo: new Set(),
        data_arquivo_iso: new Set(),
        titulo_descricao: new Set(),
        nome_fantasia_empresa: new Set(),
        natureza_descricao: new Set(),
        posicao_contagem: new Set()
    };

    var opcoesFiltros = {
        status: [],
        intervalo: [],
        data_arquivo_iso: [],
        titulo_descricao: [],
        nome_fantasia_empresa: [],
        natureza_descricao: [],
        posicao_contagem: []
    };

    function formatarDataBr(valor) {
        var texto = String(valor || "").trim();
        var match = texto.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (!match) return "--/--/----";
        return match[3] + "/" + match[2] + "/" + match[1];
    }

    function numeroResumo(resumo, chave, fallback) {
        var padrao = fallback !== undefined ? fallback : 0;
        if (!resumo || resumo[chave] === undefined || resumo[chave] === null) return Number(padrao);
        return Number(resumo[chave]);
    }

    function atualizarDashboardResumo(resumo) {
        var quantidadeDataMaisRecente = numeroResumo(
            resumo,
            "quantidade_data_mais_recente",
            numeroResumo(resumo, "quantidade", 0)
        );
        var valorDataMaisRecente = numeroResumo(
            resumo,
            "valor_data_mais_recente",
            numeroResumo(resumo, "valor_faturado", 0)
        );
        var faturamentoDataMaisRecente = numeroResumo(resumo, "faturamento_data_mais_recente", 0);
        var inadimplenciaPercentual = numeroResumo(resumo, "inadimplencia_percentual", 0);
        var valorDataInicial = numeroResumo(resumo, "valor_data_inicial", 0);
        var valorDataFinal = numeroResumo(resumo, "valor_data_final", valorDataMaisRecente);
        var diferencaPeriodo = numeroResumo(resumo, "diferenca_periodo", (valorDataFinal - valorDataInicial));

        if (kpiDataMaisRecenteEl) kpiDataMaisRecenteEl.textContent = formatarDataBr(resumo && resumo.data_mais_recente);
        if (kpiQuantidadeRecenteEl) kpiQuantidadeRecenteEl.textContent = String(quantidadeDataMaisRecente);
        if (kpiValorRecenteEl) kpiValorRecenteEl.textContent = formatadorMoeda.format(valorDataMaisRecente);
        if (kpiFaturamentoRecenteEl) kpiFaturamentoRecenteEl.textContent = formatadorMoeda.format(faturamentoDataMaisRecente);
        if (kpiInadimplenciaEl) kpiInadimplenciaEl.textContent = formatadorPercentual.format(inadimplenciaPercentual) + "%";
        if (kpiDataInicialEl) kpiDataInicialEl.textContent = formatarDataBr(resumo && resumo.data_inicial);
        if (kpiValorInicialEl) kpiValorInicialEl.textContent = formatadorMoeda.format(valorDataInicial);
        if (kpiDataFinalEl) kpiDataFinalEl.textContent = formatarDataBr(resumo && resumo.data_final);
        if (kpiValorFinalEl) kpiValorFinalEl.textContent = formatadorMoeda.format(valorDataFinal);
        if (kpiDiferencaPeriodoEl) {
            kpiDiferencaPeriodoEl.textContent = formatadorMoeda.format(diferencaPeriodo);
            kpiDiferencaPeriodoEl.classList.remove("is-positive", "is-negative", "is-neutral");
            if (diferencaPeriodo > 0) kpiDiferencaPeriodoEl.classList.add("is-positive");
            else if (diferencaPeriodo < 0) kpiDiferencaPeriodoEl.classList.add("is-negative");
            else kpiDiferencaPeriodoEl.classList.add("is-neutral");
        }
    }

    function normalizarOpcoes(lista) {
        if (!Array.isArray(lista)) return [];
        return lista
            .map(function (item) {
                var value = item && item.value !== undefined ? String(item.value) : "";
                var label = item && item.label !== undefined ? String(item.label) : value;
                return {value: value, label: label};
            })
            .filter(function (item) { return item.value !== ""; });
    }

    function valoresDisponiveisDaOpcao(chave) {
        return new Set((opcoesFiltros[chave] || []).map(function (item) { return item.value; }));
    }

    function manterSomenteValoresDisponiveis() {
        var statusDisponiveis = valoresDisponiveisDaOpcao(FILTER_KEYS.status);
        if (estadoFiltros.status && !statusDisponiveis.has(estadoFiltros.status)) {
            estadoFiltros.status = "";
        }

        [
            FILTER_KEYS.intervalo,
            FILTER_KEYS.dataArquivoIso,
            FILTER_KEYS.tituloDescricao,
            FILTER_KEYS.nomeFantasiaEmpresa,
            FILTER_KEYS.naturezaDescricao,
            FILTER_KEYS.posicao
        ].forEach(function (chave) {
            var disponiveis = valoresDisponiveisDaOpcao(chave);
            var proximo = new Set();
            estadoFiltros[chave].forEach(function (valor) {
                if (disponiveis.has(valor)) proximo.add(valor);
            });
            estadoFiltros[chave] = proximo;
        });

        if (estadoFiltros.posicao_contagem.has(POSICAO_ANTERIORES) && estadoFiltros.posicao_contagem.size > 1) {
            estadoFiltros.posicao_contagem = new Set([POSICAO_ANTERIORES]);
        }
    }

    function buildFilterCard(def) {
        var card = document.createElement("article");
        card.className = "module-filter-card";

        var head = document.createElement("div");
        head.className = "module-filter-card-head";

        var title = document.createElement("h3");
        title.textContent = def.titulo;
        head.appendChild(title);

        var actions = document.createElement("div");
        actions.className = "module-filter-card-actions";

        var btnTodos = document.createElement("button");
        btnTodos.type = "button";
        btnTodos.textContent = "Todos";
        btnTodos.addEventListener("click", def.onTodos);
        actions.appendChild(btnTodos);

        var btnLimpar = document.createElement("button");
        btnLimpar.type = "button";
        btnLimpar.textContent = "Limpar";
        btnLimpar.addEventListener("click", def.onLimpar);
        actions.appendChild(btnLimpar);

        head.appendChild(actions);
        card.appendChild(head);

        var meta = document.createElement("p");
        meta.className = "module-filter-card-meta";
        meta.textContent = String(def.selecionados) + " selecionado(s) de " + String(def.opcoes.length);
        card.appendChild(meta);

        var optionsWrap = document.createElement("div");
        optionsWrap.className = "module-filter-card-options";

        if (!def.opcoes.length) {
            var vazio = document.createElement("span");
            vazio.className = "module-filter-card-meta";
            vazio.textContent = "Sem opcoes para este filtro.";
            optionsWrap.appendChild(vazio);
        } else {
            def.opcoes.forEach(function (item) {
                var chip = document.createElement("button");
                chip.type = "button";
                chip.className = "module-filter-chip";
                if (def.isAtivo(item.value)) {
                    chip.classList.add("is-active");
                    chip.setAttribute("aria-pressed", "true");
                } else {
                    chip.setAttribute("aria-pressed", "false");
                }
                chip.textContent = item.label;
                chip.title = item.label;
                chip.addEventListener("click", function () {
                    def.onToggle(item.value);
                });
                optionsWrap.appendChild(chip);
            });
        }

        card.appendChild(optionsWrap);
        return card;
    }

    function ensureFilterColumns(section) {
        if (!section) return null;

        var left = section.querySelector('[data-module-filter-column="left"]');
        var right = section.querySelector('[data-module-filter-column="right"]');
        if (left && right) return {left: left, right: right};

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
            left.id = "contas-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "contas-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    function encodeMultiSet(setRef) {
        return Array.from(setRef).join("||");
    }

    function buildProgrammaticFilters() {
        var filtros = [];

        if (estadoFiltros.status) {
            filtros.push({field: FILTER_KEYS.status, type: "=", value: estadoFiltros.status});
        }

        [
            FILTER_KEYS.intervalo,
            FILTER_KEYS.dataArquivoIso,
            FILTER_KEYS.tituloDescricao,
            FILTER_KEYS.nomeFantasiaEmpresa,
            FILTER_KEYS.naturezaDescricao,
            FILTER_KEYS.posicao
        ].forEach(function (chave) {
            if (!estadoFiltros[chave].size) return;
            filtros.push({
                field: chave,
                type: "in",
                value: encodeMultiSet(estadoFiltros[chave])
            });
        });

        return filtros;
    }

    function aplicarFiltrosExternos() {
        tabela.setFilter(buildProgrammaticFilters());
        tabela.setPage(1);
    }

    function toggleStatus(valor) {
        estadoFiltros.status = estadoFiltros.status === valor ? "" : valor;
        renderizarFiltrosExternos();
        aplicarFiltrosExternos();
    }

    function toggleMulti(chave, valor) {
        if (estadoFiltros[chave].has(valor)) estadoFiltros[chave].delete(valor);
        else estadoFiltros[chave].add(valor);
        renderizarFiltrosExternos();
        aplicarFiltrosExternos();
    }

    function togglePosicao(valor) {
        if (valor === POSICAO_ANTERIORES) {
            if (estadoFiltros.posicao_contagem.has(POSICAO_ANTERIORES)) {
                estadoFiltros.posicao_contagem = new Set();
            } else {
                estadoFiltros.posicao_contagem = new Set([POSICAO_ANTERIORES]);
            }
        } else {
            if (estadoFiltros.posicao_contagem.has(valor)) {
                estadoFiltros.posicao_contagem.delete(valor);
            } else {
                estadoFiltros.posicao_contagem.add(valor);
            }
            estadoFiltros.posicao_contagem.delete(POSICAO_ANTERIORES);
        }

        renderizarFiltrosExternos();
        aplicarFiltrosExternos();
    }

    function selectAllMulti(chave) {
        estadoFiltros[chave] = new Set((opcoesFiltros[chave] || []).map(function (item) { return item.value; }));
        renderizarFiltrosExternos();
        aplicarFiltrosExternos();
    }

    function selectAllPosicao() {
        var opcoes = opcoesFiltros.posicao_contagem || [];
        var temUltima = opcoes.some(function (item) { return item.value === POSICAO_ULTIMA; });
        var temPenultima = opcoes.some(function (item) { return item.value === POSICAO_PENULTIMA; });
        var proximo = new Set();
        if (temUltima) proximo.add(POSICAO_ULTIMA);
        if (temPenultima) proximo.add(POSICAO_PENULTIMA);
        if (!proximo.size && opcoes.some(function (item) { return item.value === POSICAO_ANTERIORES; })) {
            proximo.add(POSICAO_ANTERIORES);
        }
        estadoFiltros.posicao_contagem = proximo;
        renderizarFiltrosExternos();
        aplicarFiltrosExternos();
    }

    function limparFiltro(chave) {
        if (chave === FILTER_KEYS.status) estadoFiltros.status = "";
        else estadoFiltros[chave] = new Set();
        renderizarFiltrosExternos();
        aplicarFiltrosExternos();
    }

    function clearAllExternalFilters() {
        estadoFiltros.status = "";
        estadoFiltros.intervalo = new Set();
        estadoFiltros.data_arquivo_iso = new Set();
        estadoFiltros.titulo_descricao = new Set();
        estadoFiltros.nome_fantasia_empresa = new Set();
        estadoFiltros.natureza_descricao = new Set();
        estadoFiltros.posicao_contagem = new Set();
        renderizarFiltrosExternos();
        tabela.setFilter([]);
        tabela.setPage(1);
    }

    function renderizarFiltrosExternos() {
        if (!secFiltros) return;
        var columns = ensureFilterColumns(secFiltros);
        if (!columns || !columns.left || !columns.right) return;

        columns.left.innerHTML = "";
        columns.right.innerHTML = "";

        columns.left.appendChild(buildFilterCard({
            titulo: "Status",
            opcoes: opcoesFiltros.status,
            selecionados: estadoFiltros.status ? 1 : 0,
            isAtivo: function (valor) { return estadoFiltros.status === valor; },
            onToggle: toggleStatus,
            onTodos: function () { limparFiltro(FILTER_KEYS.status); },
            onLimpar: function () { limparFiltro(FILTER_KEYS.status); }
        }));

        columns.left.appendChild(buildFilterCard({
            titulo: "Intervalo",
            opcoes: opcoesFiltros.intervalo,
            selecionados: estadoFiltros.intervalo.size,
            isAtivo: function (valor) { return estadoFiltros.intervalo.has(valor); },
            onToggle: function (valor) { toggleMulti(FILTER_KEYS.intervalo, valor); },
            onTodos: function () { selectAllMulti(FILTER_KEYS.intervalo); },
            onLimpar: function () { limparFiltro(FILTER_KEYS.intervalo); }
        }));

        columns.left.appendChild(buildFilterCard({
            titulo: "Data Arquivo",
            opcoes: opcoesFiltros.data_arquivo_iso,
            selecionados: estadoFiltros.data_arquivo_iso.size,
            isAtivo: function (valor) { return estadoFiltros.data_arquivo_iso.has(valor); },
            onToggle: function (valor) { toggleMulti(FILTER_KEYS.dataArquivoIso, valor); },
            onTodos: function () { selectAllMulti(FILTER_KEYS.dataArquivoIso); },
            onLimpar: function () { limparFiltro(FILTER_KEYS.dataArquivoIso); }
        }));

        columns.left.appendChild(buildFilterCard({
            titulo: "Descricao (Tipo de Titulo)",
            opcoes: opcoesFiltros.titulo_descricao,
            selecionados: estadoFiltros.titulo_descricao.size,
            isAtivo: function (valor) { return estadoFiltros.titulo_descricao.has(valor); },
            onToggle: function (valor) { toggleMulti(FILTER_KEYS.tituloDescricao, valor); },
            onTodos: function () { selectAllMulti(FILTER_KEYS.tituloDescricao); },
            onLimpar: function () { limparFiltro(FILTER_KEYS.tituloDescricao); }
        }));

        columns.right.appendChild(buildFilterCard({
            titulo: "Nome Fantasia (Empresa)",
            opcoes: opcoesFiltros.nome_fantasia_empresa,
            selecionados: estadoFiltros.nome_fantasia_empresa.size,
            isAtivo: function (valor) { return estadoFiltros.nome_fantasia_empresa.has(valor); },
            onToggle: function (valor) { toggleMulti(FILTER_KEYS.nomeFantasiaEmpresa, valor); },
            onTodos: function () { selectAllMulti(FILTER_KEYS.nomeFantasiaEmpresa); },
            onLimpar: function () { limparFiltro(FILTER_KEYS.nomeFantasiaEmpresa); }
        }));

        columns.right.appendChild(buildFilterCard({
            titulo: "Descricao (Natureza)",
            opcoes: opcoesFiltros.natureza_descricao,
            selecionados: estadoFiltros.natureza_descricao.size,
            isAtivo: function (valor) { return estadoFiltros.natureza_descricao.has(valor); },
            onToggle: function (valor) { toggleMulti(FILTER_KEYS.naturezaDescricao, valor); },
            onTodos: function () { selectAllMulti(FILTER_KEYS.naturezaDescricao); },
            onLimpar: function () { limparFiltro(FILTER_KEYS.naturezaDescricao); }
        }));

        columns.right.appendChild(buildFilterCard({
            titulo: "Posicao",
            opcoes: opcoesFiltros.posicao_contagem,
            selecionados: estadoFiltros.posicao_contagem.size,
            isAtivo: function (valor) { return estadoFiltros.posicao_contagem.has(valor); },
            onToggle: togglePosicao,
            onTodos: selectAllPosicao,
            onLimpar: function () { limparFiltro(FILTER_KEYS.posicao); }
        }));
    }

    function atualizarOpcoesFiltrosExternos(payload) {
        var external = payload && payload.external_filters ? payload.external_filters : {};

        opcoesFiltros.status = normalizarOpcoes(external.status);
        opcoesFiltros.intervalo = normalizarOpcoes(external.intervalo);
        opcoesFiltros.data_arquivo_iso = normalizarOpcoes(external.data_arquivo_iso);
        opcoesFiltros.titulo_descricao = normalizarOpcoes(external.titulo_descricao);
        opcoesFiltros.nome_fantasia_empresa = normalizarOpcoes(external.nome_fantasia_empresa);
        opcoesFiltros.natureza_descricao = normalizarOpcoes(external.natureza_descricao);
        opcoesFiltros.posicao_contagem = normalizarOpcoes(external.posicao_contagem);

        manterSomenteValoresDisponiveis();
        renderizarFiltrosExternos();
    }

    function initSecaoFiltros() {
        if (!secFiltros) return;
        secFiltros.dataset.moduleFiltersAuto = "off";
        secFiltros.dataset.moduleFiltersManual = "true";

        var placeholder = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholder) placeholder.remove();

        ensureFilterColumns(secFiltros);
        renderizarFiltrosExternos();
    }

    function construirColunas() {
        var colunas = [
            {title: "Data de Negociacao", field: "data_negociacao"},
            {title: "Data de Vencimento", field: "data_vencimento"},
            {title: "Data do Arquivo", field: "data_arquivo"},
            {title: "Nome Fantasia (Empresa)", field: "nome_fantasia_empresa"},
            {title: "Nome do Parceiro", field: "parceiro_nome"},
            {title: "Numero da Nota", field: "numero_nota"},
            {title: "Valor do Desdobramento", field: "valor_desdobramento"},
            {title: "Valor Liquido", field: "valor_liquido"},
            {title: "Descricao do Tipo de Titulo", field: "titulo_descricao"},
            {title: "Descricao da Natureza", field: "natureza_descricao"},
            {title: "Descricao do Centro de Resultado", field: "centro_resultado_descricao"},
            {title: "Vendedor", field: "vendedor"},
            {title: "Receita/Despesa", field: "operacao_descricao"},
            {title: "Status", field: "status", width: 110, hozAlign: "center", headerFilterLiveFilter: false},
            {title: "Dias de Diferenca", field: "dias_diferenca", width: 130, hozAlign: "center", headerFilterLiveFilter: false},
            {title: "Intervalo", field: "intervalo", width: 130, headerFilterLiveFilter: false}
        ];

        colunas = colunas.map(function (coluna) {
            if (!coluna || coluna.headerFilter === false) return coluna;
            var proxima = Object.assign({}, coluna);
            if (proxima.headerFilterLiveFilter === undefined) {
                proxima.headerFilterLiveFilter = false;
            }
            return proxima;
        });

        if (!canEdit) return colunas;

        window.TabulatorDefaults.addEditActionColumnIfAny(colunas, [{editar_url: "#"}], {
            width: 110,
            formatter: function (cell) {
                var url = cell.getValue();
                if (!url) return "";
                return '<button type="button" class="btn-primary js-editar-conta">Editar</button>';
            },
            cellClick: function (event, cell) {
                var row = cell.getRow().getData();
                var target = event.target && event.target.closest ? event.target.closest(".js-editar-conta") : null;
                if (!target || !row.editar_url) return;
                window.location.href = row.editar_url;
            }
        });

        return colunas;
    }

    var tabela = window.TabulatorDefaults.create("#contas-a-receber-tabulator", {
        ajaxURL: endpoint,
        ajaxURLGenerator: function (url, config, params) {
            var sortersPayload = Array.isArray(params && params.sorters)
                ? params.sorters
                : (Array.isArray(params && params.sort) ? params.sort : []);
            var filtersPayload = Array.isArray(params && params.filter)
                ? params.filter
                : (Array.isArray(params && params.filters) ? params.filters : []);

            var query = new URLSearchParams();
            query.set("page", String(params && params.page ? params.page : 1));
            query.set("size", String(params && params.size ? params.size : 100));
            query.set("sorters", JSON.stringify(sortersPayload));
            query.set("sort", JSON.stringify(sortersPayload));
            query.set("filters", JSON.stringify(filtersPayload));
            query.set("filter", JSON.stringify(filtersPayload));
            return url + "?" + query.toString();
        },
        ajaxResponse: function (url, params, response) {
            atualizarDashboardResumo(response && response.summary ? response.summary : null);
            atualizarOpcoesFiltrosExternos(response || {});
            return response;
        },
        pagination: true,
        paginationMode: "remote",
        paginationSize: 100,
        sortMode: "remote",
        filterMode: "remote",
        columns: construirColunas(),
        freezeUX: {
            enabled: true
        }
    });

    function limparTodosFiltros() {
        clearAllExternalFilters();
        if (typeof tabela.clearHeaderFilter === "function") {
            tabela.clearHeaderFilter();
        }
        if (typeof tabela.setPage === "function") {
            tabela.setPage(1);
        }
    }

    function initAcoesLimparFiltros() {
        var limparFiltrosSidebarBtn = secFiltros ? secFiltros.querySelector(".module-filters-clear-all") : null;
        var limparFiltrosToolbarBtn = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
        if (limparFiltrosSidebarBtn) {
            limparFiltrosSidebarBtn.addEventListener("click", limparTodosFiltros);
        }
        if (limparFiltrosToolbarBtn) {
            limparFiltrosToolbarBtn.addEventListener("click", limparTodosFiltros);
        }
    }

    tabela.on("dataLoadError", function () {
        atualizarDashboardResumo({quantidade: 0, valor_faturado: 0});
    });

    initSecaoFiltros();
    initAcoesLimparFiltros();
})();
