(function () {
    var dataElement = document.getElementById("dre-tabulator-data");
    var tableTarget = document.getElementById("dre-tabulator");
    var secFiltros = document.getElementById("sec-filtros");
    var filtrosColunaEsquerda = document.getElementById("dre-filtros-coluna-esquerda");
    var filtrosColunaDireita = document.getElementById("dre-filtros-coluna-direita");
    var saveStatusEl = document.getElementById("dre-save-status");
    var kpiValorTotalEl = document.getElementById("dre-kpi-valor-total");
    var analiticoTableHost = document.getElementById("dre-analitico-table");

    if (!dataElement || !tableTarget || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var tabela = null;
    var externalFilters = null;
    var internalUpdate = false;
    var seqByRowId = {};
    var analyticalExpandedGroups = {
        receitas: false,
        devolucoes: false,
        cmv: false,
        despesas: false,
    };
    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});
    var analyticalMonths = [
        {number: 1, label: "Janeiro"},
        {number: 2, label: "Fevereiro"},
        {number: 3, label: "Marco"},
        {number: 4, label: "Abril"},
        {number: 5, label: "Maio"},
        {number: 6, label: "Junho"},
        {number: 7, label: "Julho"},
        {number: 8, label: "Agosto"},
        {number: 9, label: "Setembro"},
        {number: 10, label: "Outubro"},
        {number: 11, label: "Novembro"},
        {number: 12, label: "Dezembro"},
    ];
    var analyticalSummaryRows = [
        {label: "Receita Bruta", summaryKey: "receita-bruta", badge: "+", bucketKey: "receitaBruta"},
        {label: "Despesas", summaryKey: "despesas", badge: "-", bucketKey: "despesas"},
        {label: "Devolucoes", summaryKey: "devolucoes", badge: "-", bucketKey: "devolucoes"},
        {label: "Faturamento Liquido", summaryKey: "faturamento-liquido", badge: "=", bucketKey: "faturamentoLiquido"},
        {label: "Lucro Bruto", summaryKey: "lucro-bruto", badge: "=", bucketKey: "lucroBruto"},
        {label: "Lucro Liquido", summaryKey: "lucro-liquido", badge: "=", bucketKey: "lucroLiquido"},
    ];

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

    function normalizeText(value) {
        var text = toText(value).toLowerCase();
        if (!text) return "";
        if (typeof text.normalize === "function") {
            text = text.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        }
        return text;
    }

    function escapeHtml(value) {
        return toText(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
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
        saveStatusEl.classList.remove("dre-save-status--ok", "dre-save-status--error", "dre-save-status--progress");
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function formatDateIsoToBr(dateIso) {
        var text = toText(dateIso);
        if (!text) return "";
        var parts = text.split("-");
        if (parts.length !== 3) return text;
        return parts[2] + "/" + parts[1] + "/" + parts[0];
    }

    function normalizarReceitaDespesa(item) {
        var text = normalizeText(item && item.receita_despesa);
        if (text === "receita") return "Receita";
        if (text === "despesa") return "Despesa";
        var valor = toNumber(item && item.valor_liquido);
        if (valor > 0) return "Receita";
        if (valor < 0) return "Despesa";
        return "";
    }

    function getVisibleRowsData() {
        if (!tabela) return data.slice();

        if (typeof tabela.getRows === "function") {
            var activeRows = tabela.getRows("active") || [];
            if (activeRows.length) {
                return activeRows.map(function (row) { return row.getData(); });
            }
        }

        if (typeof tabela.getData === "function") {
            var currentData = tabela.getData() || [];
            if (currentData.length) return currentData;
        }

        return data.slice();
    }

    function atualizarDashboard(rows) {
        var linhas = Array.isArray(rows) ? rows : [];
        var totalLiquido = 0;

        linhas.forEach(function (item) {
            var valorLiquido = toNumber(item && item.valor_liquido);
            totalLiquido += valorLiquido;
        });

        if (kpiValorTotalEl) kpiValorTotalEl.textContent = formatMoney(totalLiquido);
    }

    function createAnalyticalMonthTotals() {
        return {receita: 0, despesa: 0};
    }

    function createAnalyticalBucket() {
        var bucket = {};
        analyticalMonths.forEach(function (month) {
            bucket[month.number] = createAnalyticalMonthTotals();
        });
        return bucket;
    }

    function getAnalyticalMonthTotals(bucket, monthNumber) {
        if (!bucket || !bucket[monthNumber]) return createAnalyticalMonthTotals();
        return bucket[monthNumber];
    }

    function addAnalyticalValue(target, monthNumber, kind, value) {
        if (!target || !target[monthNumber] || !kind) return;
        target[monthNumber][kind] += Math.abs(toNumber(value));
    }

    function getCenterLabel(rowData) {
        return toText(rowData && rowData.descricao_centro_resultado) || "Sem centro de resultado";
    }

    function getOperationLabel(rowData) {
        return (
            toText(rowData && rowData.descricao_tipo_operacao) ||
            toText(rowData && rowData.descricao_natureza) ||
            "Sem tipo de operacao"
        );
    }

    function isDevolucaoVendaText(value) {
        var text = normalizeText(value);
        if (!text) return false;
        return text.indexOf("devolucao") >= 0 && text.indexOf("vend") >= 0;
    }

    function isDevolucaoVendaMovimento(rowData) {
        return isDevolucaoVendaText(rowData && rowData.dfc_tipo_movimento);
    }

    function isCmvCenterLabel(value) {
        return normalizeText(value) === "cmv";
    }

    function createAnalyticalStructure() {
        return {
            receitaBruta: createAnalyticalBucket(),
            devolucoes: createAnalyticalBucket(),
            devolucoesCenters: {},
            faturamentoLiquido: createAnalyticalBucket(),
            lucroBruto: createAnalyticalBucket(),
            lucroLiquido: createAnalyticalBucket(),
            despesas: createAnalyticalBucket(),
            despesasCenters: {},
            centers: {},
        };
    }

    function ensureCenterNodeInMap(centerMap, centerLabel) {
        if (!centerMap[centerLabel]) {
            centerMap[centerLabel] = {
                label: centerLabel,
                totals: createAnalyticalBucket(),
                operations: {},
            };
        }
        return centerMap[centerLabel];
    }

    function ensureCenterNode(structure, centerLabel) {
        return ensureCenterNodeInMap(structure.centers, centerLabel);
    }

    function ensureOperationNode(centerNode, operationLabel) {
        if (!centerNode.operations[operationLabel]) {
            centerNode.operations[operationLabel] = {
                label: operationLabel,
                totals: createAnalyticalBucket(),
            };
        }
        return centerNode.operations[operationLabel];
    }

    function findCenterNodeByLabel(structure, expectedLabel) {
        var expected = normalizeText(expectedLabel);
        var centerLabels = Object.keys((structure && structure.centers) || {});
        for (var i = 0; i < centerLabels.length; i += 1) {
            var centerLabel = centerLabels[i];
            if (normalizeText(centerLabel) === expected) {
                return structure.centers[centerLabel];
            }
        }
        return null;
    }

    // Derived summary rows are calculated from the already aggregated monthly buckets.
    function calculateAnalyticalSummaryRows(structure) {
        var cmvCenter = findCenterNodeByLabel(structure, "CMV");

        analyticalMonths.forEach(function (month) {
            var monthNumber = month.number;
            var receitaBrutaTotals = getAnalyticalMonthTotals(structure.receitaBruta, monthNumber);
            var devolucoesTotals = getAnalyticalMonthTotals(structure.devolucoes, monthNumber);
            var faturamentoLiquidoTotals = getAnalyticalMonthTotals(structure.faturamentoLiquido, monthNumber);
            var lucroBrutoTotals = getAnalyticalMonthTotals(structure.lucroBruto, monthNumber);
            var lucroLiquidoTotals = getAnalyticalMonthTotals(structure.lucroLiquido, monthNumber);
            var despesasTotals = getAnalyticalMonthTotals(structure.despesas, monthNumber);
            var cmvTotals = cmvCenter ? getAnalyticalMonthTotals(cmvCenter.totals, monthNumber) : createAnalyticalMonthTotals();

            faturamentoLiquidoTotals.receita = receitaBrutaTotals.receita;
            faturamentoLiquidoTotals.despesa = devolucoesTotals.despesa;

            var faturamentoLiquidoSaldo =
                toNumber(faturamentoLiquidoTotals.receita) -
                toNumber(faturamentoLiquidoTotals.despesa);

            lucroBrutoTotals.receita = faturamentoLiquidoSaldo;
            lucroBrutoTotals.despesa = toNumber(cmvTotals.despesa);

            var lucroBrutoSaldo =
                toNumber(lucroBrutoTotals.receita) -
                toNumber(lucroBrutoTotals.despesa);

            lucroLiquidoTotals.receita = lucroBrutoSaldo;
            lucroLiquidoTotals.despesa = toNumber(despesasTotals.despesa);
        });
    }

    function buildAnalyticalSummaryRow(structure, config) {
        return {
            label: config.label,
            kind: "summary",
            summaryKey: config.summaryKey,
            badge: config.badge,
            totals: structure[config.bucketKey],
        };
    }

    function buildAnalyticalSummaryRowsByKeys(structure, summaryKeys) {
        return summaryKeys
            .map(function (summaryKey) {
                return analyticalSummaryRows.find(function (config) {
                    return config.summaryKey === summaryKey;
                }) || null;
            })
            .filter(Boolean)
            .map(function (config) {
                return buildAnalyticalSummaryRow(structure, config);
            });
    }

    function getAnalyticalSummaryRowByKey(structure, summaryKey) {
        var rows = buildAnalyticalSummaryRowsByKeys(structure, [summaryKey]);
        return rows.length ? rows[0] : null;
    }

    function getAnalyticalDirectionBadge(rowTotals) {
        var receita = sumAnalyticalBucketByKind(rowTotals, "receita");
        var despesa = sumAnalyticalBucketByKind(rowTotals, "despesa");

        if (receita > 0 && despesa <= 0) return "+";
        if (despesa > 0 && receita <= 0) return "-";
        if (receita > despesa) return "+";
        if (despesa > 0) return "-";
        return "";
    }

    function buildAnalyticalCenterRows(centerNode) {
        if (!centerNode) return [];

        var rows = [{
            label: centerNode.label,
            kind: "center",
            badge: getAnalyticalDirectionBadge(centerNode.totals),
            indentLevel: 0,
            totals: centerNode.totals,
        }];

        Object.keys(centerNode.operations)
            .sort(compareLabels)
            .forEach(function (operationLabel) {
                rows.push({
                    label: centerNode.operations[operationLabel].label,
                    kind: "operation",
                    badge: getAnalyticalDirectionBadge(centerNode.operations[operationLabel].totals),
                    indentLevel: 1,
                    totals: centerNode.operations[operationLabel].totals,
                });
            });

        return rows;
    }

    function projectAnalyticalBucketByKind(rowTotals, kind) {
        var projectedTotals = createAnalyticalBucket();

        analyticalMonths.forEach(function (month) {
            projectedTotals[month.number][kind] = toNumber(getAnalyticalMonthTotals(rowTotals, month.number)[kind]);
        });

        return projectedTotals;
    }

    function hasAnalyticalBucketValues(rowTotals, kind) {
        return sumAnalyticalBucketByKind(rowTotals, kind) !== 0;
    }

    function buildAnalyticalCenterRowsByKind(centerNode, kind, labelSuffix, options) {
        if (!centerNode) return [];
        var includeOperations = Boolean(options && options.includeOperations);
        var kindBadge = kind === "receita" ? "+" : "-";

        var centerTotals = projectAnalyticalBucketByKind(centerNode.totals, kind);
        if (!hasAnalyticalBucketValues(centerTotals, kind)) return [];

        var rows = [{
            label: centerNode.label + " " + labelSuffix,
            kind: "center",
            badge: kindBadge,
            indentLevel: 1,
            totals: centerTotals,
        }];

        if (!includeOperations) return rows;

        Object.keys(centerNode.operations)
            .sort(compareLabels)
            .forEach(function (operationLabel) {
                var operationTotals = projectAnalyticalBucketByKind(centerNode.operations[operationLabel].totals, kind);
                if (!hasAnalyticalBucketValues(operationTotals, kind)) return;

                rows.push({
                    label: centerNode.operations[operationLabel].label,
                    kind: "operation",
                    indentLevel: 2,
                    totals: operationTotals,
                });
            });

        return rows;
    }

    function buildAnalyticalStructure(rows) {
        var structure = createAnalyticalStructure();

        (Array.isArray(rows) ? rows : []).forEach(function (rowData) {
            var monthNumber = Number(rowData && rowData.mes_baixa);
            if (!monthNumber || monthNumber < 1 || monthNumber > 12) return;

            var kindText = normalizeText(normalizarReceitaDespesa(rowData));
            var analyticalKind = kindText === "receita" ? "receita" : (kindText === "despesa" ? "despesa" : "");
            if (!analyticalKind) return;

            var value = toNumber(rowData && rowData.valor_liquido);
            if (!value) return;
            var centerLabel = getCenterLabel(rowData);
            var isDevolucao = isDevolucaoVendaMovimento(rowData);
            var isCmvCenter = isCmvCenterLabel(centerLabel);
            var shouldIncludeInMainCenters = !(isCmvCenter && isDevolucao);

            if (shouldIncludeInMainCenters) {
                var centerNode = ensureCenterNode(structure, centerLabel);
                var operationNode = ensureOperationNode(centerNode, getOperationLabel(rowData));

                addAnalyticalValue(operationNode.totals, monthNumber, analyticalKind, value);
                addAnalyticalValue(centerNode.totals, monthNumber, analyticalKind, value);
            }

            if (analyticalKind === "receita") addAnalyticalValue(structure.receitaBruta, monthNumber, analyticalKind, value);
            if (analyticalKind === "despesa" && !isDevolucao && !isCmvCenter) {
                addAnalyticalValue(structure.despesas, monthNumber, analyticalKind, value);

                var despesaCenterNode = ensureCenterNodeInMap(structure.despesasCenters, centerLabel);
                var despesaOperationNode = ensureOperationNode(despesaCenterNode, getOperationLabel(rowData));

                addAnalyticalValue(despesaCenterNode.totals, monthNumber, "despesa", value);
                addAnalyticalValue(despesaOperationNode.totals, monthNumber, "despesa", value);
            }
            if (isDevolucao) {
                addAnalyticalValue(structure.devolucoes, monthNumber, "despesa", value);

                var devolucaoCenterNode = ensureCenterNodeInMap(structure.devolucoesCenters, centerLabel);
                var devolucaoOperationNode = ensureOperationNode(devolucaoCenterNode, getOperationLabel(rowData));

                addAnalyticalValue(devolucaoCenterNode.totals, monthNumber, "despesa", value);
                addAnalyticalValue(devolucaoOperationNode.totals, monthNumber, "despesa", value);
            }
        });

        calculateAnalyticalSummaryRows(structure);
        return structure;
    }

    function compareLabels(a, b) {
        return toText(a).localeCompare(toText(b), "pt-BR", {sensitivity: "base"});
    }

    function isAnalyticalGroupExpanded(groupKey) {
        return Boolean(analyticalExpandedGroups[groupKey]);
    }

    function buildAnalyticalExpandableRows(parentRow, groupKey, childRows) {
        if (!parentRow) return [];

        var detailRows = Array.isArray(childRows) ? childRows.filter(Boolean) : [];
        var hasChildren = detailRows.length > 0;

        if (hasChildren) {
            parentRow.expandable = true;
            parentRow.expanded = isAnalyticalGroupExpanded(groupKey);
            parentRow.groupKey = groupKey;
        }

        var rows = [parentRow];
        if (hasChildren && parentRow.expanded) {
            rows = rows.concat(detailRows);
        }

        return rows;
    }

    function buildAnalyticalSectionRowsByKind(centerMap, kind, labelSuffix, options) {
        var rows = [];

        Object.keys(centerMap || {})
            .sort(compareLabels)
            .forEach(function (centerLabel) {
                rows = rows.concat(buildAnalyticalCenterRowsByKind(centerMap[centerLabel], kind, labelSuffix, options));
            });

        return rows;
    }

    function buildAnalyticalRows(structure) {
        var sortedCenterLabels = Object.keys(structure.centers).sort(compareLabels);
        var cmvCenter = findCenterNodeByLabel(structure, "CMV");
        var centerOnlyOptions = {includeOperations: false};
        var nonCmvCenters = sortedCenterLabels
            .map(function (centerLabel) {
                return structure.centers[centerLabel];
            })
            .filter(function (centerNode) {
                return normalizeText(centerNode.label) !== "cmv";
            });
        var rows = [];
        var receitaDetailRows = [];
        var devolucaoDetailRows = buildAnalyticalSectionRowsByKind(
            structure.devolucoesCenters,
            "despesa",
            "Devolucao",
            centerOnlyOptions
        );
        var despesaDetailRows = buildAnalyticalSectionRowsByKind(
            structure.despesasCenters,
            "despesa",
            "Despesa",
            centerOnlyOptions
        );
        var cmvRows = buildAnalyticalCenterRows(cmvCenter);
        var cmvParentRow = cmvRows.length ? cmvRows[0] : null;
        var cmvDetailRows = cmvRows.slice(1);

        nonCmvCenters.forEach(function (centerNode) {
            receitaDetailRows = receitaDetailRows.concat(
                buildAnalyticalCenterRowsByKind(centerNode, "receita", "Receita", centerOnlyOptions)
            );
        });

        rows = rows.concat(
            buildAnalyticalExpandableRows(
                getAnalyticalSummaryRowByKey(structure, "receita-bruta"),
                "receitas",
                receitaDetailRows
            )
        );
        rows = rows.concat(
            buildAnalyticalExpandableRows(
                getAnalyticalSummaryRowByKey(structure, "devolucoes"),
                "devolucoes",
                devolucaoDetailRows
            )
        );
        rows = rows.concat(buildAnalyticalSummaryRowsByKeys(structure, ["faturamento-liquido"]));
        rows = rows.concat(buildAnalyticalExpandableRows(cmvParentRow, "cmv", cmvDetailRows));
        rows = rows.concat(buildAnalyticalSummaryRowsByKeys(structure, ["lucro-bruto"]));
        rows = rows.concat(
            buildAnalyticalExpandableRows(
                getAnalyticalSummaryRowByKey(structure, "despesas"),
                "despesas",
                despesaDetailRows
            )
        );
        rows = rows.concat(buildAnalyticalSummaryRowsByKeys(structure, ["lucro-liquido"]));

        return rows;
    }

    function sumAnalyticalBucketByKind(rowTotals, kind) {
        var total = 0;

        analyticalMonths.forEach(function (month) {
            total += toNumber(getAnalyticalMonthTotals(rowTotals, month.number)[kind]);
        });

        return total;
    }

    function getAnalyticalRowSummary(rowTotals) {
        var receita = sumAnalyticalBucketByKind(rowTotals, "receita");
        var despesa = sumAnalyticalBucketByKind(rowTotals, "despesa");

        return {
            receita: receita,
            despesa: despesa,
            saldo: receita - despesa,
        };
    }

    function getAnalyticalNetValue(totals) {
        var monthTotals = totals || createAnalyticalMonthTotals();
        return toNumber(monthTotals.receita) - toNumber(monthTotals.despesa);
    }

    function appendAnalyticalValueCell(html, value) {
        html.push('<td class="dre-analitico-cell dre-analitico-cell--metric">' + formatMoney(value) + "</td>");
    }

    function appendAnalyticalMonthCells(html, rowTotals) {
        analyticalMonths.forEach(function (month) {
            var monthTotals = getAnalyticalMonthTotals(rowTotals, month.number);
            appendAnalyticalValueCell(html, getAnalyticalNetValue(monthTotals));
        });
    }

    function appendAnalyticalTotalCells(html, rowSummary) {
        appendAnalyticalValueCell(html, rowSummary.saldo);
    }

    function buildAnalyticalTreePrefix(indentLevel) {
        if (!indentLevel || indentLevel < 1) return "";

        var parts = [];
        for (var i = 0; i < indentLevel; i += 1) {
            parts.push("-");
        }
        return parts.join(" ");
    }

    function buildAnalyticalMetricColgroup(html) {
        var metricColumnCount = analyticalMonths.length + 1;

        for (var i = 0; i < metricColumnCount; i += 1) {
            html.push('<col class="dre-analitico-col dre-analitico-col--metric">');
        }
    }

    function buildAnalyticalHeadRows(html) {
        html.push(
            '<thead>',
            '<tr>',
            '<th class="dre-analitico-cell dre-analitico-cell--description dre-analitico-cell--description-head">Descricao</th>'
        );

        analyticalMonths.forEach(function (month) {
            html.push('<th class="dre-analitico-cell dre-analitico-cell--month">' + escapeHtml(month.label) + "</th>");
        });
        html.push('<th class="dre-analitico-cell dre-analitico-cell--month">Total</th>');
        html.push("</tr></thead><tbody>");
    }

    function renderAnalyticalEmptyState() {
        if (!analiticoTableHost) return;
        analiticoTableHost.innerHTML =
            '<div class="dre-analitico-empty"><strong>Nenhum dado encontrado</strong><span>Os filtros atuais nao retornaram registros para montar a tabela analitica.</span></div>';
    }

    function bindAnalyticalExpanders() {
        if (!analiticoTableHost) return;

        analiticoTableHost.querySelectorAll("[data-analitico-group]").forEach(function (button) {
            button.addEventListener("click", function () {
                var groupKey = button.getAttribute("data-analitico-group");
                if (!groupKey) return;
                analyticalExpandedGroups[groupKey] = !isAnalyticalGroupExpanded(groupKey);
                atualizarTabelaAnalitica();
            });
        });
    }

    function renderAnalyticalTable(rows) {
        if (!analiticoTableHost) return;
        if (!rows.length) {
            renderAnalyticalEmptyState();
            return;
        }

        var html = [
            '<div class="dre-analitico-table-scroll">',
            '<table class="dre-analitico-table">',
            '<colgroup>',
            '<col class="dre-analitico-col dre-analitico-col--description">',
        ];
        buildAnalyticalMetricColgroup(html);
        html.push("</colgroup>");
        buildAnalyticalHeadRows(html);

        rows.forEach(function (row) {
            var rowClass = "dre-analitico-row--operation";
            if (row.kind === "summary") rowClass = "dre-analitico-row--summary";
            if (row.kind === "center") rowClass = "dre-analitico-row--center";
            if (row.summaryKey) rowClass += " dre-analitico-row--" + row.summaryKey;
            if (row.expandable) rowClass += " dre-analitico-row--expandable";

            html.push('<tr class="' + rowClass + '">');
            var toggleHtml = "";
            if (row.expandable) {
                toggleHtml =
                    '<button type="button" class="dre-analitico-toggle" data-analitico-group="' + escapeHtml(row.groupKey) + '" aria-expanded="' +
                    (row.expanded ? "true" : "false") + '" aria-label="' +
                    (row.expanded ? "Recolher detalhes de " : "Expandir detalhes de ") + escapeHtml(row.label) + '">' +
                    '<span class="dre-analitico-toggle-icon">' + (row.expanded ? "&#9662;" : "&#9656;") + "</span>" +
                    "</button>";
            }
            var badgeHtml = row.badge
                ? '<span class="dre-analitico-badge">' + escapeHtml(row.badge) + "</span>"
                : "";
            var treePrefixHtml = row.indentLevel
                ? '<span class="dre-analitico-tree-prefix">' + escapeHtml(buildAnalyticalTreePrefix(row.indentLevel)) + "</span>"
                : "";
            var labelClass = "dre-analitico-label dre-analitico-label--" + row.kind;
            html.push(
                '<td class="dre-analitico-cell dre-analitico-cell--description"><div class="' + labelClass + '">' +
                badgeHtml +
                treePrefixHtml +
                '<span class="dre-analitico-label-text">' + escapeHtml(row.label) + "</span>" +
                toggleHtml +
                "</div></td>"
            );

            appendAnalyticalMonthCells(html, row.totals);
            var rowSummary = getAnalyticalRowSummary(row.totals);
            appendAnalyticalTotalCells(html, rowSummary);
            html.push("</tr>");
        });

        html.push("</tbody></table></div>");
        analiticoTableHost.innerHTML = html.join("");
        bindAnalyticalExpanders();
    }

    function getAnalyticalFilteredRows() {
        return data.filter(function (rowData) {
            return matchesGlobalFilters(rowData);
        });
    }

    function atualizarTabelaAnalitica() {
        var structure = buildAnalyticalStructure(getAnalyticalFilteredRows());
        renderAnalyticalTable(buildAnalyticalRows(structure));
    }

    function createFilterDefinitions() {
        return [
            {
                key: "ano_baixa",
                label: "Ano",
                singleSelect: true,
                extractValue: function (rowData) {
                    return rowData ? rowData.ano_baixa : "";
                },
            },
            {
                key: "nome_fantasia_empresa",
                label: "Nome Fantasia",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.nome_fantasia_empresa : "";
                },
            },
        ];
    }

    function setupExternalFilters() {
        if (!window.ModuleFilterCore || !secFiltros || !filtrosColunaEsquerda || !filtrosColunaDireita) {
            externalFilters = null;
            if (tabela && typeof tabela.refreshFilter === "function") tabela.refreshFilter();
            atualizarTabelaAnalitica();
            return;
        }

        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholder = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholder) placeholder.remove();

        externalFilters = window.ModuleFilterCore.create({
            data: data.slice(),
            definitions: createFilterDefinitions(),
            leftColumn: filtrosColunaEsquerda,
            rightColumn: filtrosColunaDireita,
            onChange: function () {
                if (tabela && typeof tabela.refreshFilter === "function") tabela.refreshFilter();
                atualizarTabelaAnalitica();
            },
        });

        if (tabela && typeof tabela.refreshFilter === "function") tabela.refreshFilter();
        atualizarTabelaAnalitica();
    }

    function matchesGlobalFilters(rowData) {
        if (externalFilters && typeof externalFilters.matchesRecord === "function") {
            return externalFilters.matchesRecord(rowData);
        }
        return true;
    }

    function refreshFiltersAndDashboard() {
        setupExternalFilters();
        atualizarDashboard(getVisibleRowsData());
    }

    function bindClearFilterButtons() {
        function clearAll() {
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

        var buttons = document.querySelectorAll(".module-filters-clear-all, .module-shell-clear-filters");
        buttons.forEach(function (button) {
            button.addEventListener("click", clearAll);
        });
    }

    function buildPayloadFromRow(rowData) {
        var valorPagar = toText(rowData.valor_a_pagar) ? String(toNumber(rowData.valor_a_pagar).toFixed(2)) : "";
        return {
            valor_a_pagar: valorPagar,
            plano_contas_tipo_movimento: toText(rowData.plano_contas_tipo_movimento),
            tipo_dre: toText(rowData.tipo_dre),
        };
    }

    function rollbackField(row, rowData, field, oldValue) {
        if (!row || !rowData) return;
        var payload = Object.assign({}, rowData);
        payload[field] = oldValue;
        internalUpdate = true;
        Promise.resolve(row.update(payload)).finally(function () {
            internalUpdate = false;
        });
    }

    function saveEditedRow(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;
        var rowData = row.getData() || {};
        if (!rowData.editar_url) return;

        var field = typeof cell.getField === "function" ? cell.getField() : "";
        var oldValue = typeof cell.getOldValue === "function" ? cell.getOldValue() : null;
        var rowId = rowData.id;
        var currentSeq = Number(seqByRowId[rowId] || 0) + 1;
        seqByRowId[rowId] = currentSeq;

        var formData = new FormData();
        appendCsrfToken(formData);
        var payload = buildPayloadFromRow(rowData);
        Object.keys(payload).forEach(function (key) {
            formData.append(key, payload[key]);
        });

        setSaveStatus("Salvando alteracao...", "dre-save-status--progress");
        fetch(rowData.editar_url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (seqByRowId[rowId] !== currentSeq) return;
                if (!result.ok || !result.body || result.body.ok === false || !result.body.registro) {
                    rollbackField(row, rowData, field, oldValue);
                    setSaveStatus(
                        (result.body && result.body.message) ? result.body.message : "Falha ao salvar.",
                        "dre-save-status--error"
                    );
                    return;
                }

                internalUpdate = true;
                Promise.resolve(row.update(result.body.registro))
                    .then(function () {
                        var updated = row.getData() || {};
                        var index = data.findIndex(function (item) { return Number(item.id) === Number(updated.id); });
                        if (index >= 0) data[index] = updated;
                        refreshFiltersAndDashboard();
                        setSaveStatus("Salvo automaticamente.", "dre-save-status--ok");
                    })
                    .catch(function () {
                        rollbackField(row, rowData, field, oldValue);
                        setSaveStatus("Falha ao aplicar retorno no front.", "dre-save-status--error");
                    })
                    .finally(function () {
                        internalUpdate = false;
                    });
            })
            .catch(function () {
                if (seqByRowId[rowId] !== currentSeq) return;
                rollbackField(row, rowData, field, oldValue);
                setSaveStatus("Falha ao salvar. Alteracao revertida.", "dre-save-status--error");
            });
    }

    function initTable() {
        var createTable = (window.TabulatorDefaults && typeof window.TabulatorDefaults.create === "function")
            ? window.TabulatorDefaults.create
            : function (selector, options) { return new window.Tabulator(selector, options); };

        tabela = createTable("#dre-tabulator", {
            data: data,
            layout: "fitDataStretch",
            index: "id",
            height: "560px",
            reactiveData: false,
            headerFilterLiveFilterDelay: 300,
            columns: [
                {title: "ID", field: "id", hozAlign: "right", width: 75},
                {title: "Data da Baixa", field: "data_baixa", sorter: "string", headerFilter: "input", minWidth: 130},
                {title: "Dt. Vencimento", field: "data_vencimento", sorter: "string", headerFilter: "input", minWidth: 130},
                {title: "Nome Fantasia (Empresa)", field: "nome_fantasia_empresa", headerFilter: "input", minWidth: 220},
                {title: "Receita/Despesa", field: "receita_despesa", headerFilter: "input", minWidth: 140},
                {title: "Parceiro", field: "parceiro", headerFilter: "input", minWidth: 110},
                {title: "Nome Parceiro (Parceiro)", field: "nome_parceiro", headerFilter: "input", minWidth: 220},
                {title: "Nro Nota", field: "numero_nota", headerFilter: "input", minWidth: 120},
                {title: "Natureza", field: "natureza", headerFilter: "input", minWidth: 110},
                {title: "Descricao (Natureza)", field: "descricao_natureza", headerFilter: "input", minWidth: 220},
                {
                    title: "Valor Liquido",
                    field: "valor_liquido",
                    hozAlign: "right",
                    headerFilter: "input",
                    minWidth: 140,
                    formatter: function (cell) { return formatMoney(cell.getValue()); },
                },
                {
                    title: "Valor a Pagar",
                    field: "valor_a_pagar",
                    hozAlign: "right",
                    headerFilter: "input",
                    minWidth: 140,
                    editor: "input",
                    formatter: function (cell) {
                        var value = cell.getValue();
                        if (toText(value) === "") return "";
                        return formatMoney(value);
                    },
                },
                {title: "Descricao (Tipo de Operacao)", field: "descricao_tipo_operacao", headerFilter: "input", minWidth: 220},
                {title: "Descricao (Centro de Resultado)", field: "descricao_centro_resultado", headerFilter: "input", minWidth: 230},
                {
                    title: "Plano Contas.Tipo Movimento",
                    field: "plano_contas_tipo_movimento",
                    headerFilter: "input",
                    editor: "input",
                    minWidth: 200,
                },
                {
                    title: "Tipo DRE",
                    field: "tipo_dre",
                    headerFilter: "input",
                    editor: "input",
                    minWidth: 140,
                },
            ],
            rowFormatter: function (row) {
                var rowData = row.getData() || {};
                var editable = !!rowData.editar_url;
                var rowEl = row.getElement();
                if (!rowEl) return;
                if (editable) rowEl.classList.add("dre-row-editable");
                else rowEl.classList.remove("dre-row-editable");
            },
            dataFiltered: function (_filters, filteredRows) {
                var linhas = (filteredRows || []).map(function (row) { return row.getData(); });
                atualizarDashboard(linhas);
            },
            cellEdited: function (cell) {
                if (internalUpdate) return;
                var field = toText(cell.getField());
                if (field !== "valor_a_pagar" && field !== "plano_contas_tipo_movimento" && field !== "tipo_dre") {
                    return;
                }
                saveEditedRow(cell);
            },
            initialFilter: [],
        });

        if (typeof tabela.setFilter === "function") {
            tabela.setFilter(function (rowData) {
                return matchesGlobalFilters(rowData);
            });
        }
    }

    data.forEach(function (item) {
        item.data_baixa = item.data_baixa || formatDateIsoToBr(item.data_baixa_iso);
        item.data_vencimento = item.data_vencimento || formatDateIsoToBr(item.data_vencimento_iso);
    });

    initTable();
    bindClearFilterButtons();
    refreshFiltersAndDashboard();
})();
