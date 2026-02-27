(function () {
    function normalizeLabel(value) {
        return String(value || "").trim().replace(/\.$/, "");
    }

    function onlyAllowedFileMessage(label) {
        return "Envie apenas arquivo " + normalizeLabel(label) + ".";
    }

    function selectFileToContinueMessage(label) {
        return "Selecione um arquivo " + normalizeLabel(label) + " para continuar.";
    }

    function noFileFoundMessage(label) {
        return "Nenhum arquivo " + normalizeLabel(label) + " encontrado.";
    }

    function selectFolderToContinueMessage(label) {
        return "Selecione uma pasta com arquivos " + normalizeLabel(label) + " para continuar.";
    }

    window.FrontendText = Object.freeze({
        common: Object.freeze({
            actionColumn: "A\u00E7\u00F5es",
            selectedFilePrefix: "Arquivo selecionado: ",
        }),
        confirm: Object.freeze({
            replaceCurrentFile: "J\u00E1 existe um arquivo na pasta. Deseja substituir o arquivo atual?",
            deleteCollaborator: "Excluir colaborador?",
        }),
        upload: Object.freeze({
            onlyAllowedFile: onlyAllowedFileMessage,
            selectFileToContinue: selectFileToContinueMessage,
            noFileFound: noFileFoundMessage,
            selectFolderToContinue: selectFolderToContinueMessage,
        }),
    });
})();
