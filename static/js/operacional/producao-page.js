(function () {
    var entrada = document.getElementById("data-entrada-atividade-criar");
    var aceite = document.getElementById("data-aceite-atividade-criar");
    var inicio = document.getElementById("data-inicio-atividade-criar");
    var fim = document.getElementById("data-fim-atividade-criar");
    if (!entrada || !aceite || !inicio || !fim) return;

    function atualizarEncadeamentoDatas() {
        var valorEntrada = entrada.value || "";
        aceite.disabled = !valorEntrada;
        aceite.min = valorEntrada || "";
        if (!valorEntrada) {
            aceite.value = "";
            inicio.value = "";
            fim.value = "";
        }
        if (valorEntrada && aceite.value && aceite.value < valorEntrada) {
            aceite.value = "";
            inicio.value = "";
            fim.value = "";
        }

        var valorAceite = aceite.value || "";
        inicio.disabled = !valorAceite;
        inicio.min = valorAceite || "";
        if (!valorAceite) {
            inicio.value = "";
            fim.value = "";
        }
        if (valorAceite && inicio.value && inicio.value < valorAceite) {
            inicio.value = "";
            fim.value = "";
        }

        var valorInicio = inicio.value || "";
        fim.disabled = !valorInicio;
        fim.min = valorInicio || "";
        if (!valorInicio) {
            fim.value = "";
        }
        if (valorInicio && fim.value && fim.value < valorInicio) {
            fim.value = "";
        }
    }

    [entrada, aceite, inicio, fim].forEach(function (input) {
        input.addEventListener("change", atualizarEncadeamentoDatas);
        input.addEventListener("input", atualizarEncadeamentoDatas);
    });
    atualizarEncadeamentoDatas();
})();

