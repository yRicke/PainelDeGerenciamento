(function () {
    var form = document.getElementById("upload-faturamento-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-faturamento");
    var input = document.getElementById("arquivo-faturamento-input");
    var fileStatus = document.getElementById("nome-arquivo-faturamento-selecionado");
    var loadingStatus = document.getElementById("faturamento-loading-status");

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

        iniciarCarregamento();
    });
})();

(function () {
    var dataElement = document.getElementById("faturamento-tabulator-data");
    if (!dataElement) return;

    function parseJsonPayload(texto, fallback, origem) {
        var raw = String(texto || "");
        var fallbackValue = fallback;
        if (fallbackValue === undefined) fallbackValue = null;
        if (!raw.trim()) return fallbackValue;
        try {
            return JSON.parse(raw);
        } catch (_err) {
            // Fallback para payload legado contendo NaN/Infinity.
            var sanitizado = raw
                .replace(/\bNaN\b/g, "null")
                .replace(/\b-Infinity\b/g, "null")
                .replace(/\bInfinity\b/g, "null");
            try {
                return JSON.parse(sanitizado);
            } catch (errSanitizado) {
                console.error("Falha ao ler payload JSON de " + String(origem || "faturamento") + ".", errSanitizado);
                return fallbackValue;
            }
        }
    }

    var data = parseJsonPayload(dataElement.textContent, [], "faturamento-tabulator-data");
    var metaConfigElement = document.getElementById("faturamento-meta-config-data");
    var pedidosPendentesElement = document.getElementById("faturamento-pedidos-pendentes-data");
    var parametrosMetasElement = document.getElementById("faturamento-parametros-metas-data");
    var vendedoresResumoBaseElement = document.getElementById("faturamento-vendedores-resumo-base-data");
    var metaConfig = metaConfigElement
        ? parseJsonPayload(metaConfigElement.textContent, {}, "faturamento-meta-config-data")
        : {};
    var pedidosPendentesData = pedidosPendentesElement
        ? parseJsonPayload(pedidosPendentesElement.textContent, [], "faturamento-pedidos-pendentes-data")
        : [];
    var parametrosMetasData = parametrosMetasElement
        ? parseJsonPayload(parametrosMetasElement.textContent, [], "faturamento-parametros-metas-data")
        : [];
    var vendedoresResumoBase = vendedoresResumoBaseElement
        ? parseJsonPayload(vendedoresResumoBaseElement.textContent, {}, "faturamento-vendedores-resumo-base-data")
        : {};
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
    var esconderMetasPerfilClientesEl = document.getElementById("faturamento-perfil-clientes-esconder-metas");
    var relogioMetaEl = document.getElementById("faturamento-reloginho-meta");
    var relogioRealEl = document.getElementById("faturamento-reloginho-real");
    var relogioPctEl = document.getElementById("faturamento-reloginho-pct");
    var chartTipoVendaEl = document.getElementById("faturamento-chart-tipo-venda");
    var chartVendedoresResumoEl = document.getElementById("faturamento-chart-vendedores-resumo");
    var vendedoresComVendaListaEl = document.getElementById("faturamento-vendedores-com-venda-lista");
    var vendedoresSemVendaListaEl = document.getElementById("faturamento-vendedores-sem-venda-lista");
    var vendedoresComVendaTotalEl = document.getElementById("faturamento-vendedores-com-venda-total");
    var vendedoresSemVendaTotalEl = document.getElementById("faturamento-vendedores-sem-venda-total");
    var chartLojaEl = document.getElementById("faturamento-chart-loja");
    var chartMensalEl = document.getElementById("faturamento-chart-mensal");
    var chartVendedoresEl = document.getElementById("faturamento-chart-vendedores");
    var chartTop10DiasEl = document.getElementById("faturamento-chart-top10-dias");
    var chartTop10ProdutosEl = document.getElementById("faturamento-chart-top10-produtos");
    var chartCidadeEl = document.getElementById("faturamento-chart-cidade");
    var chartPerfilClientesEl = document.getElementById("faturamento-chart-perfil-clientes");
    var perfilClientesTotalEl = document.getElementById("faturamento-perfil-clientes-total");
    var dashboardPdfButtonEl = document.getElementById("faturamento-dashboard-exportar-pdf");
    var dashboardPdfFormEl = document.getElementById("faturamento-dashboard-pdf-form");
    var dashboardPdfPayloadEl = document.getElementById("faturamento-dashboard-pdf-payload");
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});
    var formatadorMoedaCompacta = new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
        notation: "compact",
        compactDisplay: "short",
        minimumFractionDigits: 1,
        maximumFractionDigits: 2,
    });
    var nomesMeses = [
        "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ];
    var nomesMesesCurtos = [
        "jan", "fev", "mar", "abr", "mai", "jun",
        "jul", "ago", "set", "out", "nov", "dez",
    ];
    var chartLoja = null;
    var chartTipoVenda = null;
    var chartVendedoresResumo = null;
    var chartMensal = null;
    var chartVendedores = null;
    var chartTop10Dias = null;
    var chartTop10Produtos = null;
    var chartCidade = null;
    var chartPerfilClientes = null;
    var ultimoPerfilClientes = null;
    var tabelaRef = null;
    var filtrosExternosRef = null;
    var ultimoSnapshotDashboardPdf = null;
    var dashboardPdfExportInicializado = false;
    var dashboardPdfExportEmAndamento = false;

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

    function vendedorTokenResumo(valor) {
        var token = normalizeText(valor).replace(/\s+/g, " ").trim();
        if (!token || token === "sem gerente" || token === "<sem gerente>") return "";
        if (token === "sem vendedor" || token === "<sem vendedor>") return "<SEM VENDEDOR>";
        return toText(valor);
    }

    function construirMapaMetaPorPerfil(parametros) {
        var mapa = new Map();
        var itens = Array.isArray(parametros) ? parametros : [];

        itens.forEach(function (item) {
            var perfil = toText(item && item.descricao_perfil);
            if (!perfil) return;

            var chavePerfil = normalizeText(perfil);
            if (!chavePerfil) return;

            var metaValorRaw = item ? item.valor_meta_pd_acabado : null;
            if (metaValorRaw === null || metaValorRaw === undefined || metaValorRaw === "") return;

            var metaValor = Number(metaValorRaw);
            if (Number.isNaN(metaValor)) return;
            mapa.set(chavePerfil, metaValor);
        });

        return mapa;
    }

    var mapaMetaPerfil = construirMapaMetaPorPerfil(parametrosMetasData);

    var universoVendedores = (function () {
        var resultado = new Set();
        (Array.isArray(data) ? data : []).forEach(function (item) {
            var vendedor = vendedorTokenResumo(item && item.apelido_vendedor);
            if (vendedor) resultado.add(vendedor);
        });
        return resultado;
    })();

    function chaveMes(item) {
        var ano = Number(item && item.ano_faturamento ? item.ano_faturamento : 0);
        var mes = Number(item && item.mes_faturamento ? item.mes_faturamento : 0);
        if (!ano || !mes || mes < 1 || mes > 12) return "";
        return String(ano) + "-" + String(mes);
    }

    function extrairAnoMesFaturamento(item) {
        var ano = Number(item && item.ano_faturamento ? item.ano_faturamento : 0);
        var mes = Number(item && item.mes_faturamento ? item.mes_faturamento : 0);
        if (ano && mes >= 1 && mes <= 12) return {ano: ano, mes: mes};

        var iso = toText(item ? item.data_faturamento_iso : "");
        if (!iso) return {ano: 0, mes: 0};
        var partes = iso.split("-");
        if (partes.length !== 3) return {ano: 0, mes: 0};

        ano = Number(partes[0] || 0);
        mes = Number(partes[1] || 0);
        if (!ano || mes < 1 || mes > 12) return {ano: 0, mes: 0};
        return {ano: ano, mes: mes};
    }

    function formatDataBr(iso) {
        var texto = toText(iso);
        if (!texto) return "(Vazio)";
        var partes = texto.split("-");
        if (partes.length !== 3) return texto;
        return partes[2] + "/" + partes[1] + "/" + partes[0];
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
            var anoMes = extrairAnoMesFaturamento(item);
            var atual = notasMap.get(chave);

            if (!atual) {
                notasMap.set(chave, {
                    valorNotaReferencia: valorNota,
                    valorUnicoMaximo: valorUnico,
                    nomeEmpresa: toText(item && item.nome_empresa),
                    vendedor: toText(item && item.apelido_vendedor),
                    gerente: toText(item && item.gerente),
                    produtoLabel: toText(item && item.produto_label),
                    quantidadeSaida: Number(item && item.quantidade_saida || 0),
                    dataIso: toText(item && item.data_faturamento_iso),
                    ano: anoMes.ano,
                    mes: anoMes.mes,
                });
                return;
            }

            if (!atual.valorNotaReferencia && valorNota) {
                atual.valorNotaReferencia = valorNota;
            }
            if (Math.abs(valorUnico) > Math.abs(atual.valorUnicoMaximo)) {
                atual.valorUnicoMaximo = valorUnico;
            }
            if (!atual.nomeEmpresa) {
                atual.nomeEmpresa = toText(item && item.nome_empresa);
            }
            if (!atual.vendedor) {
                atual.vendedor = toText(item && item.apelido_vendedor);
            }
            if (!atual.gerente) {
                atual.gerente = toText(item && item.gerente);
            }
            if (!atual.produtoLabel) {
                atual.produtoLabel = toText(item && item.produto_label);
            }
            if (!atual.quantidadeSaida && Number(item && item.quantidade_saida || 0)) {
                atual.quantidadeSaida = Number(item && item.quantidade_saida || 0);
            }
            if (!atual.dataIso) {
                atual.dataIso = toText(item && item.data_faturamento_iso);
            }
            if ((!atual.ano || !atual.mes) && anoMes.ano && anoMes.mes) {
                atual.ano = anoMes.ano;
                atual.mes = anoMes.mes;
            }
        });

        var total = 0;
        var notasConsolidadas = [];
        notasMap.forEach(function (nota) {
            var valorConsolidado = Number(nota.valorUnicoMaximo || 0);
            if (!valorConsolidado) {
                valorConsolidado = Number(nota.valorNotaReferencia || 0);
            }
            total += valorConsolidado;
            notasConsolidadas.push({
                valor: valorConsolidado,
                nomeEmpresa: nota.nomeEmpresa || "(Vazio)",
                vendedor: nota.vendedor || "",
                gerente: nota.gerente || "",
                produtoLabel: nota.produtoLabel || "",
                quantidadeSaida: Number(nota.quantidadeSaida || 0),
                dataIso: nota.dataIso || "",
                ano: Number(nota.ano || 0),
                mes: Number(nota.mes || 0),
            });
        });

        return {
            totalValorNota: total,
            quantidadeNotasUnicas: notasMap.size,
            notas: notasConsolidadas,
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

    function ordenarNomes(a, b) {
        return String(a || "").localeCompare(String(b || ""), "pt-BR", {
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

    function formatMoeda(valor) {
        return formatadorMoeda.format(Number(valor || 0));
    }

    function formatMoedaCompacta(valor) {
        return formatadorMoedaCompacta.format(Number(valor || 0));
    }

    function textoDeElemento(el, fallback) {
        var texto = el ? toText(el.textContent) : "";
        if (texto) return texto;
        return toText(fallback) || "-";
    }

    function valorFiltroTabelaParaTexto(valor) {
        if (Array.isArray(valor)) {
            var itens = valor
                .map(function (item) { return toText(item); })
                .filter(function (item) { return !!item; });
            return itens.length ? itens.join(", ") : "(Vazio)";
        }
        var texto = toText(valor);
        return texto || "(Vazio)";
    }

    function labelCampoFiltroTabela(campo) {
        var mapa = {
            nome_origem: "Nome Origem",
            data_faturamento: "Dt. do Faturamento",
            nome_empresa: "Nome Empresa",
            parceiro_label: "Parceiro",
            numero_nota: "Nro. Nota",
            valor_nota: "Vlr. Nota",
            participacao_venda_geral: "%Part. Venda Geral",
            participacao_venda_cliente: "%Part. Venda Cliente",
            valor_nota_unico: "Vlr. Nota (Unico)",
            quantidade_saida: "Qtd. Saida",
            status_nfe: "Status NF-e",
            apelido_vendedor: "Apelido (Vendedor)",
            operacao_descricao: "Descricao (Tipo de Operacao)",
            natureza_descricao: "Descricao (Natureza)",
            centro_resultado_descricao: "Descricao (Centro de Resultado)",
            tipo_movimento: "Tipo de Movimento",
            prazo_medio: "Prazo Medio",
            media_unica: "Media (Unica)",
            tipo_venda: "Tipo da Venda",
            produto_label: "Produto",
            cidade_parceiro: "Cidade Parceiro",
            gerente: "Gerente",
            descricao_perfil: "Descricao (Perfil)",
            valor_frete: "Valor Frete",
        };
        return mapa[campo] || campo;
    }

    function listarFiltrosTabelaAtivos() {
        if (!tabelaRef || typeof tabelaRef.getFilters !== "function") return [];
        var filtros = tabelaRef.getFilters(true);
        if (!Array.isArray(filtros)) return [];

        var linhas = [];
        filtros.forEach(function (filtro) {
            if (!filtro || typeof filtro !== "object") return;
            if (!toText(filtro.field)) return;
            var valor = filtro.value;
            if (valor === null || valor === undefined) return;
            if (typeof valor === "string" && !toText(valor)) return;

            var campoLabel = labelCampoFiltroTabela(toText(filtro.field));
            var sufixoTipo = toText(filtro.type);
            var tipoTexto = sufixoTipo && sufixoTipo !== "=" ? " (" + sufixoTipo + ")" : "";
            linhas.push(
                "Tabela - "
                + campoLabel
                + tipoTexto
                + ": "
                + valorFiltroTabelaParaTexto(valor)
            );
        });
        return linhas;
    }

    function listarFiltrosExternosAtivos() {
        if (!filtrosExternosRef || !Array.isArray(filtrosExternosRef.definitions)) return [];
        var linhas = [];

        filtrosExternosRef.definitions.forEach(function (definition) {
            var key = toText(definition && definition.key);
            if (!key) return;

            var selected = filtrosExternosRef.selectedTokensByKey
                ? filtrosExternosRef.selectedTokensByKey[key]
                : null;
            if (!selected || selected.size === 0) return;

            var opcoes = Array.isArray(filtrosExternosRef.optionsByKey && filtrosExternosRef.optionsByKey[key])
                ? filtrosExternosRef.optionsByKey[key]
                : [];
            var labelByToken = new Map();
            opcoes.forEach(function (opcao) {
                labelByToken.set(String(opcao.token), toText(opcao.label) || "(Vazio)");
            });

            var selecionados = Array.from(selected).map(function (token) {
                var keyToken = String(token);
                return labelByToken.get(keyToken) || toText(token) || "(Vazio)";
            });
            if (!selecionados.length) return;

            var titulo = toText(definition.label) || key;
            linhas.push("Filtro Externo - " + titulo + ": " + selecionados.join(", "));
        });

        return linhas;
    }

    function coletarFiltrosAtivosDashboardPdf() {
        var linhas = []
            .concat(listarFiltrosExternosAtivos())
            .concat(listarFiltrosTabelaAtivos());
        return linhas.length ? linhas : ["Nenhum filtro ativo."];
    }

    function montarSnapshotDashboardPdf(metricas) {
        var metricasAtuais = metricas || {};
        return {
            dashboard: {
                valor_faturamento: textoDeElemento(kpiValorFaturamentoEl, formatMoeda(metricasAtuais.valorFaturamento || 0)),
                meta_geral: textoDeElemento(kpiMetaGeralEl, formatMoeda(metricasAtuais.metaGeral || 0)),
                gap_faturamento: textoDeElemento(kpiGapFaturamentoEl, formatMoeda(metricasAtuais.gapFaturamento || 0)),
                prazo_medio: textoDeElemento(kpiPrazoMedioEl, String(metricasAtuais.prazoMedioArredondado || 0)),
                dias_uteis: textoDeElemento(kpiDiasUteisEl, String(metricasAtuais.diasUteisRestantes || 0)),
                meta_diaria: textoDeElemento(kpiMetaDiariaEl, formatMoeda(metricasAtuais.metaDiaria || 0)),
                pedidos_pendentes: textoDeElemento(kpiTotalPedidosPendentesEl, "R$ 0,00 / 0 dias uteis"),
                qtd_clientes: textoDeElemento(kpiQtdClientesEl, String(metricasAtuais.qtdClientes || 0)),
                participacao_venda_geral: textoDeElemento(
                    kpiParticipacaoVendaGeralEl,
                    formatPercentual((metricasAtuais.participacaoVendaGeral || 0) * 100, 2)
                ),
                incluir_pedidos_pendentes: incluirPedidosPendentesEl && incluirPedidosPendentesEl.checked ? "Sim" : "Nao",
                reloginho_meta: textoDeElemento(relogioMetaEl, formatMoeda(metricasAtuais.metaGeral || 0)),
                reloginho_real: textoDeElemento(relogioRealEl, formatMoeda(metricasAtuais.valorFaturamento || 0)),
                reloginho_percentual: textoDeElemento(
                    relogioPctEl,
                    formatPercentual(
                        (
                            Number(metricasAtuais.metaGeral || 0) > 0
                                ? (Number(metricasAtuais.valorFaturamento || 0) / Number(metricasAtuais.metaGeral || 0))
                                : 0
                        ) * 100,
                        2
                    )
                ),
                vendedores_com_venda_total: textoDeElemento(vendedoresComVendaTotalEl, "0"),
                vendedores_sem_venda_total: textoDeElemento(vendedoresSemVendaTotalEl, "0"),
                registros_ativos: String(Array.isArray(metricasAtuais.linhasDetalhadas) ? metricasAtuais.linhasDetalhadas.length : 0),
            },
            filtros_ativos: coletarFiltrosAtivosDashboardPdf(),
        };
    }

    function atualizarPayloadDashboardPdf(metricas) {
        ultimoSnapshotDashboardPdf = montarSnapshotDashboardPdf(metricas);
        if (!dashboardPdfPayloadEl) return;
        try {
            dashboardPdfPayloadEl.value = JSON.stringify(ultimoSnapshotDashboardPdf);
        } catch (_erro) {
            dashboardPdfPayloadEl.value = "{}";
        }
    }

    function descritoresGraficosDashboardPdf() {
        return [
            {chave: "tipo_venda", titulo: "Tipo da Venda", chart: chartTipoVenda},
            {chave: "vendedores_resumo", titulo: "Vendedores", chart: chartVendedoresResumo},
            {chave: "faturamento_loja", titulo: "Faturamento Loja", chart: chartLoja},
            {chave: "faturamento_mensal", titulo: "Faturamento Mensal", chart: chartMensal},
            {chave: "faturamento_vendedores", titulo: "Faturamento Vendedores", chart: chartVendedores},
            {chave: "top10_dias", titulo: "TOP 10 DIAS", chart: chartTop10Dias},
            {chave: "top10_produtos", titulo: "TOP 10 PRODUTOS", chart: chartTop10Produtos},
            {chave: "faturamento_cidade", titulo: "Faturamento por Cidade", chart: chartCidade},
            {chave: "perfil_clientes", titulo: "Perfil Clientes", chart: chartPerfilClientes},
        ];
    }

    function gerarImagemGraficoParaPdf(chart) {
        if (!chart || typeof chart.dataURI !== "function") {
            return Promise.resolve("");
        }
        try {
            return chart
                .dataURI({scale: 1, width: 920})
                .then(function (resultado) {
                    return toText(resultado && resultado.imgURI);
                })
                .catch(function () {
                    return "";
                });
        } catch (_erro) {
            return Promise.resolve("");
        }
    }

    function coletarGraficosDashboardPdf() {
        var descritores = descritoresGraficosDashboardPdf();
        var tarefas = descritores.map(function (item) {
            return gerarImagemGraficoParaPdf(item.chart).then(function (imgUri) {
                return {
                    chave: item.chave,
                    titulo: item.titulo,
                    img_uri: imgUri,
                };
            });
        });

        return Promise.all(tarefas).then(function (itens) {
            var payload = {};
            itens.forEach(function (item) {
                payload[item.chave] = {
                    titulo: item.titulo,
                    img_uri: item.img_uri || "",
                };
            });
            return payload;
        });
    }

    function restaurarBotaoExportacaoPdf(textoOriginal) {
        if (!dashboardPdfButtonEl) return;
        window.setTimeout(function () {
            dashboardPdfButtonEl.disabled = false;
            dashboardPdfButtonEl.textContent = textoOriginal;
            dashboardPdfExportEmAndamento = false;
        }, 1200);
    }

    function inicializarExportacaoDashboardPdf() {
        if (dashboardPdfExportInicializado) return;
        dashboardPdfExportInicializado = true;
        if (!dashboardPdfButtonEl || !dashboardPdfFormEl || !dashboardPdfPayloadEl) return;

        dashboardPdfButtonEl.addEventListener("click", function () {
            if (dashboardPdfExportEmAndamento) return;
            dashboardPdfExportEmAndamento = true;
            var textoOriginal = dashboardPdfButtonEl.textContent || "Baixar PDF do Dashboard";
            dashboardPdfButtonEl.disabled = true;
            dashboardPdfButtonEl.textContent = "Preparando PDF...";

            var linhasAtivas = [];
            if (tabelaRef && typeof tabelaRef.getData === "function") {
                linhasAtivas = tabelaRef.getData("active");
                if (!Array.isArray(linhasAtivas)) linhasAtivas = tabelaRef.getData() || [];
            }
            if (!Array.isArray(linhasAtivas) || !linhasAtivas.length) {
                linhasAtivas = Array.isArray(data) ? data : [];
            }

            var metricasAtuais = calcularMetricasDashboard(linhasAtivas);
            atualizarPayloadDashboardPdf(metricasAtuais);
            coletarGraficosDashboardPdf()
                .then(function (graficos) {
                    if (!ultimoSnapshotDashboardPdf || typeof ultimoSnapshotDashboardPdf !== "object") {
                        ultimoSnapshotDashboardPdf = {};
                    }
                    ultimoSnapshotDashboardPdf.graficos = graficos || {};
                    dashboardPdfPayloadEl.value = JSON.stringify(ultimoSnapshotDashboardPdf);
                    dashboardPdfFormEl.submit();
                })
                .catch(function () {
                    dashboardPdfFormEl.submit();
                })
                .then(function () {
                    restaurarBotaoExportacaoPdf(textoOriginal);
                }, function () {
                    restaurarBotaoExportacaoPdf(textoOriginal);
                });
        });
    }

    function labelMesAno(ano, mes) {
        if (!mes || mes < 1 || mes > 12) return "(Vazio)";
        var mesTexto = String(nomesMeses[mes - 1] || "").toUpperCase();
        return ano ? (mesTexto + "/" + String(ano)) : mesTexto;
    }

    function labelMesCurtoAno(chaveMesAno, incluirAno) {
        var texto = toText(chaveMesAno);
        if (!texto) return "(Vazio)";
        var partes = texto.split("-");
        if (partes.length !== 2) return texto;

        var ano = Number(partes[0] || 0);
        var mes = Number(partes[1] || 0);
        if (!mes || mes < 1 || mes > 12) return texto;

        var labelMes = nomesMesesCurtos[mes - 1] || "(Vazio)";
        if (incluirAno && ano) return labelMes + "/" + String(ano).slice(-2);
        return labelMes;
    }

    function montarSerieFaturamentoLoja(notasConsolidadas) {
        var mapa = {};
        (Array.isArray(notasConsolidadas) ? notasConsolidadas : []).forEach(function (nota) {
            var nomeEmpresa = toText(nota && nota.nomeEmpresa) || "(Vazio)";
            if (!mapa[nomeEmpresa]) mapa[nomeEmpresa] = 0;
            mapa[nomeEmpresa] += Number(nota && nota.valor || 0);
        });

        var ranking = Object.keys(mapa).map(function (nome) {
            return {nome: nome, valor: Number(mapa[nome] || 0)};
        }).sort(function (a, b) { return b.valor - a.valor; });

        return {
            categorias: ranking.map(function (item) { return item.nome; }),
            valores: ranking.map(function (item) { return Number(item.valor.toFixed(2)); }),
        };
    }

    function montarSerieFaturamentoMensal(notasConsolidadas) {
        var mapa = {};
        (Array.isArray(notasConsolidadas) ? notasConsolidadas : []).forEach(function (nota) {
            var ano = Number(nota && nota.ano || 0);
            var mes = Number(nota && nota.mes || 0);
            if (!ano || !mes || mes < 1 || mes > 12) return;
            var chave = String(ano) + "-" + String(mes).padStart(2, "0");
            if (!mapa[chave]) mapa[chave] = {ano: ano, mes: mes, valor: 0};
            mapa[chave].valor += Number(nota && nota.valor || 0);
        });

        var chaves = Object.keys(mapa).sort();
        return {
            categorias: chaves.map(function (chave) {
                return labelMesAno(mapa[chave].ano, mapa[chave].mes);
            }),
            valores: chaves.map(function (chave) {
                return Number(mapa[chave].valor.toFixed(2));
            }),
        };
    }

    function montarSerieFaturamentoVendedores(notasConsolidadas) {
        var mapa = {};
        (Array.isArray(notasConsolidadas) ? notasConsolidadas : []).forEach(function (nota) {
            var vendedor = toText(nota && nota.vendedor) || toText(nota && nota.gerente) || "(Vazio)";
            if (!mapa[vendedor]) mapa[vendedor] = 0;
            mapa[vendedor] += Number(nota && nota.valor || 0);
        });

        var ranking = Object.keys(mapa).map(function (nome) {
            return {nome: nome, valor: Number(mapa[nome] || 0)};
        }).sort(function (a, b) { return b.valor - a.valor; });

        return {
            categorias: ranking.map(function (item) { return item.nome; }),
            valores: ranking.map(function (item) { return Number(item.valor.toFixed(2)); }),
        };
    }

    function montarSerieTop10Dias(notasConsolidadas) {
        var mapa = {};
        (Array.isArray(notasConsolidadas) ? notasConsolidadas : []).forEach(function (nota) {
            var dataIso = toText(nota && nota.dataIso) || "(Vazio)";
            if (!mapa[dataIso]) mapa[dataIso] = 0;
            mapa[dataIso] += Number(nota && nota.valor || 0);
        });

        var ranking = Object.keys(mapa).map(function (dataIso) {
            return {dataIso: dataIso, valor: Number(mapa[dataIso] || 0)};
        }).sort(function (a, b) { return b.valor - a.valor; }).slice(0, 10);

        return {
            categorias: ranking.map(function (item) { return formatDataBr(item.dataIso); }),
            valores: ranking.map(function (item) { return Number(item.valor.toFixed(2)); }),
        };
    }

    function montarSerieTop10Produtos(linhasDetalhadas) {
        var linhas = Array.isArray(linhasDetalhadas) ? linhasDetalhadas : [];
        var produtosMap = new Map();

        // Compatibilidade com legado:
        // o Top 10 Produtos soma o valor consolidado da NF (valor_nota_unico)
        // no produto em que esse valor foi gravado.
        linhas.forEach(function (item) {
            var produto = toText(item && item.produto_label) || "(Sem produto)";
            var valorUnico = Number(item && item.valor_nota_unico ? item.valor_nota_unico : 0);
            if (!valorUnico) return;
            produtosMap.set(produto, Number((produtosMap.get(produto) || 0) + valorUnico));
        });

        var ranking = Array.from(produtosMap.keys()).map(function (produto) {
            return {produto: produto, valor: Number(produtosMap.get(produto) || 0)};
        }).sort(function (a, b) { return b.valor - a.valor; }).slice(0, 10);

        return {
            categorias: ranking.map(function (item) { return item.produto; }),
            valores: ranking.map(function (item) { return Number(item.valor.toFixed(2)); }),
        };
    }

    function montarSerieFaturamentoCidade(linhasDetalhadas) {
        var linhas = Array.isArray(linhasDetalhadas) ? linhasDetalhadas : [];
        var cidadeMap = new Map();

        // Segue consolidacao de nota por valor_nota_unico.
        linhas.forEach(function (item) {
            var valorUnico = Number(item && item.valor_nota_unico ? item.valor_nota_unico : 0);
            if (!valorUnico) return;
            var cidade = toText(item && item.cidade_parceiro) || "(Vazio)";
            cidadeMap.set(cidade, Number((cidadeMap.get(cidade) || 0) + valorUnico));
        });

        var ranking = Array.from(cidadeMap.keys()).map(function (cidade) {
            return {cidade: cidade, valor: Number(cidadeMap.get(cidade) || 0)};
        }).sort(function (a, b) { return b.valor - a.valor; });

        return {
            categorias: ranking.map(function (item) { return item.cidade; }),
            valores: ranking.map(function (item) { return Number(item.valor.toFixed(2)); }),
        };
    }

    function montarResumoTipoVenda(linhasDetalhadas) {
        var linhas = Array.isArray(linhasDetalhadas) ? linhasDetalhadas : [];
        var notasMap = new Map();

        linhas.forEach(function (item) {
            var chaveNota = chaveNotaFiscal(item);
            var atual = notasMap.get(chaveNota);
            var valorUnico = Number(item && item.valor_nota_unico ? item.valor_nota_unico : 0);
            var valorNota = Number(item && item.valor_nota ? item.valor_nota : 0);
            var tipoVenda = toText(item && item.tipo_venda);

            if (!atual) {
                notasMap.set(chaveNota, {
                    valorUnico: valorUnico,
                    valorNota: valorNota,
                    tipoVenda: tipoVenda,
                });
                return;
            }

            if (Math.abs(valorUnico) > Math.abs(atual.valorUnico)) {
                atual.valorUnico = valorUnico;
            }
            if (!atual.valorNota && valorNota) {
                atual.valorNota = valorNota;
            }
            if (!atual.tipoVenda && tipoVenda) {
                atual.tipoVenda = tipoVenda;
            }
        });

        var totalEntrega = 0;
        var totalBalcao = 0;

        notasMap.forEach(function (nota) {
            var valor = Number(nota.valorUnico || 0);
            if (!valor) valor = Number(nota.valorNota || 0);
            if (!valor) return;
            var tokenTipo = normalizeText(nota.tipoVenda);
            if (tokenTipo.indexOf("balc") >= 0) {
                totalBalcao += valor;
                return;
            }
            totalEntrega += valor;
        });

        return {
            categorias: ["Entrega", "Venda Balcao"],
            valores: [Number(totalEntrega.toFixed(2)), Number(totalBalcao.toFixed(2))],
        };
    }

    function montarResumoVendedores(linhasDetalhadas) {
        var linhas = Array.isArray(linhasDetalhadas) ? linhasDetalhadas : [];
        var vendedoresComFaturamento = new Map();
        var vendedoresBase = new Map();

        function registrarVendedor(mapa, nome) {
            var vendedor = vendedorTokenResumo(nome);
            if (!vendedor) return;
            var chave = normalizeText(vendedor).replace(/\s+/g, " ").trim();
            if (!chave || mapa.has(chave)) return;
            mapa.set(chave, vendedor);
        }

        universoVendedores.forEach(function (vendedor) {
            registrarVendedor(vendedoresBase, vendedor);
        });
        (Array.isArray(vendedoresResumoBase && vendedoresResumoBase.vendedores)
            ? vendedoresResumoBase.vendedores
            : []
        ).forEach(function (vendedor) {
            registrarVendedor(vendedoresBase, vendedor);
        });

        linhas.forEach(function (item) {
            var valorUnico = Number(item && item.valor_nota_unico ? item.valor_nota_unico : 0);
            if (!valorUnico) return;
            var vendedor = item ? item.apelido_vendedor : "";
            registrarVendedor(vendedoresComFaturamento, vendedor);
            registrarVendedor(vendedoresBase, vendedor);
        });

        var vendedoresComVenda = Array.from(vendedoresComFaturamento.values()).sort(ordenarNomes);
        var vendedoresSemVenda = Array.from(vendedoresBase.keys())
            .filter(function (chave) { return !vendedoresComFaturamento.has(chave); })
            .map(function (chave) { return vendedoresBase.get(chave); })
            .sort(ordenarNomes);

        var totalVendedores = vendedoresComVenda.length + vendedoresSemVenda.length;

        return {
            categorias: ["Vendedor (Sem Venda)", "Vendedor (Faturamento)"],
            valores: [vendedoresSemVenda.length, vendedoresComVenda.length],
            total: totalVendedores,
            comVenda: vendedoresComVenda,
            semVenda: vendedoresSemVenda,
        };
    }

    function renderizarListaVendedores(listaEl, totalEl, nomes, mensagemVazia) {
        var itens = Array.isArray(nomes) ? nomes : [];
        if (totalEl) totalEl.textContent = String(itens.length);
        if (!listaEl) return;

        listaEl.innerHTML = "";
        if (!itens.length) {
            var vazioItem = document.createElement("li");
            vazioItem.className = "is-empty";
            vazioItem.textContent = mensagemVazia;
            listaEl.appendChild(vazioItem);
            return;
        }

        itens.forEach(function (nome) {
            var item = document.createElement("li");
            item.textContent = toText(nome) || "(Vazio)";
            listaEl.appendChild(item);
        });
    }

    function montarSeriePerfilClientes(linhasDetalhadas) {
        var linhas = Array.isArray(linhasDetalhadas) ? linhasDetalhadas : [];
        var perfilMesMap = new Map();
        var perfilTotalMap = new Map();

        linhas.forEach(function (item) {
            var valorUnico = Number(item && item.valor_nota_unico ? item.valor_nota_unico : 0);
            if (!valorUnico) return;

            var anoMes = extrairAnoMesFaturamento(item);
            var mes = Number(anoMes.mes || 0);
            if (!mes || mes < 1 || mes > 12) return;

            var perfil = toText(item && item.descricao_perfil) || "(Sem perfil)";
            var chaveMes = String(mes).padStart(2, "0");

            perfilTotalMap.set(perfil, Number((perfilTotalMap.get(perfil) || 0) + valorUnico));
            perfilMesMap.set(
                perfil + "|" + chaveMes,
                Number((perfilMesMap.get(perfil + "|" + chaveMes) || 0) + valorUnico)
            );
        });

        var mesesFixos = [];
        for (var indiceMes = 1; indiceMes <= 12; indiceMes += 1) {
            mesesFixos.push(String(indiceMes).padStart(2, "0"));
        }

        var perfisTop = Array.from(perfilTotalMap.keys()).map(function (perfil) {
            return {perfil: perfil, valor: Number(perfilTotalMap.get(perfil) || 0)};
        }).sort(function (a, b) { return b.valor - a.valor; }).slice(0, 12);

        var series = perfisTop.map(function (item) {
            var perfil = item.perfil;
            return {
                name: perfil,
                data: mesesFixos.map(function (chaveMes) {
                    var valor = Number(perfilMesMap.get(perfil + "|" + chaveMes) || 0);
                    return Number(valor.toFixed(2));
                }),
            };
        });

        perfisTop.forEach(function (item) {
            var perfil = item.perfil;
            var metaPerfil = mapaMetaPerfil.get(normalizeText(perfil));
            if (metaPerfil === undefined || metaPerfil === null || Number.isNaN(Number(metaPerfil))) return;

            var valorMeta = Number(metaPerfil);
            series.push({
                name: "Meta - " + perfil,
                data: mesesFixos.map(function () { return Number(valorMeta.toFixed(2)); }),
                isMetaSerie: true,
            });
        });

        var paletaCores = [
            "#61b84f", "#df6f2f", "#2d9cdb", "#00a8a8", "#6c757d", "#f59f00",
            "#9c36b5", "#2f9e44", "#0b7285", "#495057", "#364fc7", "#a61e4d",
        ];
        var cores = [];
        var dashArray = [];
        var strokeWidth = [];
        var markerSizes = [];
        var indiceCorBase = 0;
        var corPorPerfil = new Map();

        series.forEach(function (serie) {
            var nomeSerie = toText(serie && serie.name);
            var perfilBase = nomeSerie.indexOf("Meta - ") === 0
                ? nomeSerie.replace(/^Meta - /, "")
                : nomeSerie;
            var chavePerfilBase = normalizeText(perfilBase);
            var corBase = corPorPerfil.get(chavePerfilBase);
            if (!corBase) {
                corBase = paletaCores[indiceCorBase % paletaCores.length];
                corPorPerfil.set(chavePerfilBase, corBase);
                indiceCorBase += 1;
            }

            cores.push(corBase);
            dashArray.push(serie && serie.isMetaSerie ? 6 : 0);
            strokeWidth.push(serie && serie.isMetaSerie ? 2 : 2.4);
            markerSizes.push(serie && serie.isMetaSerie ? 0 : 2.6);
        });

        return {
            categorias: mesesFixos.map(function (chaveMes) {
                var indice = Number(chaveMes || 0);
                return nomesMesesCurtos[indice - 1] || "(Vazio)";
            }),
            series: series,
            cores: cores,
            dashArray: dashArray,
            strokeWidth: strokeWidth,
            markerSizes: markerSizes,
        };
    }

    function obterPerfilClientesVisivel(perfilClientes) {
        var base = perfilClientes || {};
        var seriesBase = Array.isArray(base.series) ? base.series : [];
        var esconderMetas = esconderMetasPerfilClientesEl ? esconderMetasPerfilClientesEl.checked : false;
        if (!esconderMetas) return base;

        var indicesVisiveis = [];
        var series = [];
        seriesBase.forEach(function (serie, index) {
            if (serie && serie.isMetaSerie) return;
            indicesVisiveis.push(index);
            series.push({
                name: toText(serie && serie.name),
                data: Array.isArray(serie && serie.data) ? serie.data : [],
            });
        });

        function pickByIndices(arr) {
            var lista = Array.isArray(arr) ? arr : [];
            return indicesVisiveis.map(function (idx) { return lista[idx]; });
        }

        return {
            categorias: Array.isArray(base.categorias) ? base.categorias : [],
            series: series,
            cores: pickByIndices(base.cores),
            dashArray: pickByIndices(base.dashArray),
            strokeWidth: pickByIndices(base.strokeWidth),
            markerSizes: pickByIndices(base.markerSizes),
        };
    }

    function atualizarGraficoPerfilClientes(perfilClientes) {
        if (!chartPerfilClientes) return;
        var visible = obterPerfilClientesVisivel(perfilClientes || ultimoPerfilClientes || {});
        chartPerfilClientes.updateOptions({
            xaxis: {categories: visible.categorias || []},
            colors: visible.cores || [],
            stroke: {
                curve: "straight",
                width: visible.strokeWidth || [],
                dashArray: visible.dashArray || [],
            },
            markers: {size: visible.markerSizes || [], strokeWidth: 0},
        });
        chartPerfilClientes.updateSeries(visible.series || []);
    }

    function inicializarGraficosFaturamento() {
        if (!window.ApexCharts) return;

        if (chartTipoVendaEl) {
            chartTipoVenda = new window.ApexCharts(chartTipoVendaEl, {
                chart: {type: "donut", height: 260, toolbar: {show: false}},
                series: [0, 0],
                labels: ["Entrega", "Venda Balcao"],
                colors: ["#1f6a8c", "#e8762d"],
                dataLabels: {
                    enabled: true,
                    formatter: function (valor) { return Math.round(valor) + "%"; },
                    style: {fontSize: "14px", fontWeight: 700},
                    dropShadow: {enabled: false},
                },
                legend: {position: "top", horizontalAlign: "right", fontSize: "12px"},
                plotOptions: {
                    pie: {
                        donut: {
                            size: "62%",
                            labels: {show: false},
                        },
                    },
                },
                tooltip: {y: {formatter: function (valor) { return formatMoeda(valor); }}},
            });
            chartTipoVenda.render();
        }

        if (chartVendedoresResumoEl) {
            chartVendedoresResumo = new window.ApexCharts(chartVendedoresResumoEl, {
                chart: {type: "donut", height: 260, toolbar: {show: false}},
                series: [0, 0],
                labels: ["Vendedor (Sem Venda)", "Vendedor (Faturamento)"],
                colors: ["#2d79c7", "#4da833"],
                dataLabels: {
                    enabled: true,
                    formatter: function (_valor, opts) {
                        var numero = Number(opts.w.config.series[opts.seriesIndex] || 0);
                        return String(Math.round(numero));
                    },
                    style: {fontSize: "14px", fontWeight: 700},
                    dropShadow: {enabled: false},
                },
                legend: {position: "top", horizontalAlign: "right", fontSize: "12px"},
                plotOptions: {
                    pie: {
                        donut: {
                            size: "62%",
                            labels: {
                                show: true,
                                name: {show: false},
                                value: {show: false},
                                total: {
                                    show: true,
                                    showAlways: true,
                                    label: "Total Vendedores:",
                                    formatter: function (w) {
                                        return String(
                                            w.globals.seriesTotals.reduce(function (acc, curr) {
                                                return acc + Number(curr || 0);
                                            }, 0)
                                        );
                                    },
                                },
                            },
                        },
                    },
                },
                tooltip: {
                    y: {
                        formatter: function (valor, opts) {
                            var numero = Number(valor || 0);
                            var totais = (
                                opts && opts.w && opts.w.globals && Array.isArray(opts.w.globals.seriesTotals)
                            )
                                ? opts.w.globals.seriesTotals
                                : [];
                            var total = totais.reduce(function (acc, atual) {
                                return acc + Number(atual || 0);
                            }, 0);
                            var percentual = total > 0 ? (numero / total) * 100 : 0;
                            return formatPercentual(percentual, 1);
                        },
                    },
                },
            });
            chartVendedoresResumo.render();
        }

        if (chartLojaEl) {
            chartLoja = new window.ApexCharts(chartLojaEl, {
                chart: {type: "bar", height: 300, toolbar: {show: false}},
                series: [{name: "Faturamento", data: []}],
                colors: ["#176087"],
                plotOptions: {bar: {borderRadius: 6, columnWidth: "52%"}},
                dataLabels: {
                    enabled: true,
                    formatter: function (valor) { return formatMoedaCompacta(valor); },
                    style: {fontSize: "11px"},
                },
                xaxis: {categories: []},
                yaxis: {labels: {formatter: function (valor) { return formatMoeda(valor); }}},
                tooltip: {y: {formatter: function (valor) { return formatMoeda(valor); }}},
            });
            chartLoja.render();
        }

        if (chartMensalEl) {
            chartMensal = new window.ApexCharts(chartMensalEl, {
                chart: {type: "bar", height: 320, toolbar: {show: false}},
                series: [{name: "Faturamento", data: []}],
                colors: ["#0b7285"],
                plotOptions: {bar: {borderRadius: 6, columnWidth: "48%"}},
                dataLabels: {
                    enabled: true,
                    formatter: function (valor) { return formatMoedaCompacta(valor); },
                    style: {fontSize: "11px"},
                },
                xaxis: {categories: []},
                yaxis: {labels: {formatter: function (valor) { return formatMoeda(valor); }}},
                tooltip: {y: {formatter: function (valor) { return formatMoeda(valor); }}},
            });
            chartMensal.render();
        }

        if (chartVendedoresEl) {
            chartVendedores = new window.ApexCharts(chartVendedoresEl, {
                chart: {type: "bar", height: 360, toolbar: {show: false}},
                series: [{name: "Faturamento", data: []}],
                colors: ["#175cd3"],
                plotOptions: {bar: {borderRadius: 4, columnWidth: "62%"}},
                dataLabels: {enabled: false},
                xaxis: {
                    categories: [],
                    labels: {
                        rotate: -60,
                        trim: false,
                        style: {fontSize: "10px"},
                    },
                },
                yaxis: {labels: {formatter: function (valor) { return formatMoedaCompacta(valor); }}},
                tooltip: {y: {formatter: function (valor) { return formatMoeda(valor); }}},
            });
            chartVendedores.render();
        }

        if (chartTop10DiasEl) {
            chartTop10Dias = new window.ApexCharts(chartTop10DiasEl, {
                chart: {type: "bar", height: 340, toolbar: {show: false}},
                series: [{name: "Faturamento", data: []}],
                colors: ["#1f6f8b"],
                plotOptions: {bar: {horizontal: true, borderRadius: 4, barHeight: "55%"}},
                dataLabels: {
                    enabled: true,
                    formatter: function (valor) { return formatMoeda(valor); },
                    style: {fontSize: "11px"},
                    offsetX: 8,
                },
                xaxis: {categories: [], labels: {formatter: function (valor) { return formatMoedaCompacta(valor); }}},
                tooltip: {y: {formatter: function (valor) { return formatMoeda(valor); }}},
            });
            chartTop10Dias.render();
        }

        if (chartTop10ProdutosEl) {
            chartTop10Produtos = new window.ApexCharts(chartTop10ProdutosEl, {
                chart: {type: "bar", height: 380, toolbar: {show: false}},
                series: [{name: "Faturamento", data: []}],
                colors: ["#125d83"],
                plotOptions: {bar: {horizontal: true, borderRadius: 4, barHeight: "56%"}},
                dataLabels: {
                    enabled: true,
                    formatter: function (valor) { return formatMoeda(valor); },
                    style: {fontSize: "10px"},
                    offsetX: 8,
                },
                xaxis: {categories: [], labels: {formatter: function (valor) { return formatMoedaCompacta(valor); }}},
                yaxis: {
                    labels: {
                        style: {fontSize: "10px"},
                    },
                },
                tooltip: {y: {formatter: function (valor) { return formatMoeda(valor); }}},
            });
            chartTop10Produtos.render();
        }

        if (chartCidadeEl) {
            chartCidade = new window.ApexCharts(chartCidadeEl, {
                chart: {type: "area", height: 360, toolbar: {show: false}},
                series: [{name: "Faturamento", data: []}],
                colors: ["#125d83"],
                stroke: {curve: "smooth", width: 2},
                fill: {
                    type: "gradient",
                    gradient: {
                        shadeIntensity: 1,
                        opacityFrom: 0.45,
                        opacityTo: 0.05,
                        stops: [0, 95, 100],
                    },
                },
                dataLabels: {enabled: false},
                xaxis: {
                    categories: [],
                    labels: {
                        rotate: -90,
                        trim: false,
                        style: {fontSize: "10px"},
                    },
                },
                yaxis: {labels: {formatter: function (valor) { return formatMoeda(valor); }}},
                tooltip: {y: {formatter: function (valor) { return formatMoeda(valor); }}},
            });
            chartCidade.render();
        }

        if (chartPerfilClientesEl) {
            chartPerfilClientes = new window.ApexCharts(chartPerfilClientesEl, {
                chart: {type: "line", height: 360, toolbar: {show: false}},
                series: [],
                colors: [
                    "#61b84f", "#df6f2f", "#2d9cdb", "#00a8a8", "#6c757d", "#f59f00",
                    "#9c36b5", "#2f9e44", "#0b7285", "#495057", "#364fc7", "#a61e4d",
                ],
                stroke: {curve: "straight", width: 2},
                markers: {size: 2.6, strokeWidth: 0},
                dataLabels: {enabled: false},
                legend: {show: false},
                xaxis: {
                    categories: [],
                    labels: {
                        rotate: 0,
                        style: {fontSize: "12px"},
                    },
                },
                yaxis: {
                    labels: {
                        formatter: function (valor) { return formatMoeda(valor); },
                    },
                },
                grid: {
                    borderColor: "#d9e2ea",
                    strokeDashArray: 0,
                },
                tooltip: {
                    shared: true,
                    intersect: false,
                    y: {formatter: function (valor) { return formatMoeda(valor); }},
                },
                noData: {text: "Sem dados"},
            });
            chartPerfilClientes.render();
        }
    }

    function atualizarGraficosFaturamento(notasConsolidadas, linhasDetalhadas) {
        var resumoTipoVenda = montarResumoTipoVenda(linhasDetalhadas);
        var resumoVendedores = montarResumoVendedores(linhasDetalhadas);
        var loja = montarSerieFaturamentoLoja(notasConsolidadas);
        var mensal = montarSerieFaturamentoMensal(notasConsolidadas);
        var vendedores = montarSerieFaturamentoVendedores(notasConsolidadas);
        var top10Dias = montarSerieTop10Dias(notasConsolidadas);
        var top10Produtos = montarSerieTop10Produtos(linhasDetalhadas);
        var cidade = montarSerieFaturamentoCidade(linhasDetalhadas);
        var perfilClientes = montarSeriePerfilClientes(linhasDetalhadas);

        if (chartTipoVenda) {
            chartTipoVenda.updateOptions({labels: resumoTipoVenda.categorias});
            chartTipoVenda.updateSeries(resumoTipoVenda.valores);
        }
        if (chartVendedoresResumo) {
            chartVendedoresResumo.updateOptions({
                labels: resumoVendedores.categorias,
                plotOptions: {
                    pie: {
                        donut: {
                            labels: {
                                total: {
                                    show: true,
                                    showAlways: true,
                                    label: "Total Vendedores:",
                                    formatter: function () { return String(resumoVendedores.total); },
                                },
                            },
                        },
                    },
                },
            });
            chartVendedoresResumo.updateSeries(resumoVendedores.valores);
        }
        renderizarListaVendedores(
            vendedoresComVendaListaEl,
            vendedoresComVendaTotalEl,
            resumoVendedores.comVenda,
            "Nenhum vendedor com venda no periodo."
        );
        renderizarListaVendedores(
            vendedoresSemVendaListaEl,
            vendedoresSemVendaTotalEl,
            resumoVendedores.semVenda,
            "Nenhum vendedor sem venda no periodo."
        );
        if (chartLoja) {
            chartLoja.updateOptions({xaxis: {categories: loja.categorias}});
            chartLoja.updateSeries([{name: "Faturamento", data: loja.valores}]);
        }
        if (chartMensal) {
            chartMensal.updateOptions({xaxis: {categories: mensal.categorias}});
            chartMensal.updateSeries([{name: "Faturamento", data: mensal.valores}]);
        }
        if (chartVendedores) {
            chartVendedores.updateOptions({xaxis: {categories: vendedores.categorias}});
            chartVendedores.updateSeries([{name: "Faturamento", data: vendedores.valores}]);
        }
        if (chartTop10Dias) {
            chartTop10Dias.updateOptions({xaxis: {categories: top10Dias.categorias}});
            chartTop10Dias.updateSeries([{name: "Faturamento", data: top10Dias.valores}]);
        }
        if (chartTop10Produtos) {
            chartTop10Produtos.updateOptions({xaxis: {categories: top10Produtos.categorias}});
            chartTop10Produtos.updateSeries([{name: "Faturamento", data: top10Produtos.valores}]);
        }
        if (chartCidade) {
            chartCidade.updateOptions({xaxis: {categories: cidade.categorias}});
            chartCidade.updateSeries([{name: "Faturamento", data: cidade.valores}]);
        }
        ultimoPerfilClientes = perfilClientes;
        atualizarGraficoPerfilClientes(perfilClientes);
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
            notasConsolidadas: consolidadoNotasFiltradas.notas,
            linhasDetalhadas: itens,
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
        if (perfilClientesTotalEl) {
            perfilClientesTotalEl.textContent = formatadorMoeda.format(metricas.valorFaturamento);
        }
        atualizarReloginho(metricas.metaGeral, metricas.valorFaturamento);
        atualizarGraficosFaturamento(metricas.notasConsolidadas, metricas.linhasDetalhadas);
        atualizarPayloadDashboardPdf(metricas);
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

    inicializarGraficosFaturamento();

    if (!tabelaTarget || !window.Tabulator || !window.TabulatorDefaults) {
        atualizarDashboard(data);
        if (incluirPedidosPendentesEl) {
            incluirPedidosPendentesEl.addEventListener("change", function () {
                atualizarDashboard(data);
            });
        }
        if (esconderMetasPerfilClientesEl) {
            esconderMetasPerfilClientesEl.addEventListener("change", function () {
                atualizarGraficoPerfilClientes();
            });
        }
        inicializarExportacaoDashboardPdf();
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
    tabelaRef = tabela;

    var filtrosConfig = configurarFiltrosExternos(tabela, data, secFiltros);
    if (filtrosConfig) {
        registrarAcaoLimparFiltros(tabela, filtrosConfig.secFiltros, filtrosConfig.filtrosExternos);
        filtrosExternosRef = filtrosConfig.filtrosExternos;
    }
    inicializarExportacaoDashboardPdf();

    function atualizarDashboardComTabela() {
        var linhasAtivas = tabela.getData("active");
        if (!Array.isArray(linhasAtivas)) linhasAtivas = tabela.getData() || [];
        atualizarDashboard(linhasAtivas);
    }

    if (incluirPedidosPendentesEl) {
        incluirPedidosPendentesEl.addEventListener("change", atualizarDashboardComTabela);
    }
    if (esconderMetasPerfilClientesEl) {
        esconderMetasPerfilClientesEl.addEventListener("change", function () {
            atualizarGraficoPerfilClientes();
        });
    }

    tabela.on("tableBuilt", atualizarDashboardComTabela);
    tabela.on("dataLoaded", atualizarDashboardComTabela);
    tabela.on("dataFiltered", atualizarDashboardComTabela);
    tabela.on("renderComplete", atualizarDashboardComTabela);
    setTimeout(atualizarDashboardComTabela, 0);
})();
