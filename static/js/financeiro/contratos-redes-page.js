(function () {
    var dataElement = document.getElementById("contratos-redes-tabulator-data");
    var parceirosElement = document.getElementById("contratos-redes-parceiros-data");
    if (!dataElement || !parceirosElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var parceiros = JSON.parse(parceirosElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var parceiroValues = {"": "Sem parceiro"};
    var parceirosById = {};
    var statusContratoValues = {
        Ativo: "Ativo",
        Inativo: "Inativo",
    };

    function toFieldValue(value) {
        if (value === null || value === undefined) return "";
        return String(value);
    }

    function parseRatioInput(texto) {
        var t = String(texto || "").trim();
        if (!t) return 0;
        var temPercentual = t.indexOf("%") >= 0;
        t = t.replace(/%/g, "").replace(/\s/g, "");
        if (t.indexOf(",") >= 0) {
            t = t.replace(/\./g, "").replace(",", ".");
        } else if ((t.match(/\./g) || []).length > 1 && t.toLowerCase().indexOf("e") < 0) {
            t = t.replace(/\./g, "");
        }
        var numero = Number(t);
        if (!Number.isFinite(numero)) return 0;
        if (temPercentual) return numero / 100;
        if (Math.abs(numero) > 1) return numero / 100;
        if (Math.abs(numero) >= 0.1) return numero / 100;
        return numero;
    }

    function formatPercentFromRatio(value) {
        var ratio = typeof value === "number" ? value : parseRatioInput(value);
        if (!Number.isFinite(ratio)) ratio = 0;
        return (ratio * 100).toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }) + "%";
    }

    function onlyDigits(value) {
        return String(value || "").replace(/\D/g, "");
    }

    function formatPercentFromDigits(digitsRaw) {
        var digits = onlyDigits(digitsRaw).replace(/^0+(?=\d)/, "");
        if (!digits) digits = "0";
        var padded = digits.padStart(3, "0");
        var intPart = padded.slice(0, -2);
        var decPart = padded.slice(-2);
        var intNumber = Number(intPart || "0");
        if (!Number.isFinite(intNumber)) intNumber = 0;
        return intNumber.toLocaleString("pt-BR") + "," + decPart + "%";
    }

    function ratioToDigits(ratio) {
        var numero = Number(ratio);
        if (!Number.isFinite(numero)) numero = 0;
        return String(Math.round(Math.abs(numero) * 10000));
    }

    function toPercentMaskValue(value) {
        if (typeof value === "number") {
            return formatPercentFromDigits(ratioToDigits(value));
        }
        var texto = String(value || "").trim();
        if (!texto) return "0,00%";
        if (texto.indexOf("%") >= 0) {
            return formatPercentFromDigits(onlyDigits(texto));
        }
        return formatPercentFromDigits(ratioToDigits(parseRatioInput(texto)));
    }

    function setCaretAtEnd(input) {
        if (!input || typeof input.setSelectionRange !== "function") return;
        var pos = String(input.value || "").length;
        input.setSelectionRange(pos, pos);
    }

    function handlePercentBackspaceAtEnd(input, event) {
        if (!input || !event || event.key !== "Backspace") return false;
        if (input.selectionStart !== input.selectionEnd) return false;
        var pos = Number(input.selectionStart || 0);
        var length = String(input.value || "").length;
        if (pos !== length) return false;

        var digits = onlyDigits(input.value);
        var nextDigits = digits.slice(0, -1);
        input.value = formatPercentFromDigits(nextDigits);
        setCaretAtEnd(input);
        event.preventDefault();
        return true;
    }

    function attachPercentMaskHandlers(input) {
        if (!input) return;
        input.addEventListener("keydown", function (event) {
            handlePercentBackspaceAtEnd(input, event);
        });
        input.addEventListener("input", function () {
            input.value = formatPercentFromDigits(onlyDigits(input.value));
            setCaretAtEnd(input);
        });
        input.addEventListener("blur", function () {
            input.value = toPercentMaskValue(input.value);
        });
    }

    function applyPercentualPixMask(input) {
        if (!input) return;
        input.value = toPercentMaskValue(input.value);
        attachPercentMaskHandlers(input);
    }

    function formatDateBr(value) {
        var t = String(value || "").trim();
        if (!t) return "";
        var matchIso = t.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (matchIso) return matchIso[3] + "/" + matchIso[2] + "/" + matchIso[1];

        var matchBr = t.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        if (matchBr) return t;

        var parsed = new Date(t);
        if (isNaN(parsed.getTime())) return t;
        var dia = String(parsed.getDate()).padStart(2, "0");
        var mes = String(parsed.getMonth() + 1).padStart(2, "0");
        var ano = String(parsed.getFullYear());
        return dia + "/" + mes + "/" + ano;
    }

    function formatTextoOuVazio(valor) {
        var texto = String(valor || "").trim();
        return texto || "(Vazio)";
    }

    function ordenarTexto(a, b) {
        return String(a.label || "").localeCompare(String(b.label || ""), "pt-BR", {
            sensitivity: "base",
            numeric: true,
        });
    }

    function ensureFilterColumns(section) {
        if (!section) return null;

        var left = section.querySelector('[data-module-filter-column="left"]')
            || section.querySelector("#contratos-redes-filtros-coluna-esquerda");
        var right = section.querySelector('[data-module-filter-column="right"]')
            || section.querySelector("#contratos-redes-filtros-coluna-direita");

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
            left.id = "contratos-redes-filtros-coluna-esquerda";
            wrapper.appendChild(left);
        }

        if (!right) {
            right = document.createElement("div");
            right.className = "module-filter-column";
            right.setAttribute("data-module-filter-column", "right");
            right.id = "contratos-redes-filtros-coluna-direita";
            wrapper.appendChild(right);
        }

        return {left: left, right: right};
    }

    function criarDefinicoesFiltrosContratos() {
        return [
            {
                key: "descricao_acordos",
                label: "Descricao dos Acordos",
                singleSelect: false,
                extractValue: function (rowData) {
                    return rowData ? rowData.descricao_acordos : "";
                },
                formatValue: formatTextoOuVazio,
                sortOptions: ordenarTexto,
            },
        ];
    }

    function configurarFiltrosExternos(tabelaRef, registros, secFiltros) {
        if (!tabelaRef || !secFiltros || !window.ModuleFilterCore) return null;

        secFiltros.dataset.moduleFiltersManual = "true";
        var placeholderFiltros = secFiltros.querySelector(".module-filters-placeholder");
        if (placeholderFiltros) placeholderFiltros.remove();

        var filtroColumns = ensureFilterColumns(secFiltros);
        if (!filtroColumns || !filtroColumns.left || !filtroColumns.right) return null;

        var filtrosExternos = window.ModuleFilterCore.create({
            data: registros,
            definitions: criarDefinicoesFiltrosContratos(),
            leftColumn: filtroColumns.left,
            rightColumn: filtroColumns.right,
            onChange: function () {
                if (typeof tabelaRef.refreshFilter === "function") {
                    tabelaRef.refreshFilter();
                }
            },
        });

        tabelaRef.addFilter(function (rowData) {
            return filtrosExternos.matchesRecord(rowData);
        });

        return {secFiltros: secFiltros, filtrosExternos: filtrosExternos};
    }

    function registrarAcaoLimparFiltros(tabelaRef, secFiltros, filtrosExternos) {
        if (!tabelaRef || !secFiltros || !filtrosExternos) return;

        function limparTodosFiltros() {
            if (typeof filtrosExternos.clearAllFilters === "function") {
                filtrosExternos.clearAllFilters();
            }
            if (typeof tabelaRef.clearHeaderFilter === "function") {
                tabelaRef.clearHeaderFilter();
            }
            if (typeof tabelaRef.refreshFilter === "function") {
                tabelaRef.refreshFilter();
            }
        }

        var limparFiltrosSidebarBtn = secFiltros.querySelector(".module-filters-clear-all");
        var limparFiltrosToolbarBtn = document.querySelector(".module-shell-main-toolbar .module-shell-clear-filters");
        if (limparFiltrosSidebarBtn) {
            limparFiltrosSidebarBtn.addEventListener("click", limparTodosFiltros);
        }
        if (limparFiltrosToolbarBtn) {
            limparFiltrosToolbarBtn.addEventListener("click", limparTodosFiltros);
        }
    }

    function percentualPixEditor(cell, onRendered, success, cancel) {
        var input = document.createElement("input");
        input.type = "text";
        input.setAttribute("inputmode", "numeric");
        input.value = toPercentMaskValue(cell.getValue());

        onRendered(function () {
            input.focus();
            input.select();
        });

        attachPercentMaskHandlers(input);

        input.addEventListener("blur", function () {
            success(toPercentMaskValue(input.value));
        });

        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                success(toPercentMaskValue(input.value));
                return;
            }
            if (event.key === "Escape") cancel();
        });

        return input;
    }

    parceiros.forEach(function (parceiro) {
        var parceiroId = String(parceiro.id);
        var codigo = parceiro && parceiro.codigo ? String(parceiro.codigo) : "";
        var nome = parceiro && parceiro.nome ? String(parceiro.nome) : "";
        var label = (codigo ? codigo + " - " : "") + nome;
        parceiroValues[parceiroId] = label || "Sem parceiro";
        parceirosById[parceiroId] = {
            codigo: codigo,
            nome: nome,
        };
    });

    document.querySelectorAll("[data-percentual-pix]").forEach(applyPercentualPixMask);

    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                codigo_registro: toFieldValue(row.codigo_registro),
                numero_contrato: toFieldValue(row.numero_contrato),
                data_inicio: toFieldValue(row.data_inicio),
                data_encerramento: toFieldValue(row.data_encerramento),
                parceiro_id: toFieldValue(row.parceiro_id),
                descricao_acordos: toFieldValue(row.descricao_acordos),
                valor_acordo: toPercentMaskValue(row.valor_acordo),
                status_contrato: toFieldValue(row.status_contrato || "Ativo"),
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir contrato de rede?",
    });

    var tabela = window.TabulatorDefaults.create("#contratos-redes-tabulator", {
        data: data,
        columns: [
            {title: "Codigo Registro", field: "codigo_registro", editor: "input", headerFilter: false},
            {title: "Numero do Contrato", field: "numero_contrato", editor: "input", headerFilter: false},
            {
                title: "Data Inicio",
                field: "data_inicio",
                editor: "date",
                headerFilter: false,
                formatter: function (cell) {
                    return formatDateBr(cell.getValue());
                },
            },
            {
                title: "Data Encerramento",
                field: "data_encerramento",
                editor: "date",
                headerFilter: false,
                formatter: function (cell) {
                    return formatDateBr(cell.getValue());
                },
            },
            {
                title: "Parceiro",
                field: "parceiro_id",
                editor: "list",
                headerFilter: false,
                editorParams: {
                    values: parceiroValues,
                    clearable: true,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var codigo = row.parceiro_codigo ? String(row.parceiro_codigo) : "";
                    var nome = row.parceiro_nome ? String(row.parceiro_nome) : "";
                    if (!codigo && !nome) return "Sem parceiro";
                    return (codigo ? codigo + " - " : "") + nome;
                },
                cellEdited: function (cell) {
                    var row = cell.getRow().getData();
                    var parceiroId = String(row.parceiro_id || "");
                    var parceiro = parceirosById[parceiroId] || {codigo: "", nome: ""};
                    cell.getRow().update({
                        parceiro_codigo: parceiro.codigo,
                        parceiro_nome: parceiro.nome,
                    });
                },
            },
            {title: "Codigo Parceiro", field: "parceiro_codigo", headerFilter: false},
            {title: "Nome Parceiro", field: "parceiro_nome", headerFilter: false},
            {
                title: "Descricao dos Acordos",
                field: "descricao_acordos",
                editor: "textarea",
                headerFilter: "input",
            },
            {
                title: "Valor do Acordo (%)",
                field: "valor_acordo",
                editor: percentualPixEditor,
                hozAlign: "right",
                headerFilter: false,
                formatter: function (cell) {
                    return formatPercentFromRatio(cell.getValue());
                },
                mutatorEdit: function (value) {
                    return parseRatioInput(value);
                },
            },
            {
                title: "Status do Contrato",
                field: "status_contrato",
                editor: "list",
                headerFilter: false,
                editorParams: {
                    values: statusContratoValues,
                    clearable: false,
                },
                mutatorEdit: function (value) {
                    var texto = String(value || "").trim().toLowerCase();
                    return texto === "inativo" ? "Inativo" : "Ativo";
                },
            },
            colunaAcoes,
        ],
    });

    var secFiltros = document.getElementById("sec-filtros");
    if (secFiltros) {
        secFiltros.dataset.moduleFiltersAuto = "off";
    }

    var filtrosConfig = configurarFiltrosExternos(tabela, data, secFiltros);
    if (filtrosConfig) {
        registrarAcaoLimparFiltros(tabela, filtrosConfig.secFiltros, filtrosConfig.filtrosExternos);
    }
})();
