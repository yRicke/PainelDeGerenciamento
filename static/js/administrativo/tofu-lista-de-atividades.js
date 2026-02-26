(function () {
    var dataElement = document.getElementById("atividades-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var codigoContainer = document.getElementById("filtro-codigo");
    var gestorContainer = document.getElementById("filtro-gestor");
    var responsavelContainer = document.getElementById("filtro-responsavel");
    var indicadorContainer = document.getElementById("filtro-indicador");
    var limparBtn = document.getElementById("limpar-filtros-tabulator");

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
            codigo_projeto: new Set(),
            gestor: new Set(),
            responsavel: new Set(),
            indicador: new Set(),
        };
    }

    var filtrosSelecionados = criarEstadoSelecao();

    function criarBotaoFiltro(valor, onToggle) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "tofu-filtro-btn";
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

    var tabela = window.TabulatorDefaults.create("#atividades-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 70, hozAlign: "center"},
            {title: "Projeto", field: "projeto"},
            {title: "Codigo", field: "codigo_projeto"},
            {title: "Gestor", field: "gestor"},
            {title: "Responsavel", field: "responsavel"},
            {title: "Interlocutor", field: "interlocutor"},
            {title: "Prazo (semana)", field: "semana_de_prazo", hozAlign: "center"},
            {title: "Prev. Inicio", field: "data_previsao_inicio"},
            {title: "Prev. Termino", field: "data_previsao_termino"},
            {title: "Finalizada", field: "data_finalizada"},
            {title: "Indicador", field: "indicador"},
            {title: "Historico", field: "historico"},
            {title: "Tarefa", field: "tarefa"},
            {title: "Progresso (%)", field: "progresso", hozAlign: "center"},
            {
                title: "Acoes",
                field: "editar_url",
                formatter: function (cell) {
                    var url = cell.getValue();
                    return '<a class="btn-primary" href="' + url + '">Editar</a>';
                },
                hozAlign: "center",
            },
        ],
    });

    function aplicarFiltros() {
        tabela.setFilter(function (dataRow) {
            var codigoValor = normalizarTexto(dataRow.codigo_projeto, "<SEM CODIGO>");
            var gestorValor = normalizarTexto(dataRow.gestor, "<SEM GESTOR>");
            var responsavelValor = normalizarTexto(dataRow.responsavel, "<SEM RESPONSAVEL>");
            var indicadorValor = normalizarTexto(dataRow.indicador, "<SEM INDICADOR>");

            if (filtrosSelecionados.codigo_projeto.size && !filtrosSelecionados.codigo_projeto.has(codigoValor)) return false;
            if (filtrosSelecionados.gestor.size && !filtrosSelecionados.gestor.has(gestorValor)) return false;
            if (filtrosSelecionados.responsavel.size && !filtrosSelecionados.responsavel.has(responsavelValor)) return false;
            if (filtrosSelecionados.indicador.size && !filtrosSelecionados.indicador.has(indicadorValor)) return false;
            return true;
        });
    }

    montarGrupoFiltros(codigoContainer, valoresUnicosOrdenados("codigo_projeto", "<SEM CODIGO>"), "codigo_projeto");
    montarGrupoFiltros(gestorContainer, valoresUnicosOrdenados("gestor", "<SEM GESTOR>"), "gestor");
    montarGrupoFiltros(responsavelContainer, valoresUnicosOrdenados("responsavel", "<SEM RESPONSAVEL>"), "responsavel");
    montarGrupoFiltros(indicadorContainer, valoresUnicosOrdenados("indicador", "<SEM INDICADOR>"), "indicador");

    limparBtn.addEventListener("click", function () {
        filtrosSelecionados = criarEstadoSelecao();
        document.querySelectorAll(".tofu-filtro-btn.is-active").forEach(function (btn) {
            btn.classList.remove("is-active");
            btn.setAttribute("aria-pressed", "false");
        });
        tabela.clearFilter(true);
    });
})();



