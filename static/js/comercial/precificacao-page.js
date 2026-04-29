(function () {
    if (!window.Tabulator) return;

    var saveStatusEl = document.getElementById("precificacao-save-status");
    var despesasGlobaisEls = {
        prazoDias: document.getElementById("precificacao-despesas-prazo-dias"),
        cifAtivo: document.getElementById("precificacao-despesas-cif-ativo"),
        cifManualAtivo: document.getElementById("precificacao-despesas-cif-manual-ativo"),
        cifRota: document.getElementById("precificacao-despesas-cif-rota"),
        cifManualValor: document.getElementById("precificacao-despesas-cif-manual-valor"),
    };
    var DESPESAS_GLOBAIS_REQUIRED_KEYS = [
        "prazoDias",
        "cifAtivo",
        "cifManualAtivo",
        "cifRota",
        "cifManualValor",
    ];

    var DATA_IDS = {
        calculadora: "precificacao-calculadora-tabulator-data",
        simulacao: "precificacao-simulacao-tabulator-data",
        materia_prima: "precificacao-materia-prima-tabulator-data",
        produto_cmv: "precificacao-produto-cmv-tabulator-data",
        produto_despesas: "precificacao-produto-despesas-tabulator-data",
        produto_impostos: "precificacao-produto-impostos-tabulator-data",
        produto_preco_venda: "precificacao-produto-preco-venda-tabulator-data",
        lucro: "precificacao-lucro-tabulator-data",
    };

    var TARGET_IDS = {
        calculadora: "#precificacao-calculadora-tabulator",
        simulacao: "#precificacao-simulacao-tabulator",
        materia_prima: "#precificacao-materia-prima-tabulator",
        produto_cmv: "#precificacao-produto-cmv-tabulator",
        produto_despesas: "#precificacao-produto-despesas-tabulator",
        produto_impostos: "#precificacao-produto-impostos-tabulator",
        produto_preco_venda: "#precificacao-produto-preco-venda-tabulator",
        lucro: "#precificacao-lucro-tabulator",
    };

    var EDITABLE_FIELDS = {
        calculadora: ["volume", "preco", "prazo", "frete"],
        simulacao: ["margem_requerida", "frete"],
        materia_prima: ["ativo", "valor", "frete_mp", "credito"],
        produto_cmv: ["acucar_quebra", "emb_primaria_quebra", "emb_secundaria_quebra"],
        produto_despesas: [
            "financeiro_taxa",
            "inadimplencia_taxa",
            "administracao_taxa",
            "producao_ativo",
            "producao_valor",
            "log_op_logistica_ativo",
        ],
        produto_impostos: [
            "interno_ativo",
            "imposto_aliquota",
            "imposto_interno_aliquota",
            "pro_goias_ativo",
            "pro_goias_aliquota_a",
            "pro_goias_aliquota_b",
        ],
        produto_preco_venda: ["pv_bruto", "interno_ativo", "comissao_aliquota", "contrato_aliquota"],
    };

    var BOOL_FIELDS = {
        materia_prima: ["ativo"],
        produto_despesas: ["producao_ativo", "log_op_logistica_ativo"],
        produto_impostos: ["interno_ativo", "pro_goias_ativo"],
        produto_preco_venda: ["interno_ativo"],
    };

    var dataByKey = {};
    var tables = {};
    var seqByRow = {};
    var internalUpdate = false;
    var syncingDespesasGlobais = false;

    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});

    function parseJsonScript(id) {
        var el = document.getElementById(id);
        if (!el) return [];
        try {
            var parsed = JSON.parse(el.textContent || "[]");
            return Array.isArray(parsed) ? parsed : [];
        } catch (_err) {
            return [];
        }
    }

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function toNumber(value) {
        if (typeof value === "number") return Number.isFinite(value) ? value : 0;
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

    function formatDecimal(value, casas) {
        var number = toNumber(value);
        return number.toLocaleString("pt-BR", {
            minimumFractionDigits: casas,
            maximumFractionDigits: casas,
        });
    }

    function formatPercentRatio(value, casas) {
        var number = toNumber(value) * 100;
        var decimals = Number.isFinite(Number(casas)) ? Number(casas) : 2;
        return number.toLocaleString("pt-BR", {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        }) + "%";
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

    function postFormData(url, formData) {
        return fetch(url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        }).then(parseJsonResponse);
    }

    function setSaveStatus(text, tone) {
        if (!saveStatusEl) return;
        saveStatusEl.classList.remove(
            "precificacao-save-status--ok",
            "precificacao-save-status--error",
            "precificacao-save-status--progress"
        );
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function toBool(value) {
        if (value === true) return true;
        var text = toText(value).toLowerCase();
        return text === "true" || text === "1" || text === "on" || text === "sim";
    }

    function boolFormatter(cell) {
        return toBool(cell.getValue()) ? "Sim" : "Não";
    }

    function boolMutator(value) {
        return toBool(value);
    }

    function appendPayloadField(formData, key, value, isBool) {
        if (isBool) {
            formData.append(key, toBool(value) ? "true" : "false");
            return;
        }
        if (value === null || value === undefined) {
            formData.append(key, "");
            return;
        }
        formData.append(key, String(value));
    }

    function buildSimulacaoPayload(rowData) {
        var rows = [];
        if (tables.simulacao && typeof tables.simulacao.getData === "function") {
            rows = tables.simulacao.getData() || [];
        }
        if (!rows.length) {
            rows = Array.isArray(dataByKey.simulacao) ? dataByKey.simulacao.slice() : [];
        }

        var compra = null;
        var venda = null;
        rows.forEach(function (item) {
            var tipo = toText(item && item.tipo).toLowerCase();
            if (tipo === "compra" && !compra) compra = item;
            if (tipo === "venda" && !venda) venda = item;
        });

        if (!compra) compra = {margem_requerida: 0, frete: 0, tipo: "compra"};
        if (!venda) venda = {margem_requerida: 0, frete: 0, tipo: "venda"};

        var editedTipo = toText(rowData && rowData.tipo).toLowerCase();
        if (editedTipo === "compra") {
            compra = Object.assign({}, compra, rowData);
        } else if (editedTipo === "venda") {
            venda = Object.assign({}, venda, rowData);
        }

        return {
            margem_requerida_compra: compra.margem_requerida,
            margem_requerida_venda: venda.margem_requerida,
            frete_compra: compra.frete,
            frete_venda: venda.frete,
        };
    }

    function getDespesasRows() {
        if (!tables.produto_despesas || typeof tables.produto_despesas.getData !== "function") return [];
        var rows = tables.produto_despesas.getData() || [];
        return Array.isArray(rows) ? rows : [];
    }

    function hasDespesasGlobaisControls() {
        return DESPESAS_GLOBAIS_REQUIRED_KEYS.every(function (key) {
            return !!despesasGlobaisEls[key];
        });
    }

    function applyDespesasControlEnabledState() {
        var el = despesasGlobaisEls;
        if (!hasDespesasGlobaisControls()) return;
        var cifAtivo = !!el.cifAtivo.checked;
        var cifManualAtivo = !!el.cifManualAtivo.checked;
        el.cifManualAtivo.disabled = !cifAtivo;
        el.cifRota.disabled = !cifAtivo || cifManualAtivo;
        el.cifManualValor.disabled = !cifAtivo || !cifManualAtivo;
    }

    function syncDespesasGlobaisFromRows(rows) {
        var el = despesasGlobaisEls;
        if (!hasDespesasGlobaisControls()) return;
        var baseRow = Array.isArray(rows) && rows.length ? rows[0] : null;
        syncingDespesasGlobais = true;
        if (baseRow) {
            el.prazoDias.value = String(toNumber(baseRow.prazo_dias));
            el.cifAtivo.checked = toBool(baseRow.cif_ativo);
            el.cifManualAtivo.checked = toBool(baseRow.cif_manual_ativo);
            el.cifRota.value = toText(baseRow.cif_rota);
            el.cifManualValor.value = String(toNumber(baseRow.cif_manual_valor));
        } else {
            el.prazoDias.value = "0";
            el.cifAtivo.checked = false;
            el.cifManualAtivo.checked = false;
            el.cifRota.value = "";
            el.cifManualValor.value = "0";
        }
        applyDespesasControlEnabledState();
        syncingDespesasGlobais = false;
    }

    function saveDespesasGlobais() {
        if (internalUpdate || syncingDespesasGlobais) return;
        var el = despesasGlobaisEls;
        if (!hasDespesasGlobaisControls()) return;

        var rows = getDespesasRows();
        if (!rows.length) return;
        var rowRef = rows[0];
        if (!rowRef || !rowRef.editar_url) return;

        var formData = new FormData();
        appendCsrfToken(formData);
        appendPayloadField(formData, "aplicar_global_despesas", true, true);
        appendPayloadField(formData, "prazo_dias", toNumber(el.prazoDias.value), false);
        appendPayloadField(formData, "cif_ativo", el.cifAtivo.checked, true);
        appendPayloadField(formData, "cif_manual_ativo", el.cifManualAtivo.checked, true);
        appendPayloadField(formData, "cif_rota", toText(el.cifRota.value), false);
        appendPayloadField(formData, "cif_manual_valor", toNumber(el.cifManualValor.value), false);

        setSaveStatus("Salvando alteracao...", "precificacao-save-status--progress");
        postFormData(rowRef.editar_url, formData)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false || !result.body.payload) {
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao salvar.",
                        "precificacao-save-status--error"
                    );
                    return;
                }
                applyPayload(result.body.payload);
                setSaveStatus(
                    result.body && result.body.message ? result.body.message : "Salvo automaticamente.",
                    "precificacao-save-status--ok"
                );
            })
            .catch(function () {
                setSaveStatus("Falha ao salvar.", "precificacao-save-status--error");
            });
    }

    function makeSaveHandler(tableKey) {
        return function (cell) {
            if (internalUpdate) return;
            if (!cell || typeof cell.getRow !== "function") return;
            var row = cell.getRow();
            var rowData = row ? row.getData() : null;
            if (!rowData || !rowData.editar_url) return;

            var oldData = Object.assign({}, rowData);
            var seqKey = tableKey + ":" + String(rowData.id || "");
            var currentSeq = Number(seqByRow[seqKey] || 0) + 1;
            seqByRow[seqKey] = currentSeq;

            var formData = new FormData();
            appendCsrfToken(formData);

            if (tableKey === "simulacao") {
                var simulacaoPayload = buildSimulacaoPayload(rowData);
                appendPayloadField(formData, "margem_requerida_compra", simulacaoPayload.margem_requerida_compra, false);
                appendPayloadField(formData, "margem_requerida_venda", simulacaoPayload.margem_requerida_venda, false);
                appendPayloadField(formData, "frete_compra", simulacaoPayload.frete_compra, false);
                appendPayloadField(formData, "frete_venda", simulacaoPayload.frete_venda, false);
            } else {
                var boolFields = BOOL_FIELDS[tableKey] || [];
                var editableFields = EDITABLE_FIELDS[tableKey] || [];
                editableFields.forEach(function (field) {
                    appendPayloadField(formData, field, rowData[field], boolFields.indexOf(field) >= 0);
                });
            }

            setSaveStatus("Salvando alteracao...", "precificacao-save-status--progress");
            postFormData(rowData.editar_url, formData)
                .then(function (result) {
                    if (seqByRow[seqKey] !== currentSeq) return;
                    if (!result.ok || !result.body || result.body.ok === false || !result.body.payload) {
                        Promise.resolve(row.update(oldData)).finally(function () {
                            setSaveStatus(
                                result.body && result.body.message ? result.body.message : "Falha ao salvar.",
                                "precificacao-save-status--error"
                            );
                        });
                        return;
                    }

                    applyPayload(result.body.payload);
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Salvo automaticamente.",
                        "precificacao-save-status--ok"
                    );
                })
                .catch(function () {
                    if (seqByRow[seqKey] !== currentSeq) return;
                    Promise.resolve(row.update(oldData)).finally(function () {
                        setSaveStatus("Falha ao salvar. Alteracao revertida.", "precificacao-save-status--error");
                    });
                });
        };
    }

    function applyPayload(payload) {
        if (!payload || typeof payload !== "object") return;
        internalUpdate = true;
        var keys = Object.keys(TARGET_IDS);
        var chain = Promise.resolve();
        keys.forEach(function (key) {
            if (!tables[key] || !Array.isArray(payload[key])) return;
            dataByKey[key] = payload[key].slice();
            chain = chain.then(function () {
                return tables[key].setData(dataByKey[key]);
            });
        });
        chain.finally(function () {
            internalUpdate = false;
            if (Array.isArray(dataByKey.produto_despesas)) {
                syncDespesasGlobaisFromRows(dataByKey.produto_despesas);
            }
        });
    }

    function createTable(selector, options) {
        if (window.TabulatorDefaults && typeof window.TabulatorDefaults.create === "function") {
            return window.TabulatorDefaults.create(selector, options);
        }
        return new window.Tabulator(selector, options);
    }

    function moneyColumn(title, field, editable, saveHandler, cssClass) {
        var isEditable = typeof editable === "function" ? editable : !!editable;
        var columnDef = {
            title: title,
            field: field,
            hozAlign: "right",
            editor: editable ? "number" : false,
            editable: isEditable,
            editorParams: {step: "0.0001"},
            formatter: function (cell) {
                return formatMoney(cell.getValue());
            },
            cellEdited: saveHandler || null,
            minWidth: 130,
        };
        if (cssClass) columnDef.cssClass = cssClass;
        return columnDef;
    }

    function moneyColumnSimulacaoCompra(title, field) {
        return {
            title: title,
            field: field,
            hozAlign: "right",
            editor: false,
            editable: false,
            formatter: function (cell) {
                var row = (cell && cell.getRow && cell.getRow().getData()) || {};
                if (toText(row.tipo).toLowerCase() === "venda") return "";
                return formatMoney(cell.getValue());
            },
            minWidth: 130,
        };
    }

    function decimalColumn(title, field, casas, editable, saveHandler, cssClass) {
        var isEditable = typeof editable === "function" ? editable : !!editable;
        var columnDef = {
            title: title,
            field: field,
            hozAlign: "right",
            editor: editable ? "number" : false,
            editable: isEditable,
            editorParams: {step: "0.0001"},
            formatter: function (cell) {
                return formatDecimal(cell.getValue(), casas || 4);
            },
            cellEdited: saveHandler || null,
            minWidth: 110,
        };
        if (cssClass) columnDef.cssClass = cssClass;
        return columnDef;
    }

    function percentEditor(cell, onRendered, success, cancel) {
        var input = document.createElement("input");
        var committed = false;

        input.type = "text";
        input.className = "tabulator-percent-editor";
        input.value = String((toNumber(cell.getValue()) * 100).toFixed(4)).replace(/\.?0+$/, "");

        function commit() {
            if (committed) return;
            committed = true;
            success(toNumber(input.value) / 100);
        }

        onRendered(function () {
            input.focus();
            input.select();
        });

        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                commit();
            } else if (event.key === "Escape") {
                committed = true;
                cancel();
            }
        });

        input.addEventListener("blur", commit);
        return input;
    }

    function percentColumn(title, field, editable, saveHandler, casas, cssClass) {
        var isEditable = typeof editable === "function" ? editable : !!editable;
        var columnDef = {
            title: title,
            field: field,
            hozAlign: "right",
            editor: isEditable ? percentEditor : false,
            editable: isEditable,
            formatter: function (cell) {
                return formatPercentRatio(cell.getValue(), casas || 2);
            },
            cellEdited: saveHandler || null,
            minWidth: 120,
        };
        if (cssClass) columnDef.cssClass = cssClass;
        return columnDef;
    }

    function booleanColumn(title, field, editable, saveHandler) {
        var isEditable = typeof editable === "function" ? editable : !!editable;
        return {
            title: title,
            field: field,
            hozAlign: "center",
            editor: editable
                ? "list"
                : false,
            editorParams: editable
                ? {
                    values: {"true": "Sim", "false": "Não"},
                    clearable: false,
                }
                : null,
            editable: isEditable,
            mutatorEdit: boolMutator,
            formatter: boolFormatter,
            cellEdited: saveHandler || null,
            minWidth: 120,
        };
    }

    function situacaoBadgeFormatter(cell) {
        var row = cell.getRow().getData() || {};
        var label = toText(row.situacao_label) || toText(cell.getValue()) || "-";
        var cor = toText(row.situacao_cor);
        var klass = "precificacao-situacao-badge";
        if (cor) klass += " precificacao-situacao-badge--" + cor;
        return '<span class="' + klass + '">' + label + "</span>";
    }

    function isMateriaPrimaEditable(field) {
        return function (cell) {
            var row = (cell && cell.getRow && cell.getRow().getData()) || {};
            var chave = toText(row.chave).toLowerCase();
            if (field === "valor" && (chave === "acucar_sc" || chave === "acucar_kg")) return false;
            if (field === "frete_mp" && chave === "acucar_sc") return false;
            return true;
        };
    }

    function buildColumns() {
        var columns = {};

        var saveCalculadora = makeSaveHandler("calculadora");
        columns.calculadora = [
            {title: "Origem", field: "origem", minWidth: 140},
            decimalColumn("Volume", "volume", 2, true, saveCalculadora),
            moneyColumn("Preço", "preco", true, saveCalculadora),
            decimalColumn("Prazo", "prazo", 2, true, saveCalculadora),
            moneyColumn("Preço Líquido", "preco_liquido", false, null),
            moneyColumn("Financeiro", "financeiro", false, null),
            moneyColumn("Frete", "frete", true, saveCalculadora),
            moneyColumn("Total", "total", false, null),
        ];

        var saveSimulacao = makeSaveHandler("simulacao");
        columns.simulacao = [
            {title: "Tipo", field: "linha", minWidth: 120},
            percentColumn("Margem Requerida", "margem_requerida", true, saveSimulacao, 2),
            moneyColumn("Frete", "frete", true, saveSimulacao),
            moneyColumnSimulacaoCompra("MP", "mp"),
            moneyColumnSimulacaoCompra("Pr Total", "preco_total"),
        ];

        var saveMateriaPrima = makeSaveHandler("materia_prima");
        columns.materia_prima = [
            {title: "Descrição", field: "descricao", minWidth: 180},
            booleanColumn("Ativo", "ativo", true, saveMateriaPrima),
            moneyColumn("Valor", "valor", isMateriaPrimaEditable("valor"), saveMateriaPrima),
            moneyColumn("Frete MP", "frete_mp", isMateriaPrimaEditable("frete_mp"), saveMateriaPrima, "precificacao-cell-yellow"),
            moneyColumn("Sub-Total", "sub_total", false, null),
            percentColumn("Credito", "credito", true, saveMateriaPrima, 2, "precificacao-cell-yellow"),
            moneyColumn("Custo Ex-Works", "custo_ex_works", false, null),
        ];

        var saveCmv = makeSaveHandler("produto_cmv");
        columns.produto_cmv = [
            {title: "Produto", field: "descricao", minWidth: 110, frozen: true},
            {
                title: "Acucar",
                columns: [
                    percentColumn("Quebra", "acucar_quebra", true, saveCmv, 2, "precificacao-cell-yellow"),
                    decimalColumn("Qtd", "acucar_qtd", 4, false, null),
                    moneyColumn("Valor", "acucar_valor", false, null),
                    moneyColumn("Ex-Works", "acucar_valor_ex_works", false, null),
                ],
            },
            {
                title: "Embalagem Primaria",
                columns: [
                    percentColumn("Quebra", "emb_primaria_quebra", true, saveCmv, 2, "precificacao-cell-yellow"),
                    decimalColumn("Qtd", "emb_primaria_qtd", 4, false, null),
                    moneyColumn("Valor", "emb_primaria_valor", false, null),
                    moneyColumn("Ex-Works", "emb_primaria_valor_ex_works", false, null),
                ],
            },
            {
                title: "Embalagem Secundaria",
                columns: [
                    percentColumn("Quebra", "emb_secundaria_quebra", true, saveCmv, 2, "precificacao-cell-yellow"),
                    decimalColumn("Qtd", "emb_secundaria_qtd", 4, false, null),
                    moneyColumn("Valor", "emb_secundaria_valor", false, null),
                    moneyColumn("Ex-Works", "emb_secundaria_valor_ex_works", false, null),
                ],
            },
            {
                title: "CMV",
                columns: [
                    moneyColumn("CMV", "cmv", false, null),
                    moneyColumn("Ex-Works", "cmv_ex_works", false, null),
                ],
            },
        ];

        var saveDespesas = makeSaveHandler("produto_despesas");
        columns.produto_despesas = [
            {title: "Produto", field: "descricao", minWidth: 110, frozen: true},
            decimalColumn("Prazo Dias", "prazo_dias", 2, false, null, "precificacao-cell-global-source"),
            {
                title: "Financeiro",
                columns: [
                    percentColumn("Taxa", "financeiro_taxa", true, saveDespesas, 2, "precificacao-cell-orange"),
                    moneyColumn("Valor", "financeiro_valor", false, null),
                ],
            },
            {
                title: "Inadimplencia",
                columns: [
                    percentColumn("Taxa", "inadimplencia_taxa", true, saveDespesas, 2, "precificacao-cell-orange"),
                    moneyColumn("Valor", "inadimplencia_valor", false, null),
                ],
            },
            {
                title: "Administração",
                columns: [
                    percentColumn("Taxa", "administracao_taxa", true, saveDespesas, 2, "precificacao-cell-orange"),
                    moneyColumn("Valor", "administracao_valor", false, null),
                ],
            },
            {
                title: "Produção",
                columns: [
                    booleanColumn("Ativo", "producao_ativo", true, saveDespesas),
                    moneyColumn("Valor", "producao_valor", true, saveDespesas, "precificacao-cell-orange"),
                ],
            },
            {
                title: "Log - Frete Rota",
                columns: [
                    moneyColumn("Base", "log_frete_rota", false, null, "precificacao-cell-global-source"),
                    moneyColumn("Valor", "log_frete_rota_valor", false, null),
                ],
            },
            {
                title: "Log Op. Logística",
                columns: [
                    booleanColumn("Ativo", "log_op_logistica_ativo", true, saveDespesas),
                    moneyColumn("Valor", "log_op_logistica_valor", false, null),
                ],
            },
            moneyColumn("Sub-Total", "subtotal", false, null),
        ];

        var saveImpostos = makeSaveHandler("produto_impostos");
        columns.produto_impostos = [
            {title: "Produto", field: "descricao", minWidth: 110, frozen: true},
            booleanColumn("Interno", "interno_ativo", true, saveImpostos),
            {
                title: "Imposto",
                columns: [
                    percentColumn("Aliquota", "imposto_aliquota", true, saveImpostos, 2, "precificacao-cell-yellow"),
                    moneyColumn("Valor", "imposto_valor", false, null),
                    percentColumn("Interno Aliquota", "imposto_interno_aliquota", true, saveImpostos, 2, "precificacao-cell-yellow"),
                    moneyColumn("Interno Valor", "imposto_interno_valor", false, null),
                    moneyColumn("Sub-Total Interno", "subtotal_interno", false, null),
                ],
            },
            {
                title: "Pro Goias",
                columns: [
                    booleanColumn("Ativo", "pro_goias_ativo", true, saveImpostos),
                    percentColumn("Aliquota A", "pro_goias_aliquota_a", true, saveImpostos, 3, "precificacao-cell-alert"),
                    percentColumn("Aliquota B", "pro_goias_aliquota_b", true, saveImpostos, 3, "precificacao-cell-alert"),
                    moneyColumn("Valor A", "pro_goias_valor_a", false, null),
                    moneyColumn("Valor B", "pro_goias_valor_b", false, null),
                    moneyColumn("Sub-Total", "subtotal_pro_goias", false, null),
                ],
            },
            moneyColumn("Total", "total", false, null),
        ];

        var savePrecoVenda = makeSaveHandler("produto_preco_venda");
        columns.produto_preco_venda = [
            {title: "Produto", field: "descricao", minWidth: 110, frozen: true},
            moneyColumn("PV Bruto", "pv_bruto", true, savePrecoVenda),
            percentColumn("CMV Estimado", "cmv_estimado", false, null, 2),
            booleanColumn("Interno", "interno_ativo", true, savePrecoVenda),
            {
                title: "Comissao",
                columns: [
                    percentColumn("Aliquota", "comissao_aliquota", true, savePrecoVenda, 2, "precificacao-cell-orange"),
                    moneyColumn("Valor", "comissao_valor", false, null),
                ],
            },
            {
                title: "Contrato",
                columns: [
                    percentColumn("Aliquota", "contrato_aliquota", true, savePrecoVenda, 2),
                    moneyColumn("Valor", "contrato_valor", false, null),
                ],
            },
            moneyColumn("Sub-Total", "subtotal", false, null),
        ];

        columns.lucro = [
            moneyColumn("Lucro", "lucro_valor", false, null),
            {
                title: "%",
                field: "lucro_percentual",
                hozAlign: "right",
                formatter: function (cell) {
                    return formatPercentRatio(cell.getValue());
                },
                minWidth: 120,
            },
            {
                title: "Situação",
                field: "situacao_label",
                formatter: situacaoBadgeFormatter,
                hozAlign: "center",
                minWidth: 160,
            },
        ];

        return columns;
    }

    Object.keys(DATA_IDS).forEach(function (key) {
        dataByKey[key] = parseJsonScript(DATA_IDS[key]);
    });

    var columnsByKey = buildColumns();
    var baseOptions = {
        layout: "fitDataStretch",
        placeholder: "Sem registros.",
        responsiveLayout: false,
        height: "auto",
        freezeUX: {
            disableGroupedLeafMenus: true,
            enableGroupMenus: false,
        },
    };

    Object.keys(TARGET_IDS).forEach(function (key) {
        if (!document.querySelector(TARGET_IDS[key])) return;
        tables[key] = createTable(TARGET_IDS[key], {
            data: dataByKey[key],
            columns: columnsByKey[key] || [],
            ...baseOptions,
        });
    });

    if (Array.isArray(dataByKey.produto_despesas)) {
        syncDespesasGlobaisFromRows(dataByKey.produto_despesas);
    }
    if (hasDespesasGlobaisControls()) {
        despesasGlobaisEls.prazoDias.addEventListener("change", saveDespesasGlobais);
        despesasGlobaisEls.prazoDias.addEventListener("blur", saveDespesasGlobais);
        despesasGlobaisEls.cifAtivo.addEventListener("change", function () {
            applyDespesasControlEnabledState();
            saveDespesasGlobais();
        });
        despesasGlobaisEls.cifManualAtivo.addEventListener("change", function () {
            applyDespesasControlEnabledState();
            saveDespesasGlobais();
        });
        despesasGlobaisEls.cifRota.addEventListener("change", saveDespesasGlobais);
        despesasGlobaisEls.cifManualValor.addEventListener("change", saveDespesasGlobais);
        despesasGlobaisEls.cifRota.addEventListener("blur", saveDespesasGlobais);
        despesasGlobaisEls.cifManualValor.addEventListener("blur", saveDespesasGlobais);
    }
})();
