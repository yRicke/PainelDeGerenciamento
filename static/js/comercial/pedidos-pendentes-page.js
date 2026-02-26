(function () {
    var form = document.getElementById("upload-pedidos-pendentes-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-pedidos-pendentes");
    var input = document.getElementById("arquivo-pedidos-pendentes-input");
    var confirmInput = document.getElementById("confirmar-substituicao-input");
    var fileStatus = document.getElementById("nome-arquivo-pedidos-pendentes-selecionado");
    var temArquivoExistente = form.dataset.temArquivoExistente === "1";

    function atualizarNomeArquivo() {
        if (!input.files || !input.files.length) {
            fileStatus.textContent = "";
            return;
        }
        fileStatus.textContent = "Arquivo selecionado: " + input.files[0].name;
    }

    function validarExtensaoXlsx(file) {
        return file && file.name.toLowerCase().endsWith(".xlsx");
    }

    function confirmarSubstituicaoSeNecessario() {
        if (!temArquivoExistente) {
            confirmInput.value = "0";
            return true;
        }
        if (!window.confirm("Já existe um arquivo na pasta. Deseja substituir o arquivo atual?")) return false;
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
            window.alert("Envie apenas arquivo .xlsx.");
            return;
        }
        input.files = files;
        atualizarNomeArquivo();
    });

    input.addEventListener("change", function () {
        if (!input.files || !input.files.length) return;
        if (!validarExtensaoXlsx(input.files[0])) {
            window.alert("Envie apenas arquivo .xlsx.");
            input.value = "";
        }
        atualizarNomeArquivo();
    });

    form.addEventListener("submit", function (event) {
        if (!input.files || !input.files.length) {
            event.preventDefault();
            window.alert("Selecione um arquivo .xlsx para continuar.");
            return;
        }
        if (!validarExtensaoXlsx(input.files[0])) {
            event.preventDefault();
            window.alert("Envie apenas arquivo .xlsx.");
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
    var possuiEdicao = data.some(function (item) { return Boolean(item.editar_url); });
    var filtroStatusContainer = document.getElementById("filtro-pedidos-status");
    var filtroRotaContainer = document.getElementById("filtro-pedidos-rota");
    var filtroRegiaoContainer = document.getElementById("filtro-pedidos-regiao");
    var filtroTipoVendaContainer = document.getElementById("filtro-pedidos-tipo-venda");
    var filtroGerenteContainer = document.getElementById("filtro-pedidos-gerente");
    var limparFiltrosBtn = document.getElementById("limpar-filtros-pedidos");
    var chartContainer = document.getElementById("pedidos-status-chart");

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
        var texto = (status || "").toString().trim().toLowerCase();
        if (texto === "atencao" || texto === "atenção") return "Atenção";
        if (texto === "atrasado") return "Atrasado";
        if (texto === "no prazo") return "No Prazo";
        return "Other";
    }

    function normalizarTipoVenda(tipoVenda) {
        var texto = (tipoVenda || "").toString().trim().toLowerCase();
        if (texto.indexOf("venda balc") >= 0 || texto.indexOf("venda balcã") >= 0) return "vendaBalcao";
        if (texto.indexOf("entrega") >= 0) return "entrega";
        return "outro";
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
            rota: new Set(),
            regiao: new Set(),
            tipo_venda: new Set(),
            status: new Set(),
            gerente: new Set(),
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

    var statusChart = null;
    if (chartContainer && window.ApexCharts) {
        statusChart = new window.ApexCharts(chartContainer, {
            chart: {
                type: "donut",
                height: 290,
            },
            labels: ["Atrasado", "Atenção", "No Prazo", "Other"],
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
            {title: "Nro. Único", field: "numero_unico", headerFilter: "input"},
            {title: "Rota", field: "rota", headerFilter: "input"},
            {title: "Região", field: "regiao", headerFilter: "input"},
            {title: "Valor Tonelada Frete[SAFIA]", field: "valor_tonelada_frete_safia", headerFilter: "input"},
            {title: "Pendente", field: "pendente", headerFilter: "input"},
            {title: "Nome Cidade Parceiro [SAFIA]", field: "nome_cidade_parceiro_safia", headerFilter: "input"},
            {title: "Previsão de entrega", field: "previsao_entrega", headerFilter: "input"},
            {title: "Dt. Neg.", field: "dt_neg", headerFilter: "input"},
            {title: "Prazo Máximo", field: "prazo_maximo", hozAlign: "center", headerFilter: "input"},
            {title: "Dias Negociados", field: "dias_negociados", hozAlign: "center", headerFilter: "input"},
            {title: "Status", field: "status", headerFilter: "input"},
            {title: "Tipo da Venda", field: "tipo_venda", headerFilter: "input"},
            {title: "Nome Empresa", field: "nome_empresa", headerFilter: "input"},
            {title: "Cód. Nome Parceiro", field: "cod_nome_parceiro", headerFilter: "input"},
            {
                title: "Vlr. Nota",
                field: "vlr_nota",
                hozAlign: "right",
                formatter: "money",
                formatterParams: {decimal: ",", thousand: ".", symbol: "R$ ", symbolAfter: false, precision: 2},
            },
            {title: "Peso bruto", field: "peso_bruto", hozAlign: "right"},
            {title: "Peso", field: "peso", hozAlign: "right"},
            {title: "Peso liq. dos Itens", field: "peso_liq_itens", hozAlign: "right"},
            {title: "Apelido (Vendedor)", field: "apelido_vendedor", headerFilter: "input"},
            {title: "Gerente", field: "gerente", headerFilter: "input"},
            {title: "Data para Cálculo", field: "data_para_calculo", headerFilter: "input"},
            {title: "Descrição (Tipo de Negociação)", field: "descricao_tipo_negociacao", headerFilter: "input"},
            {title: "Nro. Nota", field: "nro_nota", headerFilter: "input"},
            {title: "Previsão do Carregamento", field: "previsao_do_carregamento", headerFilter: "input"},
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
            "Other": 0,
        };

        linhas.forEach(function (item) {
            var pesoBruto = Number(item.peso_bruto || 0);
            var valorNota = Number(item.vlr_nota || 0);

            buckets.totalPedidos.pesoBruto += pesoBruto;
            buckets.totalPedidos.valorNota += valorNota;
            buckets.totalPedidos.qtd += 1;

            var statusNorm = normalizarStatus(item.status);
            var tipoKey = normalizarTipoVenda(item.tipo_venda);
            if (statusNorm === "Atrasado" && (tipoKey === "entrega" || tipoKey === "vendaBalcao")) {
                buckets[tipoKey].pesoBruto += pesoBruto;
                buckets[tipoKey].valorNota += valorNota;
                buckets[tipoKey].qtd += 1;
            }
            if (statusNorm === "Atenção") {
                buckets.atencao.pesoBruto += pesoBruto;
                buckets.atencao.valorNota += valorNota;
                buckets.atencao.qtd += 1;
            }
            if (statusNorm === "No Prazo") {
                buckets.noPrazo.pesoBruto += pesoBruto;
                buckets.noPrazo.valorNota += valorNota;
                buckets.noPrazo.qtd += 1;
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
                statusSeries["Atrasado"],
                statusSeries["Atenção"],
                statusSeries["No Prazo"],
                statusSeries["Other"],
            ]);
        }
    }

    function aplicarFiltros() {
        tabela.setFilter(function (item) {
            var rota = normalizarTexto(item.rota, "<SEM ROTA>");
            var regiao = normalizarTexto(item.regiao, "<SEM REGIÃO>");
            var tipoVenda = normalizarTexto(item.tipo_venda, "<SEM TIPO DE VENDA>");
            var status = normalizarTexto(item.status, "<SEM STATUS>");
            var gerente = normalizarTexto(item.gerente, "<SEM GERENTE>");

            if (filtrosSelecionados.rota.size && !filtrosSelecionados.rota.has(rota)) return false;
            if (filtrosSelecionados.regiao.size && !filtrosSelecionados.regiao.has(regiao)) return false;
            if (filtrosSelecionados.tipo_venda.size && !filtrosSelecionados.tipo_venda.has(tipoVenda)) return false;
            if (filtrosSelecionados.status.size && !filtrosSelecionados.status.has(status)) return false;
            if (filtrosSelecionados.gerente.size && !filtrosSelecionados.gerente.has(gerente)) return false;
            return true;
        });
        atualizarDashboard();
    }

    montarGrupoFiltros(filtroRotaContainer, valoresUnicosOrdenados("rota", "<SEM ROTA>"), "rota");
    montarGrupoFiltros(filtroRegiaoContainer, valoresUnicosOrdenados("regiao", "<SEM REGIÃO>"), "regiao");
    montarGrupoFiltros(filtroTipoVendaContainer, valoresUnicosOrdenados("tipo_venda", "<SEM TIPO DE VENDA>"), "tipo_venda");
    montarGrupoFiltros(filtroStatusContainer, valoresUnicosOrdenados("status", "<SEM STATUS>"), "status");
    montarGrupoFiltros(filtroGerenteContainer, valoresUnicosOrdenados("gerente", "<SEM GERENTE>"), "gerente");

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

    tabela.on("tableBuilt", atualizarDashboard);
    tabela.on("dataLoaded", atualizarDashboard);
    tabela.on("dataFiltered", atualizarDashboard);
    tabela.on("renderComplete", atualizarDashboard);
    setTimeout(atualizarDashboard, 0);
})();


