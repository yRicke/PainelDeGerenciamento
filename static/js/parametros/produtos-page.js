(function () {
    var dataElement = document.getElementById("produtos-tabulator-data");
    if (!dataElement || !window.Tabulator || !window.FinanceiroCrudUtils) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var submitPost = window.FinanceiroCrudUtils.submitPost;
    var colunaAcoes = window.TabulatorDefaults.buildSaveDeleteActionColumn({
        field: "editar_url",
        submitPost: submitPost,
        getSavePayload: function (row) {
            return {
                codigo_produto: row.codigo_produto || "",
                status: row.status || "",
                descricao_produto: row.descricao_produto || "",
                kg: row.kg || "",
                remuneracao_por_fardo: row.remuneracao_por_fardo || "",
                ppm: row.ppm || "",
                peso_kg: row.peso_kg || "",
                pacote_por_fardo: row.pacote_por_fardo || "",
                turno: row.turno || "",
                horas: row.horas || "",
                setup: row.setup || "",
                horas_uteis: row.horas_uteis || "",
                empacotadeiras: row.empacotadeiras || "",
                producao_por_dia_fd: row.producao_por_dia_fd || "",
                estoque_minimo_pacote: row.estoque_minimo_pacote || "",
            };
        },
        getDeleteUrl: function (row) {
            return row.excluir_url;
        },
        deleteConfirm: "Excluir produto?",
    });

    var tabela = window.TabulatorDefaults.create("#produtos-tabulator", {
        data: data,
        columns: [
            {title: "ID", field: "id", width: 80, hozAlign: "center"},
            {title: "Codigo", field: "codigo_produto", editor: "input"},
            {title: "Status", field: "status", editor: "input"},
            {title: "Descricao", field: "descricao_produto", editor: "input"},
            {title: "KG", field: "kg", hozAlign: "right", editor: "input"},
            {title: "Rem. por Fardo", field: "remuneracao_por_fardo", hozAlign: "right", editor: "input"},
            {title: "PPM", field: "ppm", hozAlign: "right", editor: "input"},
            {title: "Peso (KG)", field: "peso_kg", hozAlign: "right", editor: "input"},
            {title: "Pacote/Fardo", field: "pacote_por_fardo", hozAlign: "right", editor: "input"},
            {title: "Turno", field: "turno", hozAlign: "right", editor: "input"},
            {title: "Horas", field: "horas", hozAlign: "right", editor: "input"},
            {title: "Setup", field: "setup", hozAlign: "right", editor: "input"},
            {title: "Horas Uteis", field: "horas_uteis", hozAlign: "right", editor: "input"},
            {title: "Empacotadeiras", field: "empacotadeiras", hozAlign: "right", editor: "input"},
            {title: "Prod. Dia (FD)", field: "producao_por_dia_fd", hozAlign: "right", editor: "input"},
            {title: "Est. Min. Pacote", field: "estoque_minimo_pacote", hozAlign: "right", editor: "input"},
            colunaAcoes,
        ],
    });

})();
