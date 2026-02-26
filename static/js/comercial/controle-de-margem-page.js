(function () {
    var form = document.getElementById("upload-controle-margem-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-controle-margem");
    var input = document.getElementById("arquivo-controle-margem-input");
    var confirmInput = document.getElementById("confirmar-substituicao-input");
    var fileStatus = document.getElementById("nome-arquivo-controle-margem-selecionado");
    var loadingStatus = document.getElementById("controle-margem-loading-status");
    var temArquivoExistente = form.dataset.temArquivoExistente === "1";

    function validarExtensao(file) {
        if (!file) return false;
        var nome = file.name.toLowerCase();
        return nome.endsWith(".xls") || nome.endsWith(".xlsx");
    }

    function atualizarNomeArquivo() {
        if (!input.files || !input.files.length) {
            fileStatus.textContent = "";
            return;
        }
        fileStatus.textContent = "Arquivo selecionado: " + input.files[0].name;
    }

    function iniciarCarregamento() {
        form.classList.add("is-loading");
        if (loadingStatus) loadingStatus.classList.add("is-visible");
    }

    function confirmarSubstituicaoSeNecessario() {
        if (!temArquivoExistente) {
            confirmInput.value = "0";
            return true;
        }
        if (!window.confirm("Ja existe um arquivo na pasta. Deseja substituir o arquivo atual?")) return false;
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
        if (!validarExtensao(files[0])) {
            window.alert("Envie apenas arquivo .xls ou .xlsx.");
            return;
        }
        input.files = files;
        atualizarNomeArquivo();
    });

    input.addEventListener("change", function () {
        if (!input.files || !input.files.length) return;
        if (!validarExtensao(input.files[0])) {
            window.alert("Envie apenas arquivo .xls ou .xlsx.");
            input.value = "";
        }
        atualizarNomeArquivo();
    });

    form.addEventListener("submit", function (event) {
        if (!input.files || !input.files.length) {
            event.preventDefault();
            window.alert("Selecione um arquivo .xls ou .xlsx para continuar.");
            return;
        }
        if (!validarExtensao(input.files[0])) {
            event.preventDefault();
            window.alert("Envie apenas arquivo .xls ou .xlsx.");
            return;
        }
        if (temArquivoExistente && confirmInput.value !== "1" && !confirmarSubstituicaoSeNecessario()) {
            event.preventDefault();
            return;
        }
        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("controle-margem-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var possuiEdicao = data.some(function (item) { return Boolean(item.editar_url); });
    var filtroSituacaoContainer = document.getElementById("filtro-controle-situacao");
    var filtroDescricaoPerfilContainer = document.getElementById("filtro-controle-descricao-perfil");
    var filtroApelidoVendedorContainer = document.getElementById("filtro-controle-apelido-vendedor");
    var filtroNomeEmpresaContainer = document.getElementById("filtro-controle-nome-empresa");
    var filtroTipoVendaContainer = document.getElementById("filtro-controle-tipo-venda");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-controle-margem");
    var dashboardPedido = document.getElementById("dashboard-pedido");
    var dashboardCmv = document.getElementById("dashboard-cmv");
    var dashboardLucro = document.getElementById("dashboard-lucro");
    var dashboardMargem = document.getElementById("dashboard-margem");

    function fmtMoeda(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            style: "currency",
            currency: "BRL",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function fmtPercentualRatio(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", {
            style: "percent",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function normalizarSituacao(valor) {
        return String(valor || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();
    }

    function obterCorSituacao(situacao) {
        var situacaoNormalizada = normalizarSituacao(situacao);
        if (situacaoNormalizada === "roxo") return "#8e24aa";
        if (situacaoNormalizada === "vermelho") return "#e74c3c";
        if (situacaoNormalizada === "amarelo") return "#f4b000";
        if (situacaoNormalizada === "verde") return "#2f9e44";
        return "";
    }

    function atualizarDashboard() {
        var linhas = tabela.getData("active");
        if (!linhas || !linhas.length) {
            linhas = tabela.getData() || [];
        }

        var pedido = 0;
        var cmv = 0;
        linhas.forEach(function (item) {
            pedido += Number(item.vlr_nota || 0);
            cmv += Number(item.custo_total_produto || 0);
        });
        var lucro = pedido - cmv;
        var margem = pedido === 0 ? 0 : (lucro / pedido);

        if (dashboardPedido) dashboardPedido.textContent = fmtMoeda(pedido);
        if (dashboardCmv) dashboardCmv.textContent = fmtMoeda(cmv);
        if (dashboardLucro) dashboardLucro.textContent = fmtMoeda(lucro);
        if (dashboardMargem) dashboardMargem.textContent = fmtPercentualRatio(margem);
    }

    function normalizarTexto(valor, vazioLabel) {
        var texto = (valor || "").toString().trim();
        return texto || vazioLabel;
    }

    function valoresUnicosOrdenados(campo, vazioLabel) {
        var setValores = new Set();
        data.forEach(function (item) {
            setValores.add(normalizarTexto(item[campo], vazioLabel));
        });
        return Array.from(setValores).sort(function (a, b) {
            return a.localeCompare(b, "pt-BR");
        });
    }

    function criarEstadoSelecao() {
        return {
            situacao: new Set(),
            descricao_perfil: new Set(),
            apelido_vendedor: new Set(),
            nome_empresa: new Set(),
            tipo_venda: new Set(),
        };
    }

    var filtrosSelecionados = criarEstadoSelecao();

    function criarBotaoFiltro(valor, onToggle) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "carteira-filtro-btn";
        btn.textContent = valor;
        btn.setAttribute("aria-pressed", "false");
        btn.addEventListener("click", function () {
            btn.classList.toggle("is-active");
            var ativo = btn.classList.contains("is-active");
            btn.setAttribute("aria-pressed", ativo ? "true" : "false");
            onToggle(ativo, valor);
            aplicarFiltros();
        });
        return btn;
    }

    function montarGrupoFiltros(container, valores, chaveEstado) {
        if (!container) return;
        container.innerHTML = "";
        valores.forEach(function (valor) {
            var btn = criarBotaoFiltro(valor, function (ativo, valorToggle) {
                if (ativo) filtrosSelecionados[chaveEstado].add(valorToggle);
                else filtrosSelecionados[chaveEstado].delete(valorToggle);
            });
            container.appendChild(btn);
        });
    }

    function aplicarFiltros() {
        tabela.setFilter(function (item) {
            var situacao = normalizarTexto(item.situacao, "<SEM SITUACAO>");
            var descricaoPerfil = normalizarTexto(item.descricao_perfil, "<SEM DESCRICAO PERFIL>");
            var apelidoVendedor = normalizarTexto(item.apelido_vendedor, "<SEM APELIDO VENDEDOR>");
            var nomeEmpresa = normalizarTexto(item.nome_empresa, "<SEM NOME EMPRESA>");
            var tipoVenda = normalizarTexto(item.tipo_venda, "<SEM TIPO VENDA>");

            if (filtrosSelecionados.situacao.size && !filtrosSelecionados.situacao.has(situacao)) return false;
            if (filtrosSelecionados.descricao_perfil.size && !filtrosSelecionados.descricao_perfil.has(descricaoPerfil)) return false;
            if (filtrosSelecionados.apelido_vendedor.size && !filtrosSelecionados.apelido_vendedor.has(apelidoVendedor)) return false;
            if (filtrosSelecionados.nome_empresa.size && !filtrosSelecionados.nome_empresa.has(nomeEmpresa)) return false;
            if (filtrosSelecionados.tipo_venda.size && !filtrosSelecionados.tipo_venda.has(tipoVenda)) return false;
            return true;
        });
        atualizarDashboard();
    }

    var tabela = window.TabulatorDefaults.create("#controle-margem-tabulator", {
        data: data,
        columns: [
            {title: "Nro. Unico", field: "nro_unico", sorter: "number", headerFilter: "input"},
            {title: "Nome Empresa", field: "nome_empresa", headerFilter: "input"},
            {title: "Cod. Nome parceiro", field: "cod_nome_parceiro", headerFilter: "input"},
            {title: "Descricao (Perfil)", field: "descricao_perfil", headerFilter: "input"},
            {title: "Apelido (Vendedor)", field: "apelido_vendedor", headerFilter: "input"},
            {title: "Gerente", field: "gerente", headerFilter: "input"},
            {title: "Dt. Neg.", field: "dt_neg", headerFilter: "input"},
            {title: "Previsao de entrega", field: "previsao_entrega", headerFilter: "input"},
            {title: "Tipo da Venda", field: "tipo_venda", headerFilter: "input"},
            {title: "Vlr. Nota", field: "vlr_nota", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Custo Total do Produto", field: "custo_total_produto", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {
                title: "Margem Bruta",
                field: "margem_bruta",
                hozAlign: "right",
                formatter: function (cell) {
                    var valorFormatado = fmtPercentualRatio(cell.getValue());
                    var rowData = cell.getRow() ? cell.getRow().getData() : null;
                    var cor = obterCorSituacao(rowData ? rowData.situacao : "");
                    if (!cor) return valorFormatado;
                    var textoEscuro = normalizarSituacao(rowData && rowData.situacao) === "amarelo";
                    var corTexto = textoEscuro ? "#1f2937" : "#ffffff";
                    return '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:' + cor + ";color:" + corTexto + ';font-weight:600;">' + valorFormatado + "</span>";
                },
            },
            {title: "Lucro Bruto", field: "lucro_bruto", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Valor Tonelada Frete[SAFIA]", field: "valor_tonelada_frete_safia", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Peso bruto", field: "peso_bruto", hozAlign: "right"},
            {title: "Custo por KG", field: "custo_por_kg", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Vendas", field: "vendas", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Producao", field: "producao", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Operador Logistica", field: "operador_logistica", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Frete Distribuicao", field: "frete_distribuicao", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Total Logistica", field: "total_logistica", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Administracao", field: "administracao", hozAlign: "right", headerFilter: "input", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Financeiro", field: "financeiro", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Total Setores", field: "total_setores", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Valor Liquido", field: "valor_liquido", hozAlign: "right", formatter: function (cell) { return fmtMoeda(cell.getValue()); }},
            {title: "Margem Liquida", field: "margem_liquida", hozAlign: "right", formatter: function (cell) { return fmtPercentualRatio(cell.getValue()); }},
        ],
    });

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

    montarGrupoFiltros(filtroSituacaoContainer, valoresUnicosOrdenados("situacao", "<SEM SITUACAO>"), "situacao");
    montarGrupoFiltros(filtroDescricaoPerfilContainer, valoresUnicosOrdenados("descricao_perfil", "<SEM DESCRICAO PERFIL>"), "descricao_perfil");
    montarGrupoFiltros(filtroApelidoVendedorContainer, valoresUnicosOrdenados("apelido_vendedor", "<SEM APELIDO VENDEDOR>"), "apelido_vendedor");
    montarGrupoFiltros(filtroNomeEmpresaContainer, valoresUnicosOrdenados("nome_empresa", "<SEM NOME EMPRESA>"), "nome_empresa");
    montarGrupoFiltros(filtroTipoVendaContainer, valoresUnicosOrdenados("tipo_venda", "<SEM TIPO VENDA>"), "tipo_venda");

    if (limparFiltrosBtn) {
        limparFiltrosBtn.addEventListener("click", function () {
            filtrosSelecionados = criarEstadoSelecao();
            document.querySelectorAll(".carteira-filtro-btn.is-active").forEach(function (btn) {
                btn.classList.remove("is-active");
                btn.setAttribute("aria-pressed", "false");
            });
            tabela.clearFilter(true);
            tabela.clearHeaderFilter();
            atualizarDashboard();
        });
    }

    tabela.on("tableBuilt", atualizarDashboard);
    tabela.on("dataFiltered", atualizarDashboard);
    tabela.on("renderComplete", atualizarDashboard);
    setTimeout(atualizarDashboard, 0);
})();


