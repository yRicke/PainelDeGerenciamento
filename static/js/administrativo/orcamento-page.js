(function () {
    var submitPost = window.FinanceiroCrudUtils && typeof window.FinanceiroCrudUtils.submitPost === "function"
        ? window.FinanceiroCrudUtils.submitPost
        : null;

    function moneyFormatter(cell) {
        var value = Number(cell.getValue() || 0);
        if (!value) return "R$ -";
        return "R$ " + value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function desvioFormatter(cell) {
        var rowData = cell.getRow().getData();
        var field = cell.getField();
        var labelField = field + "_label";
        var label = rowData[labelField] || "0,00%";
        var valor = Number(cell.getValue() || 0);
        var real = 0;
        var orcamento = 0;
        if (field === "total_desvio") {
            real = Number(rowData.total_real || 0);
            orcamento = Number(rowData.total_orcamento || 0);
        } else if (field.endsWith("_desvio")) {
            var base = field.replace("_desvio", "");
            real = Number(rowData[base + "_real"] || 0);
            orcamento = Number(rowData[base + "_orcamento"] || 0);
        }

        var invalido = !Number.isFinite(valor) || !Number.isFinite(real) || !Number.isFinite(orcamento) || real < 0 || orcamento < 0 || (orcamento === 0 && real !== 0);

        var classe = "desvio-verde";
        if (invalido) {
            classe = "desvio-vermelho-escuro";
            label = "B.O";
        } else if (valor > 5) {
            classe = "desvio-roxo";
        } else if (valor > 0) {
            classe = "desvio-vermelho";
        } else if (valor < -5) {
            classe = "desvio-laranja";
        } else if (valor < 0) {
            classe = "desvio-amarelo";
        }
        return '<span class="desvio-chip ' + classe + '">' + label + "</span>";
    }

    function readJsonScript(id) {
        var element = document.getElementById(id);
        if (!element) return [];
        try {
            return JSON.parse(element.textContent || "[]");
        } catch (_error) {
            return [];
        }
    }

    function formatDateIsoToBr(value) {
        var iso = String(value || "").trim();
        if (!iso) return "";
        var parts = iso.split("-");
        if (parts.length !== 3) return iso;
        return parts[2] + "/" + parts[1] + "/" + parts[0];
    }

    function buildEditorValues(items, idKey, labelBuilder) {
        var values = {};
        (items || []).forEach(function (item) {
            var id = String(item && item[idKey] !== undefined && item[idKey] !== null ? item[idKey] : "").trim();
            if (!id) return;
            values[id] = String(labelBuilder(item) || "").trim();
        });
        return values;
    }

    function buildLabelMap(values) {
        var map = {};
        Object.keys(values || {}).forEach(function (key) {
            map[String(key)] = values[key];
        });
        return map;
    }

    function buildOrcamentoActionsColumn(config) {
        var cfg = config || {};
        return window.TabulatorDefaults.buildSaveDeleteActionColumn({
            field: "editar_url",
            submitPost: submitPost,
            getSavePayload: typeof cfg.getSavePayload === "function" ? cfg.getSavePayload : function () { return {}; },
            getDeleteUrl: function (row) {
                return row.excluir_url;
            },
            deleteConfirm: cfg.deleteConfirm || "",
            width: 180,
        });
    }

    function hasEditAction(data) {
        if (window.TabulatorDefaults && typeof window.TabulatorDefaults.hasAnyRowAction === "function") {
            return window.TabulatorDefaults.hasAnyRowAction(data, ["editar_url"]);
        }
        return Array.isArray(data) && data.some(function (item) { return Boolean(item && item.editar_url); });
    }

    function configurarUpload(config) {
        var form = document.getElementById(config.formId);
        if (!form) return;

        var dropzone = document.getElementById(config.dropzoneId);
        var input = document.getElementById(config.inputId);
        var fileStatus = document.getElementById(config.statusId);
        if (!dropzone || !input || !fileStatus) return;

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
                window.alert("Selecione arquivos .xls para continuar.");
            }
        });
    }

    function montarTabelaComparativo() {
        var dataElement = document.getElementById("orcamento-x-realizado-tabulator-data");
        var target = document.getElementById("orcamento-comparativo-tabulator");
        if (!dataElement || !target || !window.Tabulator) return;

        var data = JSON.parse(dataElement.textContent || "[]");
        var meses = [
            { key: "janeiro", title: "JANEIRO" },
            { key: "fevereiro", title: "FEVEREIRO" },
            { key: "marco", title: "MARCO" },
            { key: "abril", title: "ABRIL" },
            { key: "maio", title: "MAIO" },
            { key: "junho", title: "JUNHO" },
            { key: "julho", title: "JULHO" },
            { key: "agosto", title: "AGOSTO" },
            { key: "setembro", title: "SETEMBRO" },
            { key: "outubro", title: "OUTUBRO" },
            { key: "novembro", title: "NOVEMBRO" },
            { key: "dezembro", title: "DEZEMBRO" },
        ];

        var columns = [
            {
                title: "Custo Bruto / Despesas",
                field: "descricao",
                width: 340,
                headerFilter: "input",
            },
        ];

        meses.forEach(function (mes) {
            columns.push({
                title: mes.title,
                columns: [
                    { title: "Vlr. REAL", field: mes.key + "_real", hozAlign: "right", formatter: moneyFormatter, width: 130 },
                    { title: "Vlr. ORCAMENTO", field: mes.key + "_orcamento", hozAlign: "right", formatter: moneyFormatter, width: 145 },
                    { title: "DESVIOS %", field: mes.key + "_desvio", hozAlign: "right", formatter: desvioFormatter, width: 120 },
                ],
            });
        });

        columns.push({
            title: "TOTAL",
            columns: [
                { title: "Vlr. REAL", field: "total_real", hozAlign: "right", formatter: moneyFormatter, width: 130 },
                { title: "Vlr. ORCAMENTO", field: "total_orcamento", hozAlign: "right", formatter: moneyFormatter, width: 145 },
                { title: "DESVIOS %", field: "total_desvio", hozAlign: "right", formatter: desvioFormatter, width: 120 },
            ],
        });

        window.TabulatorDefaults.create(target, {
            data: data,
            dataTree: true,
            dataTreeStartExpanded: false,
            dataTreeChildField: "_children",
            rowFormatter: function (row) {
                var rowData = row.getData();
                if (rowData.is_grand_total) {
                    row.getElement().classList.add("orcamento-grand-total-row");
                }
            },
            columns: columns,
        });
    }

    function montarTabelaRealizados() {
        var dataElement = document.getElementById("orcamento-realizado-tabulator-data");
        var target = document.getElementById("orcamento-realizado-tabulator");
        if (!dataElement || !target || !window.Tabulator) return;

        var data = JSON.parse(dataElement.textContent || "[]");
        var titulos = readJsonScript("orcamento-titulos-data");
        var naturezas = readJsonScript("orcamento-naturezas-data");
        var operacoes = readJsonScript("orcamento-operacoes-data");
        var parceiros = readJsonScript("orcamento-parceiros-data");
        var centros = readJsonScript("orcamento-centros-resultado-data");

        var titulosValues = buildEditorValues(titulos, "id", function (item) {
            return (item.tipo_titulo_codigo || "") + " - " + (item.descricao || "");
        });
        var naturezasValues = buildEditorValues(naturezas, "id", function (item) {
            return (item.codigo || "") + " - " + (item.descricao || "");
        });
        var operacoesValues = buildEditorValues(operacoes, "id", function (item) {
            return (item.tipo_operacao_codigo || "") + " - " + (item.descricao_receita_despesa || "");
        });
        var parceirosValues = buildEditorValues(parceiros, "id", function (item) {
            return (item.codigo || "") + " - " + (item.nome || "");
        });
        var centrosValues = buildEditorValues(centros, "id", function (item) {
            return item.descricao || "";
        });

        var titulosMap = buildLabelMap(titulosValues);
        var naturezasMap = buildLabelMap(naturezasValues);
        var operacoesMap = buildLabelMap(operacoesValues);
        var parceirosMap = buildLabelMap(parceirosValues);
        var centrosMap = buildLabelMap(centrosValues);
        var possuiEdicao = hasEditAction(data);

        var colunas = [
            { title: "Nome Empresa", field: "nome_empresa", headerFilter: "input", editor: possuiEdicao ? "input" : false },
            {
                title: "Dt. Vencimento",
                field: "data_vencimento_iso",
                headerFilter: "input",
                editor: possuiEdicao ? "input" : false,
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
            },
            {
                title: "Data Baixa",
                field: "data_baixa_iso",
                headerFilter: "input",
                editor: possuiEdicao ? "input" : false,
                formatter: function (cell) {
                    return formatDateIsoToBr(cell.getValue());
                },
            },
            { title: "Vlr Baixa", field: "valor_baixa", hozAlign: "right", formatter: moneyFormatter, editor: possuiEdicao ? "input" : false },
            { title: "Valor Liquido", field: "valor_liquido", hozAlign: "right", formatter: moneyFormatter, editor: possuiEdicao ? "input" : false },
            { title: "Vlr do Desdobramento", field: "valor_desdobramento", hozAlign: "right", formatter: moneyFormatter, editor: possuiEdicao ? "input" : false },
            {
                title: "Titulo",
                field: "titulo_id",
                editor: possuiEdicao ? "list" : false,
                editorParams: { values: titulosValues, clearable: true },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var id = String(cell.getValue() || "");
                    return titulosMap[id] || row.titulo_descricao || "";
                },
            },
            {
                title: "Natureza",
                field: "natureza_id",
                editor: possuiEdicao ? "list" : false,
                editorParams: { values: naturezasValues, clearable: true },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var id = String(cell.getValue() || "");
                    return naturezasMap[id] || row.natureza_descricao || "";
                },
            },
            {
                title: "Centro Resultado",
                field: "centro_resultado_id",
                editor: possuiEdicao ? "list" : false,
                editorParams: { values: centrosValues, clearable: false },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var id = String(cell.getValue() || "");
                    return centrosMap[id] || row.centro_resultado_descricao || "";
                },
            },
            {
                title: "Receita/Despesa",
                field: "operacao_id",
                editor: possuiEdicao ? "list" : false,
                editorParams: { values: operacoesValues, clearable: true },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var id = String(cell.getValue() || "");
                    return operacoesMap[id] || row.operacao_descricao || "";
                },
            },
            {
                title: "Parceiro",
                field: "parceiro_id",
                editor: possuiEdicao ? "list" : false,
                editorParams: { values: parceirosValues, clearable: true },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var id = String(cell.getValue() || "");
                    return parceirosMap[id] || row.parceiro_nome || "";
                },
            },
        ];

        if (possuiEdicao) {
            colunas.push(buildOrcamentoActionsColumn({
                deleteConfirm: "Excluir orcamento realizado?",
                getSavePayload: function (row) {
                    return {
                        nome_empresa: row.nome_empresa || "",
                        data_vencimento: row.data_vencimento_iso || "",
                        data_baixa: row.data_baixa_iso || "",
                        valor_baixa: row.valor_baixa || "",
                        valor_liquido: row.valor_liquido || "",
                        valor_desdobramento: row.valor_desdobramento || "",
                        titulo_id: row.titulo_id || "",
                        natureza_id: row.natureza_id || "",
                        centro_resultado_id: row.centro_resultado_id || "",
                        operacao_id: row.operacao_id || "",
                        parceiro_id: row.parceiro_id || "",
                    };
                },
            }));
        }

        window.TabulatorDefaults.create(target, {
            data: data,
            columns: colunas,
        });
    }

    function montarTabelaOrcamentos() {
        var dataElement = document.getElementById("orcamentos-tabulator-data");
        var target = document.getElementById("orcamentos-tabulator");
        if (!dataElement || !target || !window.Tabulator) return;

        var data = JSON.parse(dataElement.textContent || "[]");
        var naturezas = readJsonScript("orcamento-planejado-naturezas-data");
        var centros = readJsonScript("orcamento-planejado-centros-resultado-data");

        var naturezasValues = buildEditorValues(naturezas, "id", function (item) {
            return (item.codigo || "") + " - " + (item.descricao || "");
        });
        var centrosValues = buildEditorValues(centros, "id", function (item) {
            return item.descricao || "";
        });
        var naturezasMap = buildLabelMap(naturezasValues);
        var centrosMap = buildLabelMap(centrosValues);
        var possuiEdicao = hasEditAction(data);

        function atualizarTotalDaLinha(rowData, row) {
            var total = 0;
            [
                "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
                "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
            ].forEach(function (campo) {
                total += Number(rowData[campo] || 0);
            });
            row.update({ total: total });
        }

        function monthColumn(title, field) {
            return {
                title: title,
                field: field,
                hozAlign: "right",
                formatter: moneyFormatter,
                editor: possuiEdicao ? "input" : false,
                cellEdited: function (cell) {
                    var row = cell.getRow();
                    var rowData = row.getData();
                    atualizarTotalDaLinha(rowData, row);
                },
            };
        }

        var colunas = [
            {
                title: "Centro Resultado",
                field: "centro_resultado_id",
                editor: possuiEdicao ? "list" : false,
                editorParams: { values: centrosValues, clearable: true },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var id = String(cell.getValue() || "");
                    return centrosMap[id] || row.centro_resultado_descricao || "";
                },
            },
            {
                title: "Natureza",
                field: "natureza_id",
                editor: possuiEdicao ? "list" : false,
                editorParams: { values: naturezasValues, clearable: true },
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var id = String(cell.getValue() || "");
                    return naturezasMap[id] || row.natureza_descricao || "";
                },
            },
            { title: "Nome Empresa", field: "nome_empresa", headerFilter: "input", editor: possuiEdicao ? "input" : false },
            { title: "Ano", field: "ano", hozAlign: "center", headerFilter: "input", editor: possuiEdicao ? "input" : false },
            monthColumn("Janeiro", "janeiro"),
            monthColumn("Fevereiro", "fevereiro"),
            monthColumn("Marco", "marco"),
            monthColumn("Abril", "abril"),
            monthColumn("Maio", "maio"),
            monthColumn("Junho", "junho"),
            monthColumn("Julho", "julho"),
            monthColumn("Agosto", "agosto"),
            monthColumn("Setembro", "setembro"),
            monthColumn("Outubro", "outubro"),
            monthColumn("Novembro", "novembro"),
            monthColumn("Dezembro", "dezembro"),
            { title: "TOTAL", field: "total", hozAlign: "right", formatter: moneyFormatter },
        ];

        if (possuiEdicao) {
            colunas.push(buildOrcamentoActionsColumn({
                deleteConfirm: "Excluir orcamento planejado?",
                getSavePayload: function (row) {
                    return {
                        nome_empresa: row.nome_empresa || "",
                        ano: row.ano || "",
                        centro_resultado_id: row.centro_resultado_id || "",
                        natureza_id: row.natureza_id || "",
                        janeiro: row.janeiro || "",
                        fevereiro: row.fevereiro || "",
                        marco: row.marco || "",
                        abril: row.abril || "",
                        maio: row.maio || "",
                        junho: row.junho || "",
                        julho: row.julho || "",
                        agosto: row.agosto || "",
                        setembro: row.setembro || "",
                        outubro: row.outubro || "",
                        novembro: row.novembro || "",
                        dezembro: row.dezembro || "",
                    };
                },
            }));
        }

        window.TabulatorDefaults.create(target, {
            data: data,
            columns: colunas,
        });
    }

    configurarUpload({
        formId: "upload-orcamento-form",
        dropzoneId: "dropzone-orcamento",
        inputId: "arquivo-orcamento-input",
        statusId: "nome-arquivos-orcamento-selecionados",
    });

    montarTabelaComparativo();
    montarTabelaRealizados();
    montarTabelaOrcamentos();
})();
