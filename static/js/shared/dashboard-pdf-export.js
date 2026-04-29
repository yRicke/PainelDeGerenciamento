(function () {
    var configEl = document.getElementById("dashboard-pdf-config");
    if (!configEl) return;

    var endpoint = String(configEl.getAttribute("data-endpoint") || "").trim();
    if (!endpoint) return;

    var sectionSelector = String(configEl.getAttribute("data-section-selector") || "#sec-dashboard").trim();
    var kpiScopeSelector = String(configEl.getAttribute("data-kpi-scope-selector") || sectionSelector).trim();
    var chartScopeSelector = String(configEl.getAttribute("data-chart-scope-selector") || sectionSelector).trim();
    var titleFallback = String(configEl.getAttribute("data-title") || "").trim();
    var detailsFallback = String(configEl.getAttribute("data-details") || "").trim();
    var buttonLabel = String(configEl.getAttribute("data-button-label") || "Baixar PDF do Dashboard").trim();
    var dashboardSlug = String(configEl.getAttribute("data-dashboard-slug") || "").trim();
    if (!dashboardSlug) {
        var endpointParts = endpoint.replace(/\/+$/, "").split("/");
        if (endpointParts.length) dashboardSlug = String(endpointParts[endpointParts.length - 1] || "").trim();
    }

    var dashboardSection = document.querySelector(sectionSelector);
    if (!dashboardSection) return;

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).replace(/\s+/g, " ").trim();
    }

    function parseJsonScript(id, fallback) {
        var element = document.getElementById(id);
        if (!element) return fallback;
        try {
            return JSON.parse(element.textContent || "");
        } catch (_err) {
            return fallback;
        }
    }

    function humanizeId(raw) {
        var text = toText(raw)
            .replace(/[_-]+/g, " ")
            .replace(/\s+/g, " ")
            .trim();
        text = text.replace(/^(kpi|dashboard)\s+/i, "");
        return text || "Indicador";
    }

    function getCsrfToken() {
        var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input && input.value) return String(input.value);
        var parts = document.cookie ? document.cookie.split(";") : [];
        for (var i = 0; i < parts.length; i += 1) {
            var cookie = parts[i].trim();
            if (cookie.indexOf("csrftoken=") === 0) {
                return decodeURIComponent(cookie.substring("csrftoken=".length));
            }
        }
        return "";
    }

    function getTitle() {
        if (titleFallback) return titleFallback;
        var heading = dashboardSection.querySelector("h2, h1");
        if (heading) return toText(heading.textContent) || "Dashboard";
        return "Dashboard";
    }

    function findMetricLabel(node) {
        if (!node) return "";
        var nodeId = toText(node.id);
        if (nodeId) {
            var forLabel = document.querySelector('label[for="' + nodeId + '"]');
            if (forLabel) {
                var labelByFor = toText(forLabel.textContent);
                if (labelByFor) return labelByFor;
            }
        }

        var previous = node.previousElementSibling;
        if (previous) {
            var previousText = toText(previous.textContent);
            if (previousText && previousText.length <= 80) return previousText;
        }

        var card = node.closest("article, .dashboard-kpi-card, .kpi-card, .dashboard-card, .cargas-kpi-card, .setor-row");
        if (card) {
            var heading = card.querySelector("h3, h4, dt, .dashboard-total-label, .setor-label");
            if (heading) {
                var headingText = toText(heading.textContent);
                if (headingText) return headingText;
            }
        }

        return humanizeId(nodeId);
    }

    function resolveScopes(selector, fallbackElement) {
        var scopes = [];
        var raw = String(selector || "").trim();
        if (raw) {
            var found = document.querySelectorAll(raw);
            for (var i = 0; i < found.length; i += 1) scopes.push(found[i]);
        }
        if (!scopes.length && fallbackElement) scopes.push(fallbackElement);
        return scopes;
    }

    function collectKpis() {
        var scopes = resolveScopes(kpiScopeSelector, dashboardSection);
        var elements = [];

        scopes.forEach(function (scope) {
            if (!scope) return;
            var candidates = scope.querySelectorAll(
                '[id], .dashboard-total-value, .dashboard-percent strong, .kpi-line strong, .setor-valor, .setor-percentual'
            );
            for (var i = 0; i < candidates.length; i += 1) {
                elements.push(candidates[i]);
            }
        });

        var seenNodes = new Set();
        var seenLines = new Set();
        var kpis = [];

        elements.forEach(function (node) {
            if (!node || seenNodes.has(node)) return;
            seenNodes.add(node);
            if (node.closest(".dashboard-pdf-actions")) return;
            if (node.closest("form")) return;
            if (node.closest(".apexcharts-canvas")) return;
            if (node.children && node.children.length > 0 && node.tagName !== "STRONG") return;

            var value = toText(node.textContent);
            if (!value || value.length > 90) return;
            if (!/[0-9]/.test(value) && !/(R\$|%|sim|nao|não|ok|alerta|ativo|inativo)/i.test(value)) return;

            var label = findMetricLabel(node);
            if (!label) return;
            var lineKey = label + "||" + value;
            if (seenLines.has(lineKey)) return;
            seenLines.add(lineKey);

            kpis.push({
                label: label,
                value: value,
            });
        });

        return kpis.slice(0, 40);
    }

    function findChartTitle(container) {
        if (!container) return "Grafico";
        var card = container.closest(".dashboard-chart-card, .chart-card, article, section, .dashboard-header, .dashboard-vendas-header");
        if (card) {
            var heading = card.querySelector("h3, h2, h4");
            if (heading) {
                var headingText = toText(heading.textContent);
                if (headingText) return headingText;
            }
        }
        var containerId = toText(container.id);
        return humanizeId(containerId || "grafico");
    }

    function svgToDataUri(svgEl) {
        if (!svgEl) return "";
        var clone = svgEl.cloneNode(true);
        var serialized = "";
        try {
            serialized = new XMLSerializer().serializeToString(clone);
        } catch (_erro) {
            return "";
        }
        if (!serialized) return "";
        if (serialized.indexOf("xmlns=") < 0) {
            serialized = serialized.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"');
        }
        return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(serialized);
    }

    function collectCharts() {
        var scopes = resolveScopes(chartScopeSelector, dashboardSection);
        var containers = [];
        scopes.forEach(function (scope) {
            if (!scope) return;
            var candidates = scope.querySelectorAll(
                '[id*="chart"], [id*="grafico"], [id*="grafico"], .apexcharts-canvas'
            );
            for (var i = 0; i < candidates.length; i += 1) {
                containers.push(candidates[i]);
            }
        });

        var seen = new Set();
        var charts = [];
        containers.forEach(function (container, index) {
            if (!container) return;
            if (container.classList && container.classList.contains("apexcharts-canvas")) {
                container = container.parentElement || container;
            }
            var key = toText(container.id) || ("chart-" + index);
            if (seen.has(key)) return;
            seen.add(key);

            var imgUri = "";
            var svg = container.querySelector("svg");
            if (svg) imgUri = svgToDataUri(svg);

            if (!imgUri) {
                var canvas = container.querySelector("canvas");
                if (canvas && typeof canvas.toDataURL === "function") {
                    try {
                        imgUri = canvas.toDataURL("image/png");
                    } catch (_erroCanvas) {
                        imgUri = "";
                    }
                }
            }

            if (!imgUri) return;
            charts.push({
                title: findChartTitle(container),
                img_uri: imgUri,
            });
        });

        return charts.slice(0, 30);
    }

    function collectFilters() {
        var lines = [];
        var seen = new Set();

        var externalCards = document.querySelectorAll("#sec-filtros .module-filter-card");
        externalCards.forEach(function (card) {
            var titleEl = card.querySelector("h3");
            var title = toText(titleEl ? titleEl.textContent : "");
            var chips = card.querySelectorAll(".module-filter-chip.is-active");
            if (!chips.length) return;
            var values = [];
            chips.forEach(function (chip) {
                var value = toText(chip.textContent);
                if (value) values.push(value);
            });
            if (!values.length) return;
            var line = "Filtro Externo - " + (title || "Filtro") + ": " + values.join(", ");
            if (seen.has(line)) return;
            seen.add(line);
            lines.push(line);
        });

        var headerFilters = document.querySelectorAll(
            ".tabulator .tabulator-header-filter input, .tabulator .tabulator-header-filter select"
        );
        headerFilters.forEach(function (field) {
            var value = toText(field.value);
            if (!value) return;
            var col = field.closest(".tabulator-col");
            var colTitleEl = col ? col.querySelector(".tabulator-col-title") : null;
            var colTitle = toText(colTitleEl ? colTitleEl.textContent : "");
            var line = "Filtro Tabela - " + (colTitle || "Coluna") + ": " + value;
            if (seen.has(line)) return;
            seen.add(line);
            lines.push(line);
        });

        var dashboardChecks = dashboardSection.querySelectorAll('input[type="checkbox"][id]');
        dashboardChecks.forEach(function (checkbox) {
            var id = toText(checkbox.id);
            if (!id) return;
            var labelEl = document.querySelector('label[for="' + id + '"]');
            var label = toText(labelEl ? labelEl.textContent : humanizeId(id));
            var line = "Painel - " + label + ": " + (checkbox.checked ? "Sim" : "Nao");
            if (seen.has(line)) return;
            seen.add(line);
            lines.push(line);
        });

        return lines.length ? lines : ["Nenhum filtro ativo."];
    }

    function collectDetails(kpis, charts, filters) {
        if (detailsFallback) return detailsFallback;
        return [
            "Indicadores capturados: " + String(Array.isArray(kpis) ? kpis.length : 0),
            "Graficos capturados: " + String(Array.isArray(charts) ? charts.length : 0),
            "Filtros ativos: " + String(Array.isArray(filters) ? filters.length : 0),
        ].join(" | ");
    }

    function findByIdText(id) {
        if (!id) return "";
        var element = document.getElementById(id);
        return toText(element ? element.textContent : "");
    }

    function parsePercentNumber(value) {
        var text = toText(value);
        if (!text) return 0;
        var normalized = text.replace(/\s+/g, "").replace("%", "").replace(/\./g, "").replace(",", ".");
        var parsed = Number(normalized);
        if (!isFinite(parsed)) return 0;
        if (parsed < 0) return 0;
        if (parsed > 100) return 100;
        return Math.round(parsed * 100) / 100;
    }

    function collectTofuModulePayload() {
        var cardsMap = [
            {
                titulo: "Atrasados",
                tone: "atrasados",
                percentualId: "dashboard-atrasados-percentual",
                lines: [
                    {label: "Total", id: "dashboard-atrasados-total"},
                    {label: "Parados", id: "dashboard-atrasados-parados"},
                    {label: "Em andamento", id: "dashboard-atrasados-em-andamento"},
                ],
            },
            {
                titulo: "Alertas",
                tone: "alertas",
                percentualId: "dashboard-alertas-percentual",
                lines: [
                    {label: "Total", id: "dashboard-alertas-total"},
                    {label: "Semana atual", id: "dashboard-alertas-semana-atual"},
                    {label: "Proxima semana", id: "dashboard-alertas-proxima-semana"},
                ],
            },
            {
                titulo: "Concluidos",
                tone: "concluidos",
                percentualId: "dashboard-concluidos-percentual",
                lines: [
                    {label: "Total", id: "dashboard-concluidos-total"},
                    {label: "No prazo", id: "dashboard-concluidos-no-prazo"},
                    {label: "Fora do prazo", id: "dashboard-concluidos-fora-do-prazo"},
                ],
            },
            {
                titulo: "A Fazer",
                tone: "a-fazer",
                percentualId: "dashboard-a-fazer-percentual",
                lines: [
                    {label: "Total", id: "dashboard-a-fazer-total"},
                    {label: "Parados", id: "dashboard-a-fazer-parados"},
                    {label: "Em andamento", id: "dashboard-a-fazer-em-andamento"},
                ],
            },
        ];

        var cards = [];
        cardsMap.forEach(function (card) {
            var linhas = [];
            card.lines.forEach(function (line) {
                var value = findByIdText(line.id);
                if (!value) return;
                linhas.push({
                    label: line.label,
                    value: value,
                });
            });

            cards.push({
                titulo: card.titulo,
                percentual: findByIdText(card.percentualId) || "0,0%",
                tone: card.tone,
                linhas: linhas,
            });
        });

        return {
            total_atividades: findByIdText("dashboard-total-atividades") || "0",
            cards: cards,
        };
    }

    function collectSetoresRows(list) {
        return list.map(function (item) {
            return {
                label: item.label,
                valor: findByIdText(item.valorId) || "R$ 0,00",
                percentual: findByIdText(item.percentualId) || "0%",
                percentual_num: parsePercentNumber(findByIdText(item.percentualId)),
                tone: item.tone,
            };
        });
    }

    function collectControleMargemModulePayload() {
        var cardsPrincipais = [
            {titulo: "Pedido", id: "dashboard-pedido", tone: "pedido"},
            {titulo: "CMV", id: "dashboard-cmv", tone: "cmv"},
            {titulo: "Lucro", id: "dashboard-lucro", tone: "lucro"},
            {titulo: "Margem", id: "dashboard-margem", tone: "margem"},
        ].map(function (item) {
            return {
                titulo: item.titulo,
                valor: findByIdText(item.id) || (item.tone === "margem" ? "0,00%" : "R$ 0,00"),
                tone: item.tone,
            };
        });

        var setores = collectSetoresRows([
            {label: "Vendas", valorId: "dashboard-setor-vendas-valor", percentualId: "dashboard-setor-vendas-percentual", tone: "vendas"},
            {label: "Producao", valorId: "dashboard-setor-producao-valor", percentualId: "dashboard-setor-producao-percentual", tone: "producao"},
            {label: "Logistica", valorId: "dashboard-setor-logistica-valor", percentualId: "dashboard-setor-logistica-percentual", tone: "logistica"},
            {label: "Administracao", valorId: "dashboard-setor-administracao-valor", percentualId: "dashboard-setor-administracao-percentual", tone: "administracao"},
            {label: "Financeiro", valorId: "dashboard-setor-financeiro-valor", percentualId: "dashboard-setor-financeiro-percentual", tone: "financeiro"},
        ]);

        var logistica = collectSetoresRows([
            {label: "Oper. Logistico", valorId: "dashboard-setor-operador-valor", percentualId: "dashboard-setor-operador-percentual", tone: "operador"},
            {label: "Frete Dist.", valorId: "dashboard-setor-frete-valor", percentualId: "dashboard-setor-frete-percentual", tone: "frete"},
        ]);

        var lucroLiquidoEl = document.getElementById("dashboard-lucro-liquido");
        var margemLiquidaEl = document.getElementById("dashboard-margem-liquida");

        function toneBySignal(element) {
            if (!element || !element.classList) return "padrao";
            if (element.classList.contains("is-negative")) return "negativo";
            if (element.classList.contains("is-positive")) return "positivo";
            return "padrao";
        }

        var resumoCards = [
            {titulo: "Total Setores", valor: findByIdText("dashboard-total-setores") || "R$ 0,00", tone: "total"},
            {
                titulo: "Lucro Liquido",
                valor: findByIdText("dashboard-lucro-liquido") || "R$ 0,00",
                tone: toneBySignal(lucroLiquidoEl),
            },
            {
                titulo: "Margem Liquida",
                valor: findByIdText("dashboard-margem-liquida") || "0,00%",
                tone: toneBySignal(margemLiquidaEl),
            },
        ];

        return {
            cards_principais: cardsPrincipais,
            setores: setores,
            logistica: logistica,
            resumo_cards: resumoCards,
        };
    }

    function parseAngleFromTransform(value) {
        var text = toText(value);
        if (!text) return -90;
        var match = text.match(/rotate\((-?[0-9]+(?:\.[0-9]+)?)deg\)/i);
        if (!match) return -90;
        var parsed = Number(match[1]);
        if (!isFinite(parsed)) return -90;
        return Math.max(-90, Math.min(90, parsed));
    }

    function getPointerAngle(id) {
        if (!id) return -90;
        var element = document.getElementById(id);
        if (!element) return -90;
        return parseAngleFromTransform(element.style ? element.style.transform : "");
    }

    function collectProducaoModulePayload() {
        var cards = [
            {sufixo: "30x1", titulo: "Producao 30x1", total: false},
            {sufixo: "15x2", titulo: "Producao 15x2", total: false},
            {sufixo: "6x5", titulo: "Producao 6x5", total: false},
            {sufixo: "total", titulo: "Producao TOTAL", total: true},
        ];

        return {
            reloginhos: cards.map(function (item) {
                var cardEl = document.querySelector('.reloginho-card[data-reloginho="' + item.sufixo + '"]');
                var tituloEl = cardEl ? cardEl.querySelector("h3") : null;
                return {
                    sufixo: item.sufixo,
                    titulo: toText(tituloEl ? tituloEl.textContent : item.titulo) || item.titulo,
                    meta_acum: findByIdText("meta-acum-" + item.sufixo) || "0",
                    real: findByIdText("real-" + item.sufixo) || "0",
                    percentual: findByIdText("pct-" + item.sufixo) || "0,00%",
                    meta_angulo: getPointerAngle("ponteiro-meta-" + item.sufixo),
                    real_angulo: getPointerAngle("ponteiro-real-" + item.sufixo),
                    meta80_angulo: item.total ? getPointerAngle("ponteiro-meta80-total") : null,
                };
            }),
        };
    }

    function collectDashboardGeralModulePayload() {
        return parseJsonScript("dashboard-geral-pdf-payload-data", null);
    }

    function collectModulePayload() {
        if (dashboardSlug === "administrativo_tofu_lista_de_atividades") {
            return collectTofuModulePayload();
        }
        if (dashboardSlug === "comercial_controle_de_margem") {
            return collectControleMargemModulePayload();
        }
        if (dashboardSlug === "operacional_producao") {
            return collectProducaoModulePayload();
        }
        if (dashboardSlug === "dashboard_geral") {
            return collectDashboardGeralModulePayload();
        }
        return null;
    }

    function ensureActionsContainer() {
        var existing = dashboardSection.querySelector(".dashboard-pdf-actions");
        if (existing) return existing;
        var container = document.createElement("div");
        container.className = "dashboard-pdf-actions";
        dashboardSection.appendChild(container);
        return container;
    }

    function ensureExportButton(container) {
        var button = container.querySelector(".dashboard-pdf-export-btn");
        if (button) return button;
        button = document.createElement("button");
        button.type = "button";
        button.className = "btn-light dashboard-pdf-export-btn";
        button.textContent = buttonLabel || "Baixar PDF do Dashboard";
        container.appendChild(button);
        return button;
    }

    function ensureForm() {
        var form = document.getElementById("dashboard-pdf-generic-form");
        if (form) return form;

        form = document.createElement("form");
        form.id = "dashboard-pdf-generic-form";
        form.method = "post";
        form.action = endpoint;
        form.hidden = true;

        var csrfInput = document.createElement("input");
        csrfInput.type = "hidden";
        csrfInput.name = "csrfmiddlewaretoken";
        csrfInput.value = getCsrfToken();
        form.appendChild(csrfInput);

        var payloadInput = document.createElement("input");
        payloadInput.type = "hidden";
        payloadInput.name = "payload_json";
        payloadInput.id = "dashboard-pdf-generic-payload";
        payloadInput.value = "";
        form.appendChild(payloadInput);

        document.body.appendChild(form);
        return form;
    }

    var actionContainer = ensureActionsContainer();
    var exportButton = ensureExportButton(actionContainer);
    var form = ensureForm();
    var payloadInputEl = form.querySelector("#dashboard-pdf-generic-payload");
    if (!payloadInputEl) return;

    var exportando = false;
    exportButton.addEventListener("click", function () {
        if (exportando) return;
        exportando = true;
        var textoOriginal = exportButton.textContent || "Baixar PDF do Dashboard";
        exportButton.disabled = true;
        exportButton.textContent = "Preparando PDF...";

        var kpis = collectKpis();
        var charts = collectCharts();
        var filters = collectFilters();

        var payload = {
            title: getTitle(),
            kpis: kpis,
            charts: charts,
            filters: filters,
            details: collectDetails(kpis, charts, filters),
            module_payload: collectModulePayload(),
        };

        try {
            payloadInputEl.value = JSON.stringify(payload);
        } catch (_erro) {
            payloadInputEl.value = "{}";
        }

        form.submit();
        window.setTimeout(function () {
            exportButton.disabled = false;
            exportButton.textContent = textoOriginal;
            exportando = false;
        }, 1200);
    });
})();
