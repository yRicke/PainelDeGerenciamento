(function () {
    var dataElement = document.getElementById("atividades-tabulator-data");
    if (!dataElement || !window.Tabulator) return;

    var data = JSON.parse(dataElement.textContent || "[]");
    var colunas = [
        {title: "ID", field: "id", width: 70, hozAlign: "center"},
        {title: "Projeto", field: "projeto"},
        {title: "Código", field: "codigo_projeto"},
        {title: "Criada por", field: "criada_por"},
        {title: "Gestor", field: "gestor"},
        {title: "Responsável", field: "responsavel"},
        {title: "Interlocutor", field: "interlocutor"},
        {title: "Prazo (semana)", field: "semana_de_prazo", hozAlign: "center"},
        {title: "Prev. Início", field: "data_previsao_inicio"},
        {title: "Prev. Término", field: "data_previsao_termino"},
        {title: "Finalizada", field: "data_finalizada"},
        {title: "Indicador", field: "indicador"},
        {title: "Histórico", field: "historico"},
        {title: "Tarefa", field: "tarefa"},
        {title: "Progresso (%)", field: "progresso", hozAlign: "center"},
    ];

    window.TabulatorDefaults.addEditActionColumnIfAny(colunas, data);

    var tabela = window.TabulatorDefaults.create("#atividades-tabulator", {
        data: data,
        columns: colunas,
    });
    tabela.setLocale("pt-br");
})();
