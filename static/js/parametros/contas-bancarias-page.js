(function () {
    var dataElement = document.getElementById("contas-bancarias-tabulator-data");
    var opcoesElement = document.getElementById("contas-bancarias-opcoes-data");
    var cadastroForm = document.getElementById("contas-bancarias-cadastro-form");
    var saveStatusEl = document.getElementById("contas-bancarias-save-status");

    if (!dataElement || !opcoesElement || !cadastroForm || !window.Tabulator || !window.TabulatorDefaults) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var opcoes = JSON.parse(opcoesElement.textContent || "[]");
    var nomeEmpresaValues = {};
    var tabela = null;
    var seqByRowId = {};
    var internalUpdate = false;

    opcoes.forEach(function (opcao) {
        nomeEmpresaValues[String(opcao.id)] = String(opcao.nome || "");
    });

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
        var csrfToken = getCsrfToken();
        if (csrfToken) {
            formData.append("csrfmiddlewaretoken", csrfToken);
        }
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
            "contas-bancarias-save-status--ok",
            "contas-bancarias-save-status--error",
            "contas-bancarias-save-status--progress"
        );
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function buildPayloadFromRow(rowData) {
        return {
            agencia: toText(rowData.agencia),
            numero_conta: toText(rowData.numero_conta),
            nome_banco: toText(rowData.nome_banco),
            nome_empresa_fantasia: toText(rowData.nome_empresa_fantasia),
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

    function atualizarRotuloNomeEmpresa(rowData) {
        var key = String(rowData.nome_empresa_fantasia || "");
        rowData.nome_empresa_fantasia_label = nomeEmpresaValues[key] || "";
    }

    function saveRowAutomatically(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;

        var rowData = row.getData() || {};
        if (!rowData.editar_url) return;

        atualizarRotuloNomeEmpresa(rowData);

        var rowId = rowData.id;
        var currentSeq = Number(seqByRowId[rowId] || 0) + 1;
        seqByRowId[rowId] = currentSeq;

        var oldValue = typeof cell.getOldValue === "function" ? cell.getOldValue() : null;
        var payload = buildPayloadFromRow(rowData);

        var formData = new FormData();
        appendCsrfToken(formData);
        Object.keys(payload).forEach(function (key) {
            formData.append(key, payload[key]);
        });

        setSaveStatus("Salvando alteracao...", "contas-bancarias-save-status--progress");

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
                    restoreCellValue(cell, oldValue);
                    setSaveStatus(
                        result.body && result.body.message ? result.body.message : "Falha ao salvar.",
                        "contas-bancarias-save-status--error"
                    );
                    return;
                }

                if (result.body.registro && typeof row.update === "function") {
                    internalUpdate = true;
                    row.update(result.body.registro);
                    internalUpdate = false;
                }

                setSaveStatus("Salvo automaticamente.", "contas-bancarias-save-status--ok");
            })
            .catch(function () {
                if (seqByRowId[rowId] !== currentSeq) return;
                restoreCellValue(cell, oldValue);
                setSaveStatus("Falha ao salvar.", "contas-bancarias-save-status--error");
            });
    }

    function onCellEdited(cell) {
        if (internalUpdate) return;
        saveRowAutomatically(cell);
    }

    function submitCreate(event) {
        if (!event) return;
        event.preventDefault();

        var url = cadastroForm.getAttribute("action");
        if (!url) return;

        var formData = new FormData(cadastroForm);
        if (!formData.get("csrfmiddlewaretoken")) {
            appendCsrfToken(formData);
        }

        setSaveStatus("Criando registro...", "contas-bancarias-save-status--progress");

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
                        "contas-bancarias-save-status--error"
                    );
                    return;
                }

                Promise.resolve(tabela.addData([result.body.registro], false))
                    .then(function () {
                        cadastroForm.reset();
                        setSaveStatus("Registro criado e tabela atualizada.", "contas-bancarias-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro criado, mas houve falha ao atualizar a tabela.",
                            "contas-bancarias-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao criar registro.", "contas-bancarias-save-status--error");
            });
    }

    function deleteRowByCell(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;
        var rowData = row.getData() || {};
        if (!rowData.excluir_url) return;
        if (!window.confirm("Excluir conta bancaria?")) return;

        var formData = new FormData();
        appendCsrfToken(formData);

        setSaveStatus("Excluindo registro...", "contas-bancarias-save-status--progress");

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
                        "contas-bancarias-save-status--error"
                    );
                    return;
                }

                if (Array.isArray(result.body.registros) && typeof tabela.replaceData === "function") {
                    Promise.resolve(tabela.replaceData(result.body.registros))
                        .then(function () {
                            setSaveStatus("Registro excluido e tabela atualizada.", "contas-bancarias-save-status--ok");
                        })
                        .catch(function () {
                            setSaveStatus(
                                "Registro excluido, mas houve falha ao atualizar a tabela.",
                                "contas-bancarias-save-status--error"
                            );
                        });
                    return;
                }

                Promise.resolve(row.delete())
                    .then(function () {
                        setSaveStatus("Registro excluido e tabela atualizada.", "contas-bancarias-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro excluido, mas houve falha ao atualizar a tabela.",
                            "contas-bancarias-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao excluir registro.", "contas-bancarias-save-status--error");
            });
    }

    function buildDeleteColumn() {
        return {
            title: "Acoes",
            field: "acoes",
            width: 120,
            headerSort: false,
            hozAlign: "center",
            formatter: function () {
                return '<button type="button" class="btn-danger">Excluir</button>';
            },
            cellClick: function (e, cell) {
                e.preventDefault();
                deleteRowByCell(cell);
            },
        };
    }

    tabela = window.TabulatorDefaults.create("#contas-bancarias-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Agencia", field: "agencia", editor: "input", cellEdited: onCellEdited},
            {title: "Numero Conta", field: "numero_conta", editor: "input", cellEdited: onCellEdited},
            {title: "Nome Banco", field: "nome_banco", editor: "input", cellEdited: onCellEdited},
            {
                title: "Empresa Fantasia",
                field: "nome_empresa_fantasia",
                editor: "list",
                editorParams: {
                    values: nomeEmpresaValues,
                    clearable: false,
                },
                formatter: function (cell) {
                    var row = cell.getRow().getData() || {};
                    return row.nome_empresa_fantasia_label || nomeEmpresaValues[String(row.nome_empresa_fantasia || "")] || "";
                },
                cellEdited: onCellEdited,
            },
            buildDeleteColumn(),
        ],
    });

    cadastroForm.addEventListener("submit", submitCreate);
})();
