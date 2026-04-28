(function () {
    var dataElement = document.getElementById("plano-cargos-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.TabulatorDefaults) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var cadastroForm = document.querySelector("#sec-cadastro form");
    var dashboardEls = {
        totalComSalario: document.getElementById("pcs-dashboard-total-salario-carteira"),
        mediaSalario: document.getElementById("pcs-dashboard-media-salario"),
        maxSalario: document.getElementById("pcs-dashboard-max-salario"),
        minSalario: document.getElementById("pcs-dashboard-min-salario"),
        desvioSalario: document.getElementById("pcs-dashboard-desvio-salario"),
        totalJr: document.getElementById("pcs-dashboard-total-jr"),
        totalPleno: document.getElementById("pcs-dashboard-total-pleno"),
        totalSenior: document.getElementById("pcs-dashboard-total-senior"),
    };
    var saveStatusEl = document.getElementById("pcs-save-status");
    var seqByRowId = {};
    var internalUpdate = false;

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function parseInteger(value) {
        var texto = toText(value);
        if (!texto) return 0;
        var numero = Number(texto.replace(/\D/g, ""));
        if (!Number.isFinite(numero)) return 0;
        return Math.max(0, Math.trunc(numero));
    }

    function parseDecimal(value) {
        if (value === null || value === undefined) return null;
        if (typeof value === "number") {
            return Number.isFinite(value) ? value : null;
        }
        var texto = toText(value);
        if (!texto) return null;
        texto = texto.replace(/R\$/gi, "").replace(/\s/g, "");
        if (texto.indexOf(",") >= 0) {
            texto = texto.replace(/\./g, "").replace(",", ".");
        } else if ((texto.match(/\./g) || []).length > 1 && texto.toLowerCase().indexOf("e") < 0) {
            texto = texto.replace(/\./g, "");
        }
        var numero = Number(texto);
        return Number.isFinite(numero) ? numero : null;
    }

    function toDecimalForPost(value) {
        var numero = parseDecimal(value);
        if (numero === null) return "";
        return numero.toFixed(2);
    }

    function getCurrencyDigits(value) {
        return toText(value).replace(/\D/g, "");
    }

    function formatCurrencyFromDigits(digits) {
        var texto = toText(digits).replace(/\D/g, "");
        if (!texto) return "";
        var centavos = Number(texto);
        if (!Number.isFinite(centavos)) return "";
        var valor = centavos / 100;
        return "R$ " + valor.toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function setupFormCurrencyMask() {
        var inputs = document.querySelectorAll("#sec-cadastro .js-pcs-currency-input");
        if (!inputs || !inputs.length) return;

        inputs.forEach(function (input) {
            if (!input) return;
            if (getCurrencyDigits(input.value)) {
                input.value = formatCurrencyFromDigits(getCurrencyDigits(input.value));
            }
            if (input.dataset.pcsCurrencyMaskBound === "1") return;
            input.dataset.pcsCurrencyMaskBound = "1";

            input.addEventListener("input", function () {
                var digits = getCurrencyDigits(input.value);
                input.value = digits ? formatCurrencyFromDigits(digits) : "";
            });

            input.addEventListener("blur", function () {
                var digits = getCurrencyDigits(input.value);
                input.value = digits ? formatCurrencyFromDigits(digits) : "";
            });
        });
    }

    function formatDateIsoToBr(value) {
        var texto = toText(value);
        if (!texto) return "";
        var iso = texto.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (!iso) return texto;
        return iso[3] + "/" + iso[2] + "/" + iso[1];
    }

    var formatadorMoeda = new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"});

    function formatCurrencyCell(cell) {
        var numero = parseDecimal(cell.getValue());
        if (numero === null) return "";
        return formatadorMoeda.format(numero);
    }

    function setSaveStatus(text, tone) {
        if (!saveStatusEl) return;
        saveStatusEl.classList.remove("pcs-save-status--ok", "pcs-save-status--error", "pcs-save-status--progress");
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
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

    function ensureFilterColumns(section) {
        if (!section) return null;

        var left = section.querySelector('[data-module-filter-column="left"]')
            || section.querySelector("#plano-cargos-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#plano-cargos-filtros-coluna-direita");
        if (left && right) return {left: left, right: right};

        var wrapper = section.querySelector(".module-filter-columns");
        if (!wrapper) {
            wrapper = document.createElement("div");
            wrapper.className = "module-filter-columns";
            section.appendChild(wrapper);
        }
        if (!left) {
            left = document.createElement("div");
            left.className = "module-filter-column";
            left.id = "plano-cargos-filtros-coluna-esquerda";
            left.setAttribute("data-module-filter-column", "left");
            wrapper.appendChild(left);
        }
        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.id = "plano-cargos-filtros-coluna-direita";
            right.setAttribute("data-module-filter-column", "right");
            wrapper.appendChild(right);
        }
        return {left: left, right: right};
    }

    function formatTextoOuVazio(valor) {
        return toText(valor) || "(Vazio)";
    }

    function ordenarTexto(a, b) {
        return String(a.label || "").localeCompare(String(b.label || ""), "pt-BR", {
            sensitivity: "base",
            numeric: true,
        });
    }

    function definirFiltrosMultiselecao() {
        return [
            {
                key: "genero",
                label: "Genero",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.genero : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "setor",
                label: "Setor",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.setor : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "contato",
                label: "Contato",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.contato : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
            {
                key: "cargo",
                label: "Cargo",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.cargo : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
        ];
    }

    function registrarLimparFiltros(tabela, secFiltros, filtrosExternos) {
        if (!tabela || !secFiltros || !filtrosExternos) return;

        function limparTudo() {
            if (typeof filtrosExternos.clearAllFilters === "function") {
                filtrosExternos.clearAllFilters();
            }
            if (typeof tabela.clearHeaderFilter === "function") {
                tabela.clearHeaderFilter();
            }
            if (typeof tabela.refreshFilter === "function") {
                tabela.refreshFilter();
            }
        }

        var limparSidebar = secFiltros.querySelector(".module-filters-clear-all");
        var limparToolbar = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
        if (limparSidebar) limparSidebar.addEventListener("click", limparTudo);
        if (limparToolbar) limparToolbar.addEventListener("click", limparTudo);
    }

    function determinarFaixa(rowData) {
        var salario = parseDecimal(rowData && rowData.salario_carteira);
        var jr = parseDecimal(rowData && rowData.jr);
        var pleno = parseDecimal(rowData && rowData.pleno);
        var senior = parseDecimal(rowData && rowData.senior);

        if (salario === null) return "";

        var jrAtivo = jr !== null && jr > 0;
        var plenoAtivo = pleno !== null && pleno > 0;
        var seniorAtivo = senior !== null && senior > 0;

        if (seniorAtivo && salario >= senior) return "senior";
        if (jrAtivo && salario <= jr) return "jr";
        if (jrAtivo || seniorAtivo || plenoAtivo) return "pleno";
        return "";
    }

    function aplicarCorFaixaNaLinha(row) {
        if (!row) return;
        var faixa = determinarFaixa(row.getData());
        var cellJr = row.getCell("jr");
        var cellPleno = row.getCell("pleno");
        var cellSenior = row.getCell("senior");
        [cellJr, cellPleno, cellSenior].forEach(function (cell) {
            if (!cell) return;
            var el = cell.getElement();
            if (!el) return;
            el.classList.remove("pcs-faixa-jr", "pcs-faixa-pleno", "pcs-faixa-senior");
        });

        var targetCell = null;
        if (faixa === "jr") targetCell = cellJr;
        if (faixa === "pleno") targetCell = cellPleno;
        if (faixa === "senior") targetCell = cellSenior;
        if (targetCell && targetCell.getElement()) {
            targetCell.getElement().classList.add("pcs-faixa-" + faixa);
        }
    }

    function formatCount(value) {
        var numero = Number(value);
        if (!Number.isFinite(numero)) return "0";
        return String(Math.max(0, Math.trunc(numero)));
    }

    function formatCurrencyOrDefault(value) {
        var numero = Number(value);
        if (!Number.isFinite(numero)) return "R$ 0,00";
        return formatadorMoeda.format(numero);
    }

    function obterRegistrosDashboard(tabela) {
        if (tabela && typeof tabela.getRows === "function") {
            try {
                var rowsAtivos = tabela.getRows("active");
                if (Array.isArray(rowsAtivos) && rowsAtivos.length) {
                    return rowsAtivos.map(function (row) {
                        return row && typeof row.getData === "function" ? row.getData() : null;
                    }).filter(function (item) {
                        return item && typeof item === "object";
                    });
                }
            } catch (error) {
                // Fallback para implementacoes sem suporte ao getRows("active").
            }
        }

        if (tabela && typeof tabela.getData === "function") {
            try {
                var ativos = tabela.getData("active");
                if (Array.isArray(ativos) && ativos.length) return ativos;
            } catch (error) {
                // Fallback para versões/implementações sem suporte ao argumento "active".
            }
            var todos = tabela.getData();
            if (Array.isArray(todos) && todos.length) return todos;
        }
        return Array.isArray(data) ? data : [];
    }

    function calcularDashboardIndicadores(registros) {
        var linhas = Array.isArray(registros) ? registros : [];
        var salarios = [];
        var totalJr = 0;
        var totalPleno = 0;
        var totalSenior = 0;

        linhas.forEach(function (item) {
            var salario = parseDecimal(item && item.salario_carteira);
            if (salario !== null && Math.abs(salario) > 0.000001) {
                salarios.push(salario);
            }

            var faixa = determinarFaixa(item);
            if (faixa === "jr") totalJr += 1;
            if (faixa === "pleno") totalPleno += 1;
            if (faixa === "senior") totalSenior += 1;
        });

        var totalComSalario = salarios.length;
        var media = 0;
        var min = 0;
        var max = 0;
        var desvioPadrao = 0;

        if (totalComSalario > 0) {
            var soma = salarios.reduce(function (acc, valor) {
                return acc + valor;
            }, 0);
            media = soma / totalComSalario;
            min = Math.min.apply(null, salarios);
            max = Math.max.apply(null, salarios);
            var somaQuadrados = salarios.reduce(function (acc, valor) {
                var delta = valor - media;
                return acc + (delta * delta);
            }, 0);
            desvioPadrao = Math.sqrt(somaQuadrados / totalComSalario);
        }

        return {
            totalComSalario: totalComSalario,
            media: media,
            min: min,
            max: max,
            desvioPadrao: desvioPadrao,
            totalJr: totalJr,
            totalPleno: totalPleno,
            totalSenior: totalSenior,
        };
    }

    function atualizarDashboardIndicadores(registros) {
        var indicadores = calcularDashboardIndicadores(registros);

        if (dashboardEls.totalComSalario) dashboardEls.totalComSalario.textContent = formatCount(indicadores.totalComSalario);
        if (dashboardEls.mediaSalario) dashboardEls.mediaSalario.textContent = formatCurrencyOrDefault(indicadores.media);
        if (dashboardEls.minSalario) dashboardEls.minSalario.textContent = formatCurrencyOrDefault(indicadores.min);
        if (dashboardEls.maxSalario) dashboardEls.maxSalario.textContent = formatCurrencyOrDefault(indicadores.max);
        if (dashboardEls.desvioSalario) dashboardEls.desvioSalario.textContent = formatCurrencyOrDefault(indicadores.desvioPadrao);
        if (dashboardEls.totalJr) dashboardEls.totalJr.textContent = formatCount(indicadores.totalJr);
        if (dashboardEls.totalPleno) dashboardEls.totalPleno.textContent = formatCount(indicadores.totalPleno);
        if (dashboardEls.totalSenior) dashboardEls.totalSenior.textContent = formatCount(indicadores.totalSenior);
    }

    function refreshDashboard() {
        if (!tabela) return;
        atualizarDashboardIndicadores(obterRegistrosDashboard(tabela));
    }

    function aplicarCoresCabecalho(tabela) {
        if (!tabela || typeof tabela.getColumn !== "function") return;
        var jrCol = tabela.getColumn("jr");
        var plenoCol = tabela.getColumn("pleno");
        var seniorCol = tabela.getColumn("senior");
        if (jrCol && jrCol.getElement()) jrCol.getElement().classList.add("pcs-header-jr");
        if (plenoCol && plenoCol.getElement()) plenoCol.getElement().classList.add("pcs-header-pleno");
        if (seniorCol && seniorCol.getElement()) seniorCol.getElement().classList.add("pcs-header-senior");
    }

    function payloadFromRow(rowData) {
        return {
            cadastro: String(parseInteger(rowData.cadastro) || ""),
            funcionario: toText(rowData.funcionario),
            contrato: toText(rowData.contrato),
            contato: toText(rowData.contato),
            genero: toText(rowData.genero),
            setor: toText(rowData.setor),
            cargo: toText(rowData.cargo),
            novo_cargo: toText(rowData.novo_cargo),
            data_admissao: toText(rowData.data_admissao_iso),
            salario_carteira: toDecimalForPost(rowData.salario_carteira),
            piso_categoria: toDecimalForPost(rowData.piso_categoria),
            jr: toDecimalForPost(rowData.jr),
            pleno: toDecimalForPost(rowData.pleno),
            senior: toDecimalForPost(rowData.senior),
        };
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

    function salvarLinhaAutomatica(tabela, cell) {
        if (!tabela || !cell) return;
        var row = cell.getRow();
        if (!row) return;
        var rowData = row.getData() || {};
        if (!rowData.editar_url) return;

        var rowId = rowData.id;
        var currentSeq = Number(seqByRowId[rowId] || 0) + 1;
        seqByRowId[rowId] = currentSeq;
        var valorAntigo = typeof cell.getOldValue === "function" ? cell.getOldValue() : null;
        var payload = payloadFromRow(rowData);
        var csrfToken = getCsrfToken();

        setSaveStatus("Salvando alteracao...", "pcs-save-status--progress");

        var formData = new FormData();
        if (csrfToken) {
            formData.append("csrfmiddlewaretoken", csrfToken);
        }
        Object.keys(payload).forEach(function (key) {
            formData.append(key, payload[key]);
        });

        fetch(rowData.editar_url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (seqByRowId[rowId] !== currentSeq) return;

                if (!result.ok || !result.body || result.body.ok === false) {
                    restoreCellValue(cell, valorAntigo);
                    aplicarCorFaixaNaLinha(row);
                    refreshDashboard();
                    setSaveStatus(result.body && result.body.message ? result.body.message : "Falha ao salvar.", "pcs-save-status--error");
                    return;
                }

                if (result.body.registro && typeof row.update === "function") {
                    internalUpdate = true;
                    row.update(result.body.registro);
                    internalUpdate = false;
                }
                aplicarCorFaixaNaLinha(row);
                refreshDashboard();
                setSaveStatus("Salvo automaticamente.", "pcs-save-status--ok");
            })
            .catch(function () {
                if (seqByRowId[rowId] !== currentSeq) return;
                restoreCellValue(cell, valorAntigo);
                aplicarCorFaixaNaLinha(row);
                refreshDashboard();
                setSaveStatus("Falha ao salvar.", "pcs-save-status--error");
            });
    }

    function onCellEdited(cell) {
        if (internalUpdate) return;
        salvarLinhaAutomatica(tabela, cell);
    }

    function salvarNovoRegistroPelaTabela(event) {
        if (!event || !cadastroForm) return;
        event.preventDefault();
        if (!tabela || typeof tabela.addData !== "function") return;

        var url = cadastroForm.getAttribute("action");
        if (!url) return;

        var csrfToken = getCsrfToken();
        var formData = new FormData(cadastroForm);
        if (csrfToken && !formData.get("csrfmiddlewaretoken")) {
            formData.append("csrfmiddlewaretoken", csrfToken);
        }

        setSaveStatus("Criando registro...", "pcs-save-status--progress");

        fetch(url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false || !result.body.registro) {
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao criar registro.",
                        "pcs-save-status--error"
                    );
                    return;
                }

                Promise.resolve(tabela.addData([result.body.registro], true))
                    .then(function () {
                        cadastroForm.reset();
                        setupFormCurrencyMask();
                        refreshDashboard();
                        setSaveStatus("Registro criado e tabela atualizada.", "pcs-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus("Registro criado, mas houve falha ao atualizar a tabela.", "pcs-save-status--error");
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao criar registro.", "pcs-save-status--error");
            });
    }

    function excluirRegistroPelaTabela(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;
        var rowData = row.getData() || {};
        if (!rowData.excluir_url) return;
        if (!window.confirm("Excluir registro?")) return;

        var csrfToken = getCsrfToken();
        var formData = new FormData();
        if (csrfToken) {
            formData.append("csrfmiddlewaretoken", csrfToken);
        }

        setSaveStatus("Excluindo registro...", "pcs-save-status--progress");

        fetch(rowData.excluir_url, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        })
            .then(parseJsonResponse)
            .then(function (result) {
                if (!result.ok || !result.body || result.body.ok === false) {
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao excluir registro.",
                        "pcs-save-status--error"
                    );
                    return;
                }

                Promise.resolve(row.delete())
                    .then(function () {
                        refreshDashboard();
                        setSaveStatus("Registro excluido e tabela atualizada.", "pcs-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus("Registro excluido, mas houve falha ao atualizar a tabela.", "pcs-save-status--error");
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao excluir registro.", "pcs-save-status--error");
            });
    }

    var colunaExcluir = {
        title: "Acoes",
        field: "excluir_url",
        hozAlign: "center",
        headerFilter: false,
        formatter: function (cell) {
            if (!cell.getValue()) return "";
            return '<button class="btn-danger js-pcs-excluir" type="button">Excluir</button>';
        },
        cellClick: function (event, cell) {
            var target = event && event.target;
            var botao = target && target.closest ? target.closest(".js-pcs-excluir") : null;
            if (!botao) return;
            excluirRegistroPelaTabela(cell);
        },
    };

    var tabela = window.TabulatorDefaults.create("#plano-cargos-tabulator", {
        data: data,
        rowFormatter: function (row) {
            aplicarCorFaixaNaLinha(row);
        },
        columns: [
            {
                title: "Cadastro",
                field: "cadastro",
                editor: "number",
                hozAlign: "center",
                editorParams: {min: 1, step: 1},
                cellEdited: onCellEdited,
                mutatorEdit: function (value) {
                    return parseInteger(value);
                },
            },
            {title: "Funcionario", field: "funcionario", editor: "input", cellEdited: onCellEdited},
            {title: "Contrato", field: "contrato", editor: "input", cellEdited: onCellEdited},
            {title: "Contato", field: "contato", editor: "input", cellEdited: onCellEdited},
            {title: "Genero", field: "genero", editor: "input", cellEdited: onCellEdited},
            {title: "Setor", field: "setor", editor: "input", cellEdited: onCellEdited},
            {title: "Cargo", field: "cargo", editor: "input", cellEdited: onCellEdited},
            {title: "Novo Cargo", field: "novo_cargo", editor: "input", cellEdited: onCellEdited},
            {
                title: "Data de Admissao",
                field: "data_admissao_iso",
                editor: "date",
                cellEdited: onCellEdited,
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
            },
            {
                title: "Salario Carteira",
                field: "salario_carteira",
                editor: "input",
                hozAlign: "right",
                cellEdited: onCellEdited,
                formatter: formatCurrencyCell,
                mutatorEdit: function (value) {
                    return parseDecimal(value);
                },
            },
            {
                title: "Piso Categoria",
                field: "piso_categoria",
                editor: "input",
                hozAlign: "right",
                cellEdited: onCellEdited,
                formatter: formatCurrencyCell,
                mutatorEdit: function (value) {
                    return parseDecimal(value);
                },
            },
            {
                title: "JR",
                field: "jr",
                cssClass: "pcs-col-jr",
                editor: "input",
                hozAlign: "right",
                cellEdited: onCellEdited,
                formatter: formatCurrencyCell,
                mutatorEdit: function (value) {
                    return parseDecimal(value);
                },
            },
            {
                title: "Pleno",
                field: "pleno",
                cssClass: "pcs-col-pleno",
                editor: "input",
                hozAlign: "right",
                cellEdited: onCellEdited,
                formatter: formatCurrencyCell,
                mutatorEdit: function (value) {
                    return parseDecimal(value);
                },
            },
            {
                title: "Senior",
                field: "senior",
                cssClass: "pcs-col-senior",
                editor: "input",
                hozAlign: "right",
                cellEdited: onCellEdited,
                formatter: formatCurrencyCell,
                mutatorEdit: function (value) {
                    return parseDecimal(value);
                },
            },
            colunaExcluir,
        ],
    });

    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros && window.ModuleFilterCore) {
        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholder = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholder) placeholder.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (filtroColumns && filtroColumns.left && filtroColumns.right) {
            var filtrosExternos = window.ModuleFilterCore.create({
                data: data,
                definitions: definirFiltrosMultiselecao(),
                leftColumn: filtroColumns.left,
                rightColumn: filtroColumns.right,
                onChange: function () {
                    if (typeof tabela.refreshFilter === "function") {
                        tabela.refreshFilter();
                    }
                    refreshDashboard();
                },
            });

            tabela.addFilter(function (rowData) {
                return filtrosExternos.matchesRecord(rowData);
            });

            registrarLimparFiltros(tabela, secFiltros, filtrosExternos);
        }
    }

    if (tabela && typeof tabela.on === "function") {
        tabela.on("tableBuilt", function () {
            refreshDashboard();
        });
        tabela.on("dataLoaded", function () {
            refreshDashboard();
        });
        tabela.on("renderComplete", function () {
            refreshDashboard();
        });
        tabela.on("dataFiltered", function () {
            refreshDashboard();
        });
        tabela.on("rowAdded", function () {
            refreshDashboard();
        });
        tabela.on("rowDeleted", function () {
            refreshDashboard();
        });
        tabela.on("rowUpdated", function () {
            refreshDashboard();
        });
        tabela.on("dataChanged", function () {
            refreshDashboard();
        });
    }

    aplicarCoresCabecalho(tabela);
    refreshDashboard();
    setSaveStatus("", "");
    setupFormCurrencyMask();

    if (cadastroForm) {
        cadastroForm.addEventListener("submit", salvarNovoRegistroPelaTabela);
    }
})();
