(function () {
    var form = document.getElementById("upload-fretes-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-fretes");
    var input = document.getElementById("arquivo-fretes-input");
    var statusArquivo = document.getElementById("nome-arquivo-fretes-selecionado");
    var loadingStatus = document.getElementById("fretes-loading-status");
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
    var dataElement = document.getElementById("fretes-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var tipoFreteContainer = document.getElementById("filtro-frete-tipo-frete");
    var regiaoNomeContainer = document.getElementById("filtro-frete-regiao-nome");
    var cidadeNomeContainer = document.getElementById("filtro-frete-cidade-nome");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-fretes");

    var data = JSON.parse(dataElement.textContent || "[]");
    var dadosOriginais = Array.isArray(data) ? data.slice() : [];
    var filtrosSelecionados = {
        tipo_frete: new Set(),
        regiao_nome: new Set(),
        cidade_nome: new Set(),
    };

    function paraTexto(valor) {
        return String(valor || "").toLowerCase().trim();
    }

    function normalizarTexto(valor, vazioLabel) {
        var texto = (valor || "").toString().trim();
        return texto || vazioLabel;
    }

    function valoresUnicosOrdenados(campo, vazioLabel) {
        var setValores = new Set();
        dadosOriginais.forEach(function (item) {
            setValores.add(normalizarTexto(item[campo], vazioLabel));
        });
        return Array.from(setValores).sort(function (a, b) {
            return a.localeCompare(b, "pt-BR");
        });
    }

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
            aplicarFiltrosExibicao();
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

    var table = window.TabulatorDefaults.create("#fretes-tabulator", {
        data: dadosOriginais,
        columns: [
            { title: "ID", field: "id", width: 80, hozAlign: "center" },
            { title: "Cidade Código", field: "cidade_codigo" },
            { title: "Cidade Nome", field: "cidade_nome" },
            { title: "UF Código", field: "unidade_federativa_codigo" },
            { title: "UF Sigla", field: "unidade_federativa_sigla" },
            { title: "Região Código", field: "regiao_codigo" },
            { title: "Região Nome", field: "regiao_nome" },
            { title: "Valor Frete Comercial", field: "valor_frete_comercial", hozAlign: "right" },
            { title: "Data/Hora Alteração", field: "data_hora_alteracao" },
            { title: "Valor Frete Mínimo", field: "valor_frete_minimo", hozAlign: "right" },
            { title: "Valor Frete Tonelada", field: "valor_frete_tonelada", hozAlign: "right" },
            { title: "Tipo Frete", field: "tipo_frete" },
            { title: "Valor Frete por KM", field: "valor_frete_por_km", hozAlign: "right" },
            { title: "Valor Taxa Entrada", field: "valor_taxa_entrada", hozAlign: "right" },
            { title: "Venda Mínima", field: "venda_minima", hozAlign: "right" },
            {
                title: "Acoes",
                field: "editar_url",
                formatter: function (cell) {
                    var url = cell.getValue();
                    return url ? '<a class="btn-primary" href="' + url + '">Editar</a>' : "";
                },
                hozAlign: "center"
            }
        ]
    });

    function aplicarFiltrosExibicao() {
        table.setFilter(function (dataItem) {
            var tipoFreteValor = normalizarTexto(dataItem.tipo_frete, "<SEM TIPO>");
            var regiaoNomeValor = normalizarTexto(dataItem.regiao_nome, "<SEM REGIAO>");
            var cidadeNomeValor = normalizarTexto(dataItem.cidade_nome, "<SEM CIDADE>");

            if (filtrosSelecionados.tipo_frete.size && !filtrosSelecionados.tipo_frete.has(tipoFreteValor)) return false;
            if (filtrosSelecionados.regiao_nome.size && !filtrosSelecionados.regiao_nome.has(regiaoNomeValor)) return false;
            if (filtrosSelecionados.cidade_nome.size && !filtrosSelecionados.cidade_nome.has(cidadeNomeValor)) return false;
            return true;
        });
    }

    montarGrupoFiltros(tipoFreteContainer, valoresUnicosOrdenados("tipo_frete", "<SEM TIPO>"), "tipo_frete");
    montarGrupoFiltros(regiaoNomeContainer, valoresUnicosOrdenados("regiao_nome", "<SEM REGIAO>"), "regiao_nome");
    montarGrupoFiltros(cidadeNomeContainer, valoresUnicosOrdenados("cidade_nome", "<SEM CIDADE>"), "cidade_nome");

    if (limparFiltrosBtn) {
        limparFiltrosBtn.addEventListener("click", function () {
            filtrosSelecionados = {
                tipo_frete: new Set(),
                regiao_nome: new Set(),
                cidade_nome: new Set(),
            };
            document.querySelectorAll(".carteira-filtro-btn.is-active").forEach(function (btn) {
                btn.classList.remove("is-active");
                btn.setAttribute("aria-pressed", "false");
            });
            table.clearFilter(true);
            table.clearHeaderFilter();
        });
    }

    table.setLocale("pt-br");
})();