(function () {
    var form = document.getElementById("upload-producao-form");
    if (!form) return;

    var dropzone = document.getElementById("dropzone-producao");
    var input = document.getElementById("arquivos-producao-input");
    var fileStatus = document.getElementById("nome-arquivos-producao-selecionado");
    var loadingStatus = document.getElementById("producao-loading-status");

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
    var dataElement = document.getElementById("producao-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var dadosOriginais = Array.isArray(data) ? data.slice() : [];

    var CHAVES_RELOGINHO = {
        x30x1: "30x1",
        x15x2: "15x2",
        x6x5: "6x5",
        total: "total",
    };
    var NOME_MES = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    };

    function formatNumero(valor) {
        var numero = Number(valor || 0);
        return numero.toLocaleString("pt-BR", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
    }

    function paraTexto(valor) {
        return String(valor || "").toLowerCase().trim();
    }

    function parseNumeroLote(valor) {
        var texto = String(valor || "").trim();
        if (!texto) return 0;
        texto = texto.replace(/\s/g, "");
        if (texto.indexOf(",") >= 0) {
            texto = texto.replace(/\./g, "").replace(/,/g, ".");
        }
        var num = Number(texto);
        return Number.isFinite(num) ? num : 0;
    }

    function parseDataIso(valor) {
        var texto = String(valor || "").trim();
        if (!texto) return null;
        var partes = texto.split("-");
        if (partes.length !== 3) return null;
        var ano = Number(partes[0]);
        var mes = Number(partes[1]);
        var dia = Number(partes[2]);
        if (!(ano > 0 && mes >= 1 && mes <= 12 && dia >= 1 && dia <= 31)) return null;
        var dt = new Date(ano, mes - 1, dia);
        if (isNaN(dt.getTime())) return null;
        dt.setHours(0, 0, 0, 0);
        return dt;
    }

    function extrairDataEntrada(item) {
        if (item.data_hora_entrada_atividade_iso) {
            return parseDataIso(item.data_hora_entrada_atividade_iso);
        }
        var texto = String(item.data_hora_entrada_atividade || "").trim();
        if (!texto) return null;
        var partes = texto.split(" ");
        var dataBr = partes[0] || "";
        var dmy = dataBr.split("/");
        if (dmy.length !== 3) return null;
        var dia = Number(dmy[0]);
        var mes = Number(dmy[1]);
        var ano = Number(dmy[2]);
        if (!(ano > 0 && mes >= 1 && mes <= 12 && dia >= 1 && dia <= 31)) return null;
        var dt = new Date(ano, mes - 1, dia);
        if (isNaN(dt.getTime())) return null;
        dt.setHours(0, 0, 0, 0);
        return dt;
    }

    function extrairAnoEntrada(item) {
        var dt = extrairDataEntrada(item);
        return dt ? dt.getFullYear() : "";
    }

    function extrairMesEntrada(item) {
        var dt = extrairDataEntrada(item);
        return dt ? (dt.getMonth() + 1) : "";
    }

    function formatarMes(valor) {
        var mes = Number(valor || 0);
        if (!mes) return "(Vazio)";
        return NOME_MES[mes] || String(mes);
    }

    function ensureFilterColumns(section) {
        if (!section) return null;

        var left = section.querySelector('[data-module-filter-column="left"]')
            || section.querySelector("#producao-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#producao-filtros-coluna-direita");

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
            left.id = "producao-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "producao-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    var colunas = [
        { title: "Origem", field: "data_origem" },
        { title: "Número da OP", field: "numero_operacao", hozAlign: "right" },
        { title: "Situação", field: "situacao" },
        { title: "Código do Produto", field: "produto_codigo" },
        { title: "Descrição do Produto", field: "produto_descricao" },
        { title: "Tamanho do Lote", field: "tamanho_lote" },
        { title: "Número do Lote", field: "numero_lote" },
        { title: "Data e Hora de Entrada da Atividade", field: "data_hora_entrada_atividade" },
        { title: "Data e Hora de Aceite da Atividade", field: "data_hora_aceite_atividade" },
        { title: "Data e Hora de Início da Atividade", field: "data_hora_inicio_atividade" },
        { title: "Data e Hora de Fim da Atividade", field: "data_hora_fim_atividade" },
        { title: "KG", field: "kg", hozAlign: "right" },
        { title: "Produção por Dia (FD)", field: "producao_por_dia", hozAlign: "right" },
        { title: "KG por Lote", field: "kg_por_lote", hozAlign: "right" }
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, dadosOriginais);

    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros) {
        secFiltros.dataset.moduleFiltersAuto = "off";
    }

    var tabela = window.TabulatorDefaults.create("#producao-tabulator", {
        data: dadosOriginais,
        columns: colunas,
    });
    var filtrosExternos = null;

    if (window.ModuleFilterCore && secFiltros) {
        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholderFiltros = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholderFiltros) placeholderFiltros.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (filtroColumns && filtroColumns.left && filtroColumns.right) {
            filtrosExternos = window.ModuleFilterCore.create({
                data: dadosOriginais,
                definitions: [
                    {
                        key: "situacao",
                        label: "Situação",
                        extractValue: function (rowData) {
                            return rowData ? rowData.situacao : "";
                        },
                        formatValue: function (valor) {
                            return String(valor || "").trim() || "(Vazio)";
                        },
                    },
                    {
                        key: "ano_entrada_atividade",
                        label: "Ano",
                        singleSelect: true,
                        extractValue: function (rowData) {
                            return extrairAnoEntrada(rowData);
                        },
                        formatValue: function (valor) {
                            return String(valor || "").trim() || "(Vazio)";
                        },
                        sortOptions: function (a, b) {
                            return Number(b.value || 0) - Number(a.value || 0);
                        },
                    },
                    {
                        key: "mes_entrada_atividade",
                        label: "Mês",
                        singleSelect: true,
                        extractValue: function (rowData) {
                            return extrairMesEntrada(rowData);
                        },
                        formatValue: function (valor) {
                            return formatarMes(valor);
                        },
                        sortOptions: function (a, b) {
                            return Number(a.value || 0) - Number(b.value || 0);
                        },
                    },
                ],
                leftColumn: filtroColumns.left,
                rightColumn: filtroColumns.right,
                onChange: function () {
                    if (typeof tabela.refreshFilter === "function") {
                        tabela.refreshFilter();
                    }
                },
            });

            tabela.addFilter(function (rowData) {
                return filtrosExternos.matchesRecord(rowData);
            });
        }
    }

    function limparTodosFiltros() {
        if (filtrosExternos && typeof filtrosExternos.clearAllFilters === "function") {
            filtrosExternos.clearAllFilters();
        }
        if (typeof tabela.clearHeaderFilter === "function") {
            tabela.clearHeaderFilter();
        }
        if (typeof tabela.refreshFilter === "function") {
            tabela.refreshFilter();
        }
    }

    var limparFiltrosSidebarBtn = secFiltros ? secFiltros.querySelector(".module-filters-clear-all") : null;
    var limparFiltrosToolbarBtn = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
    if (limparFiltrosSidebarBtn) {
        limparFiltrosSidebarBtn.addEventListener("click", limparTodosFiltros);
    }
    if (limparFiltrosToolbarBtn) {
        limparFiltrosToolbarBtn.addEventListener("click", limparTodosFiltros);
    }

    function possuiFiltroExternoAtivo() {
        if (!filtrosExternos || !Array.isArray(filtrosExternos.definitions)) return false;
        if (typeof filtrosExternos.getSelectedCount !== "function") return false;
        return filtrosExternos.definitions.some(function (definition) {
            return filtrosExternos.getSelectedCount(definition.key) > 0;
        });
    }

    function possuiFiltroCabecalhoAtivo() {
        if (!tabela || typeof tabela.getHeaderFilters !== "function") return false;
        var headerFilters = tabela.getHeaderFilters();
        if (!Array.isArray(headerFilters) || !headerFilters.length) return false;
        return headerFilters.some(function (item) {
            if (!item) return false;
            var value = item.value;
            if (value === null || value === undefined) return false;
            if (typeof value === "string") return value.trim() !== "";
            return true;
        });
    }

    function semFiltrosSelecionados() {
        return !possuiFiltroExternoAtivo() && !possuiFiltroCabecalhoAtivo();
    }

    function obterCategoriaProduto(desc) {
        var texto = paraTexto(desc).replace(/\s+/g, "");
        if (texto.indexOf("30x1") >= 0) return "x30x1";
        if (texto.indexOf("15x2") >= 0) return "x15x2";
        if (texto.indexOf("6x5") >= 0) return "x6x5";
        return "outras";
    }

    function deveExcluirDoTotal(desc) {
        return paraTexto(desc).indexOf("varredura") >= 0;
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

    function atualizarCard(chave, valores, semFiltrosAtivos) {
        var sufixo = CHAVES_RELOGINHO[chave];
        if (!sufixo) return;

        var metaMes = Number(valores.meta_mes || 0);
        var metaAcum = Number(valores.meta_acumulada || 0);
        var metaAndamento = Number(valores.meta_andamento || 0);
        var real = Number(valores.realizado || 0);
        var pct = metaAcum > 0 ? (real / metaAcum) * 100 : 0;

        var metaAcumEl = document.getElementById("meta-acum-" + sufixo);
        var realEl = document.getElementById("real-" + sufixo);
        var pctEl = document.getElementById("pct-" + sufixo);

        if (metaAcumEl) metaAcumEl.textContent = formatNumero(metaAcum);
        if (realEl) realEl.textContent = formatNumero(real);
        if (pctEl) pctEl.textContent = pct.toFixed(2).replace(".", ",") + "%";

        var referenciaEscala = metaAcum > 0 ? metaAcum : Math.max(real, 1);
        var referenciaEscalaMetaMes = metaMes > 0 ? metaMes : referenciaEscala;
        var realPonteiro = real;
        if (semFiltrosAtivos) {
            realPonteiro = referenciaEscalaMetaMes * (pct / 100);
        }
        setRotacaoPonteiro("ponteiro-meta-" + sufixo, valorParaAngulo(metaAndamento, referenciaEscalaMetaMes));
        if (chave === "total") {
            setRotacaoPonteiro("ponteiro-meta80-total", valorParaAngulo(metaAndamento * 0.8, referenciaEscalaMetaMes));
        }
        setRotacaoPonteiro("ponteiro-real-" + sufixo, valorParaAngulo(realPonteiro, referenciaEscalaMetaMes));
    }

    function calcularDashboard(dados) {
        var buckets = {
            x30x1: {realizado: 0, producao_dia_referencia: 0},
            x15x2: {realizado: 0, producao_dia_referencia: 0},
            x6x5: {realizado: 0, producao_dia_referencia: 0},
        };
        var realizadoTotalTodosProdutos = 0;
        var dataReferencia = null;
        var dataMinima = null;
        var dataMaxima = null;

        dados.forEach(function (item) {
            var dt = extrairDataEntrada(item);
            if (dt && (!dataReferencia || dt > dataReferencia)) {
                dataReferencia = dt;
            }
            if (dt && (!dataMinima || dt < dataMinima)) {
                dataMinima = dt;
            }
            if (dt && (!dataMaxima || dt > dataMaxima)) {
                dataMaxima = dt;
            }

            var categoria = obterCategoriaProduto(item.produto_descricao);
            var tamLote = parseNumeroLote(item.tamanho_lote);
            var multiplo = Number(item.pacote_por_fardo_parametro || 0);
            if (multiplo <= 0) multiplo = Number(item.kg || 0);
            var realizado = (multiplo > 0) ? (tamLote / multiplo) : 0;
            if (!deveExcluirDoTotal(item.produto_descricao)) {
                realizadoTotalTodosProdutos += realizado;
            }

            if (!buckets[categoria]) return;
            buckets[categoria].realizado += realizado;

            var prodDia = Number(item.producao_por_dia || 0);
            if (prodDia > 0 && prodDia > buckets[categoria].producao_dia_referencia) {
                buckets[categoria].producao_dia_referencia = prodDia;
            }
        });

        if (!dataReferencia) {
            dataReferencia = new Date();
            dataReferencia.setHours(0, 0, 0, 0);
        }
        if (!dataMinima) dataMinima = dataReferencia;
        if (!dataMaxima) dataMaxima = dataReferencia;

        var inicioMes = new Date(dataReferencia.getFullYear(), dataReferencia.getMonth(), 1);
        var fimMes = new Date(dataReferencia.getFullYear(), dataReferencia.getMonth() + 1, 0);
        var diasUteisMes = contarDiasUteisEntre(inicioMes, fimMes);
        var diasUteisAndamentoMes = contarDiasUteisEntre(inicioMes, dataReferencia);
        var diasUteisPeriodo = contarDiasUteisEntre(dataMinima, dataMaxima);

        var resultado = {
            x30x1: {meta_mes: 0, meta_acumulada: 0, meta_andamento: 0, realizado: 0},
            x15x2: {meta_mes: 0, meta_acumulada: 0, meta_andamento: 0, realizado: 0},
            x6x5: {meta_mes: 0, meta_acumulada: 0, meta_andamento: 0, realizado: 0},
            total: {meta_mes: 0, meta_acumulada: 0, meta_andamento: 0, realizado: 0},
        };

        ["x30x1", "x15x2", "x6x5"].forEach(function (chave) {
            var bucket = buckets[chave];
            var producaoDiaBase = Number(bucket.producao_dia_referencia || 0);
            resultado[chave].meta_mes = producaoDiaBase * diasUteisMes;
            resultado[chave].meta_acumulada = producaoDiaBase * diasUteisPeriodo;
            resultado[chave].meta_andamento = producaoDiaBase * diasUteisAndamentoMes;
            resultado[chave].realizado = bucket.realizado;

            resultado.total.meta_mes += resultado[chave].meta_mes;
            resultado.total.meta_acumulada += resultado[chave].meta_acumulada;
            resultado.total.meta_andamento += resultado[chave].meta_andamento;
        });
        resultado.total.realizado = realizadoTotalTodosProdutos;

        return resultado;
    }

    function atualizarDashboard(dados) {
        var metricas = calcularDashboard(dados);
        var semFiltrosAtivos = semFiltrosSelecionados();
        if (semFiltrosAtivos) {
            ["x30x1", "x15x2", "x6x5", "total"].forEach(function (chave) {
                metricas[chave].meta_andamento = metricas[chave].meta_mes;
            });
        }
        atualizarCard("x30x1", metricas.x30x1, semFiltrosAtivos);
        atualizarCard("x15x2", metricas.x15x2, semFiltrosAtivos);
        atualizarCard("x6x5", metricas.x6x5, semFiltrosAtivos);
        atualizarCard("total", metricas.total, semFiltrosAtivos);
    }

    tabela.on("dataFiltered", function (_filters, rows) {
        var dadosFiltrados = rows.map(function (row) { return row.getData(); });
        atualizarDashboard(dadosFiltrados);
    });

    tabela.setLocale("pt-br");
    atualizarDashboard(dadosOriginais);
})();
