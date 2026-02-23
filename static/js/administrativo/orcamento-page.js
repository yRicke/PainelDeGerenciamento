(function () {
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

    function linkEditarFormatter(cell) {
        var url = cell.getValue();
        if (!url) return "";
        return '<a class="tabulator-action-link" href="' + url + '">Editar</a>';
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
                frozen: true,
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
            layout: "fitDataTable",
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
        function compararDataIso(aRow, bRow, campoIso) {
            var aIso = aRow.getData()[campoIso] || "";
            var bIso = bRow.getData()[campoIso] || "";
            return aIso.localeCompare(bIso);
        }

        window.TabulatorDefaults.create(target, {
            data: data,
            layout: "fitDataTable",
            pagination: true,
            paginationSize: 100,
            columns: [
                { title: "Nome Empresa", field: "nome_empresa", headerFilter: "input" },
                {
                    title: "Dt. Vencimento",
                    field: "data_vencimento",
                    headerFilter: "input",
                    sorter: function (_a, _b, aRow, bRow) {
                        return compararDataIso(aRow, bRow, "data_vencimento_iso");
                    },
                },
                {
                    title: "Data Baixa",
                    field: "data_baixa",
                    headerFilter: "input",
                    sorter: function (_a, _b, aRow, bRow) {
                        return compararDataIso(aRow, bRow, "data_baixa_iso");
                    },
                },
                { title: "Vlr Baixa", field: "valor_baixa", hozAlign: "right", formatter: moneyFormatter },
                { title: "Valor Liquido", field: "valor_liquido", hozAlign: "right", formatter: moneyFormatter },
                { title: "Vlr do Desdobramento", field: "valor_desdobramento", hozAlign: "right", formatter: moneyFormatter },
                { title: "Descricao (Tipo de Titulo)", field: "titulo_descricao", headerFilter: "input" },
                { title: "Descricao (Natureza)", field: "natureza_descricao", headerFilter: "input" },
                { title: "Descricao (Centro de Resultado)", field: "centro_resultado_descricao", headerFilter: "input" },
                { title: "Receita/Despesa", field: "operacao_descricao", headerFilter: "input" },
                { title: "Codigo Parceiro", field: "parceiro_codigo", headerFilter: "input" },
                { title: "Nome Parceiro", field: "parceiro_nome", headerFilter: "input" },
                { title: "Acoes", field: "editar_url", formatter: linkEditarFormatter, hozAlign: "center", width: 95 },
            ],
        });
    }

    function montarTabelaOrcamentos() {
        var dataElement = document.getElementById("orcamentos-tabulator-data");
        var target = document.getElementById("orcamentos-tabulator");
        if (!dataElement || !target || !window.Tabulator) return;

        var data = JSON.parse(dataElement.textContent || "[]");
        window.TabulatorDefaults.create(target, {
            data: data,
            layout: "fitDataTable",
            pagination: true,
            paginationSize: 100,
            columns: [
                { title: "Descricao (Centro de Resultado)", field: "centro_resultado_descricao", headerFilter: "input" },
                { title: "Descricao (Natureza)", field: "natureza_descricao", headerFilter: "input" },
                { title: "Nome Empresa", field: "nome_empresa", headerFilter: "input" },
                { title: "Ano", field: "ano", hozAlign: "center", headerFilter: "input" },
                { title: "Janeiro", field: "janeiro", hozAlign: "right", formatter: moneyFormatter },
                { title: "Fevereiro", field: "fevereiro", hozAlign: "right", formatter: moneyFormatter },
                { title: "Marco", field: "marco", hozAlign: "right", formatter: moneyFormatter },
                { title: "Abril", field: "abril", hozAlign: "right", formatter: moneyFormatter },
                { title: "Maio", field: "maio", hozAlign: "right", formatter: moneyFormatter },
                { title: "Junho", field: "junho", hozAlign: "right", formatter: moneyFormatter },
                { title: "Julho", field: "julho", hozAlign: "right", formatter: moneyFormatter },
                { title: "Agosto", field: "agosto", hozAlign: "right", formatter: moneyFormatter },
                { title: "Setembro", field: "setembro", hozAlign: "right", formatter: moneyFormatter },
                { title: "Outubro", field: "outubro", hozAlign: "right", formatter: moneyFormatter },
                { title: "Novembro", field: "novembro", hozAlign: "right", formatter: moneyFormatter },
                { title: "Dezembro", field: "dezembro", hozAlign: "right", formatter: moneyFormatter },
                { title: "TOTAL", field: "total", hozAlign: "right", formatter: moneyFormatter },
                { title: "Acoes", field: "editar_url", formatter: linkEditarFormatter, hozAlign: "center", width: 95 },
            ],
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

