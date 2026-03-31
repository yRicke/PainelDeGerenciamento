(function () {
    var dataElement = document.getElementById("comite-diario-tabulator-data");
    var empresasElement = document.getElementById("comite-diario-empresas-opcoes-data");
    var parceirosElement = document.getElementById("comite-diario-parceiros-opcoes-data");
    var naturezasElement = document.getElementById("comite-diario-naturezas-opcoes-data");
    var centrosElement = document.getElementById("comite-diario-centros-opcoes-data");
    var bancosElement = document.getElementById("comite-diario-bancos-opcoes-data");
    var receitaDespesaElement = document.getElementById("comite-diario-receita-despesa-opcoes-data");
    var tipoMovimentoElement = document.getElementById("comite-diario-tipo-movimento-opcoes-data");
    var decisaoElement = document.getElementById("comite-diario-decisao-opcoes-data");
    var ultimaDataElement = document.getElementById("comite-diario-ultima-data-iso");
    var lancamentosPayloadElement = document.getElementById("comite-diario-lancamentos-bancarios-data");
    var lancamentosWrapper = document.getElementById("comite-lancamentos-bancarios-wrapper");
    var comiteResumoWrapper = document.getElementById("comite-resumo-wrapper");
    var comiteDecisaoChartEl = document.getElementById("comite-decisao-chart");
    var cadastroForm = document.getElementById("comite-diario-cadastro-form");
    var saveStatusEl = document.getElementById("comite-diario-save-status");
    var cadastroDecisaoSelect = cadastroForm ? cadastroForm.querySelector('select[name="decisao"]') : null;
    var cadastroDataProrrogadaInput = cadastroForm ? cadastroForm.querySelector('input[name="data_prorrogada"]') : null;
    var cadastroTransferFields = cadastroForm
        ? [
            cadastroForm.querySelector('select[name="de_banco_id"]'),
            cadastroForm.querySelector('select[name="para_banco_id"]'),
            cadastroForm.querySelector('select[name="para_empresa_id"]'),
        ]
        : [];

    if (
        !dataElement ||
        !empresasElement ||
        !parceirosElement ||
        !naturezasElement ||
        !centrosElement ||
        !bancosElement ||
        !receitaDespesaElement ||
        !tipoMovimentoElement ||
        !decisaoElement ||
        !lancamentosPayloadElement ||
        !lancamentosWrapper ||
        !cadastroForm ||
        !window.Tabulator ||
        !window.TabulatorDefaults
    ) {
        return;
    }

    var tabela = null;
    var seqByRowId = {};
    var internalUpdate = false;
    var externalFilters = null;
    var selectedDateIso = "";

    var data = JSON.parse(dataElement.textContent || "[]");
    var empresasOpcoes = JSON.parse(empresasElement.textContent || "[]");
    var parceirosOpcoes = JSON.parse(parceirosElement.textContent || "[]");
    var naturezasOpcoes = JSON.parse(naturezasElement.textContent || "[]");
    var centrosOpcoes = JSON.parse(centrosElement.textContent || "[]");
    var bancosOpcoes = JSON.parse(bancosElement.textContent || "[]");
    var receitaDespesaOpcoes = JSON.parse(receitaDespesaElement.textContent || "[]");
    var tipoMovimentoOpcoes = JSON.parse(tipoMovimentoElement.textContent || "[]");
    var decisaoOpcoes = JSON.parse(decisaoElement.textContent || "[]");
    var lancamentosPayload = JSON.parse(lancamentosPayloadElement.textContent || "{}");
    var ultimaDataIso = "";
    try {
        ultimaDataIso = JSON.parse(ultimaDataElement ? (ultimaDataElement.textContent || "\"\"") : "\"\"");
    } catch (_error) {
        ultimaDataIso = "";
    }

    var filtroDataInput = document.getElementById("comite-diario-data-filtro");
    var btnUltimaData = document.getElementById("comite-diario-btn-ultima-data");
    var btnLimparData = document.getElementById("comite-diario-btn-limpar-data");
    var secFiltros = document.getElementById("sec-filtros");
    var filtrosColunaEsquerda = document.getElementById("comite-filtros-coluna-esquerda");
    var filtrosColunaDireita = document.getElementById("comite-filtros-coluna-direita");

    var lancamentosEndpointUrl = toText(lancamentosWrapper.getAttribute("data-endpoint-url"));
    var lancamentosUsarLimite = false;
    var lancamentosRefreshInFlight = false;
    var lancamentosPollingTimer = null;
    var comiteDecisaoChart = null;

    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});

    var empresasValues = {};
    var parceirosValues = {};
    var naturezasValues = {};
    var centrosValues = {};
    var bancosValues = {};
    var receitaDespesaValues = {};
    var tipoMovimentoValues = {};
    var decisaoValues = {};

    empresasOpcoes.forEach(function (item) {
        var id = String(item.id || "").trim();
        if (!id) return;
        empresasValues[id] = String(item.label || "").trim();
    });

    parceirosOpcoes.forEach(function (item) {
        var id = String(item.id || "").trim();
        if (!id) return;
        parceirosValues[id] = String(item.label || "").trim();
    });

    naturezasOpcoes.forEach(function (item) {
        var id = String(item.id || "").trim();
        if (!id) return;
        naturezasValues[id] = String(item.label || "").trim();
    });

    centrosOpcoes.forEach(function (item) {
        var id = String(item.id || "").trim();
        if (!id) return;
        centrosValues[id] = String(item.label || "").trim();
    });

    bancosOpcoes.forEach(function (item) {
        var id = String(item.id || "").trim();
        if (!id) return;
        bancosValues[id] = String(item.label || "").trim();
    });

    receitaDespesaOpcoes.forEach(function (item) {
        var value = String(item.value || "").trim();
        if (!value) return;
        receitaDespesaValues[value] = String(item.label || "").trim() || value;
    });

    tipoMovimentoOpcoes.forEach(function (item) {
        var value = String(item.value || "").trim();
        if (!value) return;
        tipoMovimentoValues[value] = String(item.label || "").trim() || value;
    });

    decisaoOpcoes.forEach(function (item) {
        var value = String(item.value || "").trim();
        if (!value) return;
        decisaoValues[value] = String(item.label || "").trim() || value;
    });

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function toNumber(value) {
        if (typeof value === "number") {
            return Number.isFinite(value) ? value : 0;
        }
        var text = toText(value);
        if (!text) return 0;
        text = text.replace(/\s+/g, "").replace("R$", "");
        if (text.indexOf(",") >= 0) {
            text = text.replace(/\./g, "").replace(",", ".");
        }
        var parsed = Number(text);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function formatMoney(value) {
        return formatadorMoeda.format(toNumber(value));
    }

    function formatDateIsoToBr(dateIso) {
        var text = toText(dateIso);
        if (!text) return "";
        var parts = text.split("-");
        if (parts.length !== 3) return text;
        return parts[2] + "/" + parts[1] + "/" + parts[0];
    }

    function getCookie(name) {
        var cookieValue = null;
        if (!document.cookie) return cookieValue;
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i += 1) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
        return cookieValue;
    }

    function getCsrfToken() {
        var input = document.querySelector("input[name='csrfmiddlewaretoken']");
        return (input ? input.value : "") || getCookie("csrftoken") || "";
    }

    function appendCsrfToken(formData) {
        var token = getCsrfToken();
        if (token) formData.append("csrfmiddlewaretoken", token);
    }

    function parseJsonResponse(response) {
        return response
            .json()
            .catch(function () {
                return {};
            })
            .then(function (body) {
                return {ok: response.ok, body: body};
            });
    }

    function setSaveStatus(text, tone) {
        if (!saveStatusEl) return;
        saveStatusEl.classList.remove(
            "comite-diario-save-status--ok",
            "comite-diario-save-status--error",
            "comite-diario-save-status--progress"
        );
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function getLinhaLancamentos(payload, chave) {
        var linhas = payload && payload.linhas ? payload.linhas : {};
        return linhas[chave] || {};
    }

    function getBancoValor(linha, bancoId) {
        if (!linha) return 0;
        return toNumber(linha[String(bancoId)] || 0);
    }

    function renderLancamentosBancarios(payload) {
        if (!lancamentosWrapper) return;
        var dados = payload && typeof payload === "object" ? payload : {};
        var bancos = Array.isArray(dados.bancos) ? dados.bancos : [];

        var linhaSaldo = getLinhaLancamentos(dados, "saldo_atual");
        var linhaLimite = getLinhaLancamentos(dados, "limite");
        var linhaAntecipacoes = getLinhaLancamentos(dados, "antecipacoes");
        var linhaTransferencias = getLinhaLancamentos(dados, "transferencias");

        var html = [];
        html.push('<table class="comite-lancamentos-table">');
        html.push("<thead><tr><th>Linha</th>");
        bancos.forEach(function (banco) {
            html.push("<th>" + toText(banco.nome) + "</th>");
        });
        html.push("<th>Todos</th></tr></thead>");
        html.push("<tbody>");

        function renderLinha(chave, label, linhaValores, includeToggle) {
            var total = 0;
            html.push("<tr>");
            if (includeToggle) {
                var checkedAttr = lancamentosUsarLimite ? " checked" : "";
                html.push(
                    '<td><span class="comite-lancamentos-row-label">' +
                    label +
                    '<label class="comite-lancamentos-row-toggle">' +
                    '<input type="checkbox" id="comite-lancamentos-usar-limite"' + checkedAttr + ">" +
                    "<span>Usar limite</span>" +
                    "</label></span></td>"
                );
            } else {
                html.push("<td>" + label + "</td>");
            }

            bancos.forEach(function (banco) {
                var valor = getBancoValor(linhaValores, banco.id);
                total += valor;
                html.push("<td>" + formatMoney(valor) + "</td>");
            });
            html.push("<td>" + formatMoney(total) + "</td>");
            html.push("</tr>");
        }

        renderLinha("saldo_atual", "Saldo atual", linhaSaldo, false);
        renderLinha("limite", "Limite", linhaLimite, true);
        renderLinha("antecipacoes", "Antecipacoes", linhaAntecipacoes, false);
        renderLinha("transferencias", "Transferencias", linhaTransferencias, false);

        var totalSaldoDisponivel = 0;
        html.push("<tr>");
        html.push("<td>Saldo disponivel</td>");
        bancos.forEach(function (banco) {
            var saldo = getBancoValor(linhaSaldo, banco.id);
            var limite = lancamentosUsarLimite ? getBancoValor(linhaLimite, banco.id) : 0;
            var antecipacao = getBancoValor(linhaAntecipacoes, banco.id);
            var transferencia = getBancoValor(linhaTransferencias, banco.id);
            var saldoDisponivel = saldo + limite + antecipacao - transferencia;
            totalSaldoDisponivel += saldoDisponivel;
            html.push("<td>" + formatMoney(saldoDisponivel) + "</td>");
        });
        html.push("<td>" + formatMoney(totalSaldoDisponivel) + "</td>");
        html.push("</tr>");

        html.push("</tbody></table>");

        var meta = dados.meta || {};
        var legenda = [];
        if (toText(meta.data_saldos)) legenda.push("Saldos/Limites: " + formatDateIsoToBr(meta.data_saldos));
        if (toText(meta.data_transferencias)) legenda.push("Transferencias: " + formatDateIsoToBr(meta.data_transferencias));
        if (legenda.length) {
            html.push('<div class="comite-lancamentos-meta">' + legenda.join(" | ") + "</div>");
        }

        lancamentosWrapper.innerHTML = html.join("");

        var checkboxLimite = document.getElementById("comite-lancamentos-usar-limite");
        if (checkboxLimite) {
            checkboxLimite.addEventListener("change", function () {
                lancamentosUsarLimite = !!checkboxLimite.checked;
                renderLancamentosBancarios(lancamentosPayload);
                updateDashboard(getVisibleRowsData());
            });
        }
    }

    function calcularSaldoDisponivelTodos(payload) {
        var dados = payload && typeof payload === "object" ? payload : {};
        var linhaSaldo = getLinhaLancamentos(dados, "saldo_atual");
        var linhaLimite = getLinhaLancamentos(dados, "limite");
        var linhaAntecipacoes = getLinhaLancamentos(dados, "antecipacoes");
        var linhaTransferencias = getLinhaLancamentos(dados, "transferencias");

        var saldo = getBancoValor(linhaSaldo, "todos");
        var limite = lancamentosUsarLimite ? getBancoValor(linhaLimite, "todos") : 0;
        var antecipacoes = getBancoValor(linhaAntecipacoes, "todos");
        var transferencias = getBancoValor(linhaTransferencias, "todos");
        return saldo + limite + antecipacoes - transferencias;
    }

    function getResumoIconSvg(iconKey) {
        var icones = {
            pagar: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 100 20 10 10 0 000-20zm-1.3 13.3l-3-3 1.4-1.4 1.6 1.6 4.6-4.6 1.4 1.4-6 6z"/></svg>',
            adiar: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 1.8A10.2 10.2 0 112.8 12 10.21 10.21 0 0112 1.8zm0 2a8.2 8.2 0 108.2 8.2A8.21 8.21 0 0012 3.8zm1 3v5.2l3.6 2.2-1 1.7L11 13V6.8h2z"/></svg>',
            saldo_em_conta: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6.5A2.5 2.5 0 015.5 4h13A2.5 2.5 0 0121 6.5v11a2.5 2.5 0 01-2.5 2.5h-13A2.5 2.5 0 013 17.5v-11zm2.5-.5a.5.5 0 00-.5.5V8h14V6.5a.5.5 0 00-.5-.5h-13zM19 10H5v7.5a.5.5 0 00.5.5h13a.5.5 0 00.5-.5V10zm-3.8 2.2a2.3 2.3 0 110 4.6 2.3 2.3 0 010-4.6z"/></svg>',
            corrigir: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 17.2V21h3.8l11-11-3.8-3.8-11 11zM20.7 7a1 1 0 000-1.4l-2.3-2.3a1 1 0 00-1.4 0l-1.8 1.8L18.9 8.8 20.7 7z"/></svg>',
            transferir: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7h9.2l-2.1-2.1 1.4-1.4L20 8l-4.5 4.5-1.4-1.4L16.2 9H7V7zm10 10H7.8l2.1 2.1-1.4 1.4L4 16l4.5-4.5 1.4 1.4L7.8 15H17v2z"/></svg>',
            conciliar_adiantamento: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4V1L8 5l4 4V6a6 6 0 016 6c0 1.01-.25 1.96-.69 2.8l1.46 1.46A7.93 7.93 0 0020 12c0-4.42-3.58-8-8-8zM5.69 4.2L4.23 5.66A7.93 7.93 0 004 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3a6 6 0 01-6-6c0-1.01.25-1.96.69-2.8z"/></svg>',
        };
        return icones[iconKey] || "";
    }

    function buildResumoRow(label, valor, extraClass, iconKey) {
        var classes = ["comite-resumo-row"];
        if (extraClass) classes.push(extraClass);
        var iconSvg = getResumoIconSvg(iconKey);
        var labelContent = iconSvg
            ? '<span class="comite-resumo-label-group"><span class="comite-resumo-icon" aria-hidden="true">' + iconSvg + "</span><span>" + label + "</span></span>"
            : '<span class="comite-resumo-label-group"><span>' + label + "</span></span>";
        return (
            '<div class="' + classes.join(" ") + '">' +
            '<span class="comite-resumo-label">' + labelContent + "</span>" +
            '<strong class="comite-resumo-value">' + formatMoney(valor) + "</strong>" +
            "</div>"
        );
    }

    function buildDecisaoChartDataset(linhas) {
        var categorias = [
            {key: "adiar", label: "Adiar", valor: 0},
            {key: "corrigir", label: "Corrigir", valor: 0},
            {key: "pagar", label: "Pagar", valor: 0},
            {key: "transferir", label: "Transferir", valor: 0},
            {key: "conciliar_adiantamento", label: "Conciliar Adiantamento", valor: 0},
            {key: "saldo_em_conta", label: "Saldo em Conta", valor: 0},
            {key: "sem_resposta", label: "Sem resposta", valor: 0},
        ];
        var indicePorChave = {};
        categorias.forEach(function (item, index) {
            indicePorChave[item.key] = index;
        });

        (linhas || []).forEach(function (item) {
            var decisao = toText(item && item.decisao);
            var valorLiquido = toNumber(item && item.valor_liquido);
            var chave = decisao && Object.prototype.hasOwnProperty.call(indicePorChave, decisao) ? decisao : "sem_resposta";
            categorias[indicePorChave[chave]].valor += valorLiquido;
        });

        return {
            labels: categorias.map(function (item) { return item.label; }),
            series: categorias.map(function (item) { return item.valor; }),
        };
    }

    function renderOrUpdateDecisaoChart(linhas) {
        if (!comiteDecisaoChartEl) return;

        var dataset = buildDecisaoChartDataset(linhas);

        if (!window.ApexCharts) {
            comiteDecisaoChartEl.innerHTML = '<p class="comite-decisao-chart-fallback">Grafico indisponivel no momento.</p>';
            return;
        }

        var options = {
            chart: {type: "donut", height: 320, toolbar: {show: false}},
            labels: dataset.labels,
            series: dataset.series,
            colors: ["#2563eb", "#f97316", "#10b981", "#e11d48", "#7c3aed", "#0ea5e9", "#94a3b8"],
            legend: {position: "bottom"},
            dataLabels: {enabled: true},
            stroke: {width: 1},
            tooltip: {
                y: {
                    formatter: function (value) {
                        return formatMoney(value);
                    },
                },
            },
            plotOptions: {
                pie: {
                    donut: {
                        size: "58%",
                        labels: {
                            show: true,
                            value: {
                                show: true,
                                formatter: function (value) {
                                    return formatMoney(value);
                                },
                            },
                            total: {
                                show: true,
                                label: "Total",
                                formatter: function (w) {
                                    var soma = (w && w.globals && Array.isArray(w.globals.seriesTotals))
                                        ? w.globals.seriesTotals.reduce(function (acc, valor) { return acc + toNumber(valor); }, 0)
                                        : 0;
                                    return formatMoney(soma);
                                },
                            },
                        },
                    },
                },
            },
            noData: {text: "Sem valores"},
        };

        if (!comiteDecisaoChart) {
            comiteDecisaoChart = new window.ApexCharts(comiteDecisaoChartEl, options);
            comiteDecisaoChart.render();
            return;
        }

        comiteDecisaoChart.updateOptions({labels: dataset.labels}, false, true);
        comiteDecisaoChart.updateSeries(dataset.series, true);
    }

    function refreshLancamentosBancarios(options) {
        var opts = options || {};
        if (!lancamentosEndpointUrl || lancamentosRefreshInFlight) return Promise.resolve();

        lancamentosRefreshInFlight = true;
        var url = new URL(lancamentosEndpointUrl, window.location.origin);
        if (selectedDateIso) {
            url.searchParams.set("data", selectedDateIso);
        }

        return fetch(url.toString(), {
            method: "GET",
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false || !result.body.payload) {
                    return;
                }
                lancamentosPayload = result.body.payload;
                renderLancamentosBancarios(lancamentosPayload);
                updateDashboard(getVisibleRowsData());
            })
            .catch(function () {
                if (!opts.silent) {
                    setSaveStatus("Falha ao atualizar lancamentos bancarios.", "comite-diario-save-status--error");
                }
            })
            .finally(function () {
                lancamentosRefreshInFlight = false;
            });
    }

    function iniciarPollingLancamentosBancarios() {
        if (lancamentosPollingTimer) {
            window.clearInterval(lancamentosPollingTimer);
        }
        lancamentosPollingTimer = window.setInterval(function () {
            if (document.hidden) return;
            refreshLancamentosBancarios({silent: true});
        }, 10000);
    }

    function applyDecisionRulesToRow(rowData) {
        if (!rowData) return false;
        var changed = false;
        var decisao = toText(rowData.decisao);

        if (decisao !== "transferir") {
            if (toText(rowData.de_banco_id)) changed = true;
            if (toText(rowData.para_banco_id)) changed = true;
            if (toText(rowData.para_empresa_id)) changed = true;
            rowData.de_banco_id = "";
            rowData.de_banco_label = "";
            rowData.para_banco_id = "";
            rowData.para_banco_label = "";
            rowData.para_empresa_id = "";
            rowData.para_empresa_label = "";
        }

        if (decisao !== "adiar") {
            if (toText(rowData.data_prorrogada_iso)) changed = true;
            rowData.data_prorrogada_iso = "";
            rowData.data_prorrogada = "";
        }

        return changed;
    }

    function updateLocalLabels(rowData) {
        applyDecisionRulesToRow(rowData);
        var empresaTitularId = String(rowData.empresa_titular_id || "");
        var parceiroId = String(rowData.parceiro_id || "");
        var naturezaId = String(rowData.natureza_id || "");
        var centroResultadoId = String(rowData.centro_resultado_id || "");
        var deBancoId = String(rowData.de_banco_id || "");
        var paraBancoId = String(rowData.para_banco_id || "");
        var paraEmpresaId = String(rowData.para_empresa_id || "");
        var receitaDespesa = String(rowData.receita_despesa || "");
        var tipoMovimento = String(rowData.tipo_movimento || "");
        var decisao = String(rowData.decisao || "");

        rowData.empresa_titular_label = empresasValues[empresaTitularId] || "";
        rowData.parceiro_label = parceirosValues[parceiroId] || "";
        rowData.natureza_label = naturezasValues[naturezaId] || "";
        rowData.centro_resultado_label = centrosValues[centroResultadoId] || "";
        rowData.de_banco_label = bancosValues[deBancoId] || "";
        rowData.para_banco_label = bancosValues[paraBancoId] || "";
        rowData.para_empresa_label = empresasValues[paraEmpresaId] || "";
        rowData.receita_despesa_label = receitaDespesaValues[receitaDespesa] || receitaDespesa;
        rowData.tipo_movimento_label = tipoMovimentoValues[tipoMovimento] || tipoMovimento;
        rowData.decisao_label = decisaoValues[decisao] || decisao;
        rowData.data_negociacao = formatDateIsoToBr(rowData.data_negociacao_iso);
        rowData.data_vencimento = formatDateIsoToBr(rowData.data_vencimento_iso);
        rowData.data_prorrogada = formatDateIsoToBr(rowData.data_prorrogada_iso);
    }

    function restoreCellValue(cell, oldValue) {
        if (!cell) return;
        if (typeof cell.restoreOldValue === "function") {
            cell.restoreOldValue();
            return;
        }
        internalUpdate = true;
        cell.setValue(oldValue, true);
        internalUpdate = false;
    }

    function refreshRowVisual(row) {
        if (!row) return;
        if (typeof row.reformat === "function") {
            row.reformat();
            return;
        }
        if (tabela && typeof tabela.redraw === "function") {
            tabela.redraw(true);
        }
    }

    function rollbackEditedField(row, rowData, field, oldValue) {
        if (!row || !rowData) return;
        var rollbackData = Object.assign({}, rowData);
        if (field) rollbackData[field] = oldValue;
        updateLocalLabels(rollbackData);
        internalUpdate = true;
        Promise.resolve(row.update(rollbackData))
            .catch(function () {
                if (field) {
                    restoreCellValue(row.getCell(field), oldValue);
                }
            })
            .finally(function () {
                internalUpdate = false;
                refreshRowVisual(row);
            });
    }

    function buildPayloadFromRow(rowData) {
        var payload = {
            data_negociacao: toText(rowData.data_negociacao_iso),
            data_vencimento: toText(rowData.data_vencimento_iso),
            receita_despesa: toText(rowData.receita_despesa),
            empresa_titular_id: toText(rowData.empresa_titular_id),
            parceiro_id: toText(rowData.parceiro_id),
            natureza_id: toText(rowData.natureza_id),
            centro_resultado_id: toText(rowData.centro_resultado_id),
            historico: toText(rowData.historico),
            numero_nota: toText(rowData.numero_nota),
            valor_liquido: toText(rowData.valor_liquido),
            tipo_movimento: toText(rowData.tipo_movimento),
            decisao: toText(rowData.decisao),
            data_prorrogada: toText(rowData.data_prorrogada_iso),
            de_banco_id: toText(rowData.de_banco_id),
            para_banco_id: toText(rowData.para_banco_id),
            para_empresa_id: toText(rowData.para_empresa_id),
        };

        if (payload.decisao !== "transferir") {
            payload.de_banco_id = "";
            payload.para_banco_id = "";
            payload.para_empresa_id = "";
        }
        if (payload.decisao !== "adiar") {
            payload.data_prorrogada = "";
        }

        return payload;
    }

    function saveRowAutomatically(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;

        var rowData = row.getData() || {};
        if (!rowData.editar_url) return;

        var rowId = rowData.id;
        var editedField = typeof cell.getField === "function" ? cell.getField() : "";
        var currentSeq = Number(seqByRowId[rowId] || 0) + 1;
        seqByRowId[rowId] = currentSeq;

        var oldValue = typeof cell.getOldValue === "function" ? cell.getOldValue() : null;
        var payload = buildPayloadFromRow(rowData);
        var formData = new FormData();
        appendCsrfToken(formData);
        Object.keys(payload).forEach(function (key) {
            formData.append(key, payload[key]);
        });

        setSaveStatus("Salvando alteracao...", "comite-diario-save-status--progress");

        var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
        var timeoutId = null;
        if (controller && typeof window.setTimeout === "function") {
            timeoutId = window.setTimeout(function () {
                controller.abort();
            }, 15000);
        }

        var fetchOptions = {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        };
        if (controller) {
            fetchOptions.signal = controller.signal;
        }

        fetch(rowData.editar_url, fetchOptions)
            .then(parseJsonResponse)
            .then(function (result) {
                if (seqByRowId[rowId] !== currentSeq) return;

                if (!result.ok || !result.body || result.body.ok === false || !result.body.registro) {
                    rollbackEditedField(row, rowData, editedField, oldValue);
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao salvar.",
                        "comite-diario-save-status--error"
                    );
                    return;
                }

                internalUpdate = true;
                Promise.resolve(row.update(result.body.registro))
                    .then(function () {
                        var updatedRowData = row.getData() || {};
                        updateLocalLabels(updatedRowData);
                        refreshRowVisual(row);

                        var rowIndex = data.findIndex(function (item) {
                            return Number(item.id) === Number(result.body.registro.id);
                        });
                        if (rowIndex >= 0) {
                            data[rowIndex] = updatedRowData;
                        }

                        rebuildExternalFiltersByDate();
                        updateDashboard(getVisibleRowsData());
                        refreshLancamentosBancarios({silent: true});
                        setSaveStatus("Salvo automaticamente.", "comite-diario-save-status--ok");
                    })
                    .catch(function () {
                        rollbackEditedField(row, rowData, editedField, oldValue);
                        setSaveStatus("Falha ao aplicar retorno no front.", "comite-diario-save-status--error");
                    })
                    .finally(function () {
                        internalUpdate = false;
                    });
            })
            .catch(function (error) {
                if (seqByRowId[rowId] !== currentSeq) return;
                rollbackEditedField(row, rowData, editedField, oldValue);
                if (error && error.name === "AbortError") {
                    setSaveStatus("Tempo de resposta excedido ao salvar. Alteracao revertida.", "comite-diario-save-status--error");
                    return;
                }
                setSaveStatus("Falha ao salvar. Alteracao revertida.", "comite-diario-save-status--error");
            })
            .finally(function () {
                if (timeoutId) window.clearTimeout(timeoutId);
            });
    }

    function onCellEdited(cell) {
        if (internalUpdate) return;
        var row = cell && typeof cell.getRow === "function" ? cell.getRow() : null;
        var rowData = row ? row.getData() : null;
        var changedByRules = applyDecisionRulesToRow(rowData);

        if (row && rowData) {
            updateLocalLabels(rowData);
        }

        if (changedByRules && row && rowData && typeof row.update === "function") {
            internalUpdate = true;
            Promise.resolve(row.update(rowData))
                .finally(function () {
                    internalUpdate = false;
                    refreshRowVisual(row);
                    saveRowAutomatically(cell);
                });
            return;
        }

        saveRowAutomatically(cell);
    }

    function getDataScopedByDate() {
        if (!selectedDateIso) return data.slice();
        return data.filter(function (rowData) {
            return toText(rowData.data_negociacao_iso) === selectedDateIso;
        });
    }

    function createFilterDefinitions() {
        return [
            {
                key: "receita_despesa_label",
                label: "Receita/Despesa",
                singleSelect: false,
                extractValue: function (rowData) {
                    if (!rowData) return "";
                    var receitaDespesa = String(rowData.receita_despesa || "");
                    return receitaDespesaValues[receitaDespesa] || rowData.receita_despesa_label || "";
                },
            },
            {
                key: "decisao_label",
                label: "Decisao",
                singleSelect: false,
                extractValue: function (rowData) {
                    if (!rowData) return "";
                    var decisao = String(rowData.decisao || "");
                    return decisaoValues[decisao] || rowData.decisao_label || "";
                },
            },
            {
                key: "empresa_titular_label",
                label: "Empresa Titular",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.empresa_titular_label : "";
                },
            },
            {
                key: "parceiro_label",
                label: "Parceiro",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.parceiro_label : "";
                },
            },
            {
                key: "centro_resultado_label",
                label: "Centro Resultado",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.centro_resultado_label : "";
                },
            },
            {
                key: "data_vencimento",
                label: "Data Vencimento",
                singleSelect: false,
                extractValue: function (rowData) {
                    if (!rowData) return "";
                    return rowData.data_vencimento || formatDateIsoToBr(rowData.data_vencimento_iso);
                },
            },
        ];
    }

    function rebuildExternalFiltersByDate() {
        if (!window.ModuleFilterCore || !filtrosColunaEsquerda || !filtrosColunaDireita) {
            externalFilters = null;
            if (tabela && typeof tabela.refreshFilter === "function") {
                tabela.refreshFilter();
            }
            return;
        }

        if (secFiltros) {
            secFiltros.dataset.moduleFiltersManual = "true";
            var placeholder = secFiltros.querySelector(".module-filters-placeholder");
            if (placeholder) placeholder.remove();
        }

        externalFilters = window.ModuleFilterCore.create({
            data: getDataScopedByDate(),
            definitions: createFilterDefinitions(),
            leftColumn: filtrosColunaEsquerda,
            rightColumn: filtrosColunaDireita,
            onChange: function () {
                if (tabela && typeof tabela.refreshFilter === "function") {
                    tabela.refreshFilter();
                }
            },
        });

        if (tabela && typeof tabela.refreshFilter === "function") {
            tabela.refreshFilter();
        }
    }

    function matchesGlobalFilters(rowData) {
        if (selectedDateIso && toText(rowData.data_negociacao_iso) !== selectedDateIso) {
            return false;
        }
        if (externalFilters && typeof externalFilters.matchesRecord === "function") {
            return externalFilters.matchesRecord(rowData);
        }
        return true;
    }

    function getVisibleRowsData() {
        if (!tabela || typeof tabela.getData !== "function") return getDataScopedByDate();
        return tabela.getData("active") || [];
    }

    function updateDashboard(linhas) {
        var valores = {
            pagar: 0,
            adiar: 0,
            saldo_em_conta: 0,
            corrigir: 0,
            transferir: 0,
            conciliar_adiantamento: 0,
        };

        (linhas || []).forEach(function (item) {
            var decisao = toText(item && item.decisao);
            var valor = toNumber(item && item.valor_liquido);
            if (Object.prototype.hasOwnProperty.call(valores, decisao)) {
                valores[decisao] += valor;
            }
        });

        var totalAPagar = valores.pagar + valores.transferir + valores.saldo_em_conta;
        var saldoDisponivelTodos = calcularSaldoDisponivelTodos(lancamentosPayload);
        var saldoComite = saldoDisponivelTodos - valores.pagar - valores.saldo_em_conta;

        var html = [];
        html.push(buildResumoRow("Pagar", valores.pagar, "", "pagar"));
        html.push(buildResumoRow("Prorrogado", valores.adiar, "", "adiar"));
        html.push(buildResumoRow("Saldo em Conta", valores.saldo_em_conta, "", "saldo_em_conta"));
        html.push(buildResumoRow("Correcoes", valores.corrigir, "", "corrigir"));
        html.push(buildResumoRow("Transferencias", valores.transferir, "", "transferir"));
        html.push(buildResumoRow("Conciliar Adiantamento", valores.conciliar_adiantamento, "", "conciliar_adiantamento"));
        html.push(buildResumoRow("Total a Pagar", totalAPagar, "is-total"));
        html.push(buildResumoRow("Saldo Comite", saldoComite, "is-saldo"));
        if (comiteResumoWrapper) {
            comiteResumoWrapper.innerHTML = html.join("");
        }
        renderOrUpdateDecisaoChart(linhas);
    }

    function applyDateFilterValue(nextDateIso) {
        selectedDateIso = toText(nextDateIso);
        if (filtroDataInput && filtroDataInput.value !== selectedDateIso) {
            filtroDataInput.value = selectedDateIso;
        }
        rebuildExternalFiltersByDate();
        updateDashboard(getVisibleRowsData());
        refreshLancamentosBancarios({silent: true});
    }

    function bindFilterClearButtons() {
        function limparTodosFiltros() {
            if (externalFilters && typeof externalFilters.clearAllFilters === "function") {
                externalFilters.clearAllFilters();
            }
            if (tabela && typeof tabela.clearHeaderFilter === "function") {
                tabela.clearHeaderFilter();
            }
            if (tabela && typeof tabela.refreshFilter === "function") {
                tabela.refreshFilter();
            }
        }

        var clearButtons = document.querySelectorAll(".module-filters-clear-all, .module-shell-clear-filters");
        clearButtons.forEach(function (button) {
            button.addEventListener("click", limparTodosFiltros);
        });
    }

    function toggleDecisionDependentFormFields() {
        if (!cadastroDecisaoSelect) return;
        var decisao = toText(cadastroDecisaoSelect.value);
        var isTransferir = decisao === "transferir";
        var isAdiar = decisao === "adiar";

        cadastroTransferFields.forEach(function (field) {
            if (!field) return;
            field.required = false;
            field.disabled = !isTransferir;
            if (!isTransferir) {
                field.value = "";
            }
        });

        if (cadastroDataProrrogadaInput) {
            cadastroDataProrrogadaInput.required = false;
            cadastroDataProrrogadaInput.disabled = !isAdiar;
            if (!isAdiar) {
                cadastroDataProrrogadaInput.value = "";
            }
        }
    }

    function submitCreate(event) {
        if (!event) return;
        event.preventDefault();
        if (!tabela || typeof tabela.addData !== "function") return;

        var url = cadastroForm.getAttribute("action");
        if (!url) return;

        var formData = new FormData(cadastroForm);
        if (!formData.get("csrfmiddlewaretoken")) {
            appendCsrfToken(formData);
        }

        setSaveStatus("Criando registro...", "comite-diario-save-status--progress");

        fetch(url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false || !result.body.registro) {
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao criar registro.",
                        "comite-diario-save-status--error"
                    );
                    return;
                }

                data.push(result.body.registro);
                Promise.resolve(tabela.addData([result.body.registro], true))
                    .then(function () {
                        cadastroForm.reset();
                        toggleDecisionDependentFormFields();
                        rebuildExternalFiltersByDate();
                        updateDashboard(getVisibleRowsData());
                        refreshLancamentosBancarios({silent: true});
                        setSaveStatus("Registro criado e tabela atualizada.", "comite-diario-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro criado, mas houve falha ao atualizar a tabela.",
                            "comite-diario-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao criar registro.", "comite-diario-save-status--error");
            });
    }

    function deleteRowByCell(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;
        var rowData = row.getData() || {};
        if (!rowData.excluir_url) return;
        if (!window.confirm("Excluir registro?")) return;

        var formData = new FormData();
        appendCsrfToken(formData);

        setSaveStatus("Excluindo registro...", "comite-diario-save-status--progress");

        fetch(rowData.excluir_url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false) {
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao excluir registro.",
                        "comite-diario-save-status--error"
                    );
                    return;
                }

                var idExcluido = Number(rowData.id);
                data = data.filter(function (item) {
                    return Number(item.id) !== idExcluido;
                });

                Promise.resolve(row.delete())
                    .then(function () {
                        rebuildExternalFiltersByDate();
                        updateDashboard(getVisibleRowsData());
                        refreshLancamentosBancarios({silent: true});
                        setSaveStatus("Registro excluido e tabela atualizada.", "comite-diario-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro excluido, mas houve falha ao atualizar a tabela.",
                            "comite-diario-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao excluir registro.", "comite-diario-save-status--error");
            });
    }

    tabela = window.TabulatorDefaults.create("#comite-diario-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {
                title: "Data Negociacao",
                field: "data_negociacao_iso",
                editor: "input",
                editorParams: {elementAttributes: {type: "date"}},
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
                cellEdited: onCellEdited,
                width: 150,
            },
            {
                title: "Data Vencimento",
                field: "data_vencimento_iso",
                editor: "input",
                editorParams: {elementAttributes: {type: "date"}},
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
                cellEdited: onCellEdited,
                width: 150,
            },
            {
                title: "Receita/Despesa",
                field: "receita_despesa",
                editor: "list",
                editorParams: {values: receitaDespesaValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var value = String(cell.getValue() || row.receita_despesa || "");
                    return receitaDespesaValues[value] || row.receita_despesa_label || value;
                },
                cellEdited: onCellEdited,
                width: 170,
            },
            {
                title: "Empresa Titular",
                field: "empresa_titular_id",
                editor: "list",
                editorParams: {values: empresasValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.empresa_titular_label || empresasValues[String(row.empresa_titular_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 220,
            },
            {
                title: "Parceiro",
                field: "parceiro_id",
                editor: "list",
                editorParams: {values: parceirosValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.parceiro_label || parceirosValues[String(row.parceiro_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 240,
            },
            {
                title: "Natureza",
                field: "natureza_id",
                editor: "list",
                editorParams: {values: naturezasValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.natureza_label || naturezasValues[String(row.natureza_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 240,
            },
            {
                title: "Centro Resultado",
                field: "centro_resultado_id",
                editor: "list",
                editorParams: {values: centrosValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.centro_resultado_label || centrosValues[String(row.centro_resultado_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 220,
            },
            {title: "Historico", field: "historico", editor: "input", cellEdited: onCellEdited, width: 260},
            {title: "Numero Nota", field: "numero_nota", editor: "input", cellEdited: onCellEdited, width: 130},
            {
                title: "Valor Liquido",
                field: "valor_liquido",
                editor: "input",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatMoney(cell.getValue());
                },
                cellEdited: onCellEdited,
                width: 140,
            },
            {
                title: "Tipo Movimento",
                field: "tipo_movimento",
                editor: "list",
                editorParams: {values: tipoMovimentoValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var value = String(cell.getValue() || row.tipo_movimento || "");
                    return tipoMovimentoValues[value] || row.tipo_movimento_label || value;
                },
                cellEdited: onCellEdited,
                width: 170,
            },
            {
                title: "Decisao",
                field: "decisao",
                editor: "list",
                editorParams: {values: decisaoValues, clearable: false},
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    var value = String(cell.getValue() || row.decisao || "");
                    return decisaoValues[value] || row.decisao_label || value;
                },
                cellEdited: onCellEdited,
                width: 200,
            },
            {
                title: "Data Prorrogada",
                field: "data_prorrogada_iso",
                editor: "input",
                editorParams: {elementAttributes: {type: "date"}},
                editable: function (cell) {
                    var rowData = cell && cell.getRow ? cell.getRow().getData() : null;
                    return toText(rowData && rowData.decisao) === "adiar";
                },
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
                cellEdited: onCellEdited,
                width: 150,
            },
            {
                title: "De Banco",
                field: "de_banco_id",
                editor: "list",
                editorParams: {values: bancosValues, clearable: true},
                editable: function (cell) {
                    var rowData = cell && cell.getRow ? cell.getRow().getData() : null;
                    return toText(rowData && rowData.decisao) === "transferir";
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.de_banco_label || bancosValues[String(row.de_banco_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 170,
            },
            {
                title: "Para Banco",
                field: "para_banco_id",
                editor: "list",
                editorParams: {values: bancosValues, clearable: true},
                editable: function (cell) {
                    var rowData = cell && cell.getRow ? cell.getRow().getData() : null;
                    return toText(rowData && rowData.decisao) === "transferir";
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.para_banco_label || bancosValues[String(row.para_banco_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 170,
            },
            {
                title: "Para Empresa",
                field: "para_empresa_id",
                editor: "list",
                editorParams: {values: empresasValues, clearable: true},
                editable: function (cell) {
                    var rowData = cell && cell.getRow ? cell.getRow().getData() : null;
                    return toText(rowData && rowData.decisao) === "transferir";
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.para_empresa_label || empresasValues[String(row.para_empresa_id || "")] || "";
                },
                cellEdited: onCellEdited,
                width: 220,
            },
            {
                title: "Acoes",
                field: "acoes",
                width: 120,
                headerSort: false,
                hozAlign: "center",
                formatter: function () {
                    return '<button type="button" class="btn-danger">Excluir</button>';
                },
                cellClick: function (event, cell) {
                    event.preventDefault();
                    deleteRowByCell(cell);
                },
            },
        ],
    });

    if (tabela && typeof tabela.setFilter === "function") {
        tabela.setFilter(matchesGlobalFilters);
    }

    if (tabela && typeof tabela.on === "function") {
        tabela.on("dataFiltered", function (_filters, rows) {
            var linhas = (rows || []).map(function (row) { return row.getData(); });
            updateDashboard(linhas);
        });
    }

    if (filtroDataInput) {
        filtroDataInput.addEventListener("change", function () {
            applyDateFilterValue(filtroDataInput.value);
        });
    }

    if (btnUltimaData) {
        btnUltimaData.addEventListener("click", function () {
            if (!ultimaDataIso) return;
            applyDateFilterValue(ultimaDataIso);
        });
    }

    if (btnLimparData) {
        btnLimparData.addEventListener("click", function () {
            applyDateFilterValue("");
        });
    }

    cadastroForm.addEventListener("submit", submitCreate);
    if (cadastroDecisaoSelect) {
        cadastroDecisaoSelect.addEventListener("change", toggleDecisionDependentFormFields);
    }

    bindFilterClearButtons();
    toggleDecisionDependentFormFields();
    renderLancamentosBancarios(lancamentosPayload);
    iniciarPollingLancamentosBancarios();
    applyDateFilterValue("");
    setSaveStatus("", "");
})();
