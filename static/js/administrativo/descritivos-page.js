(function () {
    var dataElement = document.getElementById("descritivos-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.TabulatorDefaults) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var cadastroForm = document.getElementById("descritivos-cadastro-form");
    var inicioInput = cadastroForm ? cadastroForm.querySelector('input[name="inicio"]') : null;
    var terminoInput = cadastroForm ? cadastroForm.querySelector('input[name="termino"]') : null;
    var saveStatusEl = document.getElementById("descritivos-save-status");
    var seqByRowId = {};
    var internalUpdate = false;
    var tabela = null;

    var TEXT_FIELDS = [
        "contas_a_pagar",
        "contas_a_receber",
        "supervisor_financeiro",
        "faturamento",
        "supervisor_logistica",
        "conferente",
        "gerente_de_producao",
        "gerente_cml",
        "assistente_comercial",
        "diretor",
    ];

    var TEXT_COLUMNS = [
        {title: "Contas a Pagar", field: "contas_a_pagar", width: 260},
        {title: "Contas a Receber", field: "contas_a_receber", width: 260},
        {title: "Supervisor Financeiro", field: "supervisor_financeiro", width: 260},
        {title: "Faturamento", field: "faturamento", width: 240},
        {title: "Supervisor Logistica", field: "supervisor_logistica", width: 260},
        {title: "Conferente", field: "conferente", width: 220},
        {title: "Gerente de Producao", field: "gerente_de_producao", width: 260},
        {title: "Gerente CML", field: "gerente_cml", width: 220},
        {title: "Assistente Comercial", field: "assistente_comercial", width: 260},
        {title: "Diretor", field: "diretor", width: 240},
    ];

    function toText(value) {
        if (value === null || value === undefined) return "";
        return String(value).trim();
    }

    function normalizeTime(value) {
        var texto = toText(value);
        if (!texto) return "";

        var match = texto.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
        if (!match) return texto;

        var hora = Number(match[1]);
        var minuto = Number(match[2]);
        if (!Number.isFinite(hora) || !Number.isFinite(minuto)) return texto;
        if (hora < 0 || hora > 23 || minuto < 0 || minuto > 59) return texto;

        return String(hora).padStart(2, "0") + ":" + String(minuto).padStart(2, "0");
    }

    function isValidTime(value) {
        return /^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(toText(value));
    }

    function formatTimeCell(cell) {
        return normalizeTime(cell.getValue());
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

    function setSaveStatus(text, tone) {
        if (!saveStatusEl) return;
        saveStatusEl.classList.remove(
            "descritivos-save-status--ok",
            "descritivos-save-status--error",
            "descritivos-save-status--progress"
        );
        saveStatusEl.textContent = text || "";
        if (tone) saveStatusEl.classList.add(tone);
    }

    function appendCsrfToken(formData) {
        var csrfToken = getCsrfToken();
        if (csrfToken) {
            formData.append("csrfmiddlewaretoken", csrfToken);
        }
    }

    function buildPayloadFromRow(rowData) {
        var payload = {
            inicio: normalizeTime(rowData.inicio),
            termino: normalizeTime(rowData.termino),
        };

        TEXT_FIELDS.forEach(function (field) {
            payload[field] = toText(rowData[field]);
        });

        return payload;
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

    function setupFormTimeInputs() {
        [inicioInput, terminoInput].forEach(function (input) {
            if (!input) return;
            input.addEventListener("blur", function () {
                input.value = normalizeTime(input.value);
            });
        });
    }

    function saveRowAutomatically(cell) {
        if (!cell) return;
        var row = cell.getRow();
        if (!row) return;

        var rowData = row.getData() || {};
        if (!rowData.editar_url) return;

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

        setSaveStatus("Salvando alteracao...", "descritivos-save-status--progress");

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
                        "descritivos-save-status--error"
                    );
                    return;
                }

                if (result.body.registro && typeof row.update === "function") {
                    internalUpdate = true;
                    row.update(result.body.registro);
                    internalUpdate = false;
                }

                setSaveStatus("Salvo automaticamente.", "descritivos-save-status--ok");
            })
            .catch(function () {
                if (seqByRowId[rowId] !== currentSeq) return;
                restoreCellValue(cell, oldValue);
                setSaveStatus("Falha ao salvar.", "descritivos-save-status--error");
            });
    }

    function onCellEdited(cell) {
        if (internalUpdate) return;
        saveRowAutomatically(cell);
    }

    function submitCreate(event) {
        if (!event || !cadastroForm) return;
        event.preventDefault();
        if (!tabela || typeof tabela.addData !== "function") return;

        if (inicioInput) inicioInput.value = normalizeTime(inicioInput.value);
        if (terminoInput) terminoInput.value = normalizeTime(terminoInput.value);

        if (!isValidTime(inicioInput ? inicioInput.value : "")) {
            setSaveStatus("Preencha o Inicio no formato HH:MM.", "descritivos-save-status--error");
            return;
        }
        if (!isValidTime(terminoInput ? terminoInput.value : "")) {
            setSaveStatus("Preencha o Termino no formato HH:MM.", "descritivos-save-status--error");
            return;
        }

        var url = cadastroForm.getAttribute("action");
        if (!url) return;

        var formData = new FormData(cadastroForm);
        if (!formData.get("csrfmiddlewaretoken")) {
            appendCsrfToken(formData);
        }

        setSaveStatus("Criando registro...", "descritivos-save-status--progress");

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
                        "descritivos-save-status--error"
                    );
                    return;
                }

                Promise.resolve(tabela.addData([result.body.registro], true))
                    .then(function () {
                        cadastroForm.reset();
                        setSaveStatus("Registro criado e tabela atualizada.", "descritivos-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro criado, mas houve falha ao atualizar a tabela.",
                            "descritivos-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao criar registro.", "descritivos-save-status--error");
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

        setSaveStatus("Excluindo registro...", "descritivos-save-status--progress");

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
                        "descritivos-save-status--error"
                    );
                    return;
                }

                Promise.resolve(row.delete())
                    .then(function () {
                        setSaveStatus("Registro excluido e tabela atualizada.", "descritivos-save-status--ok");
                    })
                    .catch(function () {
                        setSaveStatus(
                            "Registro excluido, mas houve falha ao atualizar a tabela.",
                            "descritivos-save-status--error"
                        );
                    });
            })
            .catch(function () {
                setSaveStatus("Falha ao excluir registro.", "descritivos-save-status--error");
            });
    }

    function buildTextColumns() {
        return TEXT_COLUMNS.map(function (columnDef) {
            return {
                title: columnDef.title,
                field: columnDef.field,
                editor: "textarea",
                cellEdited: onCellEdited,
                width: columnDef.width,
            };
        });
    }

    function buildActionColumn() {
        return {
            title: "Acoes",
            field: "excluir_url",
            hozAlign: "center",
            headerFilter: false,
            formatter: function (cell) {
                if (!cell.getValue()) return "";
                return '<button class="btn-danger js-descritivos-excluir" type="button">Excluir</button>';
            },
            cellClick: function (event, cell) {
                var target = event && event.target;
                var button = target && target.closest ? target.closest(".js-descritivos-excluir") : null;
                if (!button) return;
                deleteRowByCell(cell);
            },
        };
    }

    tabela = window.TabulatorDefaults.create("#descritivos-tabulator", {
        data: data,
        columns: [
            {
                title: "Inicio",
                field: "inicio",
                editor: "input",
                formatter: formatTimeCell,
                mutatorEdit: normalizeTime,
                cellEdited: onCellEdited,
                width: 110,
                hozAlign: "center",
            },
            {
                title: "Termino",
                field: "termino",
                editor: "input",
                formatter: formatTimeCell,
                mutatorEdit: normalizeTime,
                cellEdited: onCellEdited,
                width: 110,
                hozAlign: "center",
            },
        ].concat(buildTextColumns(), [buildActionColumn()]),
    });

    if (cadastroForm) {
        setupFormTimeInputs();
        cadastroForm.addEventListener("submit", submitCreate);
    }

    setSaveStatus("", "");
})();
