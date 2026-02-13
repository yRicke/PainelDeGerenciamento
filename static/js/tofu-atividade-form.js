(function () {
    function atualizarEstadoDataFinalizada(form) {
        var progressoInput = form.querySelector("[data-progresso]");
        var dataFinalizadaInput = form.querySelector("[data-data-finalizada]");
        if (!progressoInput || !dataFinalizadaInput) return;

        var progresso = parseInt(progressoInput.value || "0", 10);
        var podePreencherDataFinalizada = progresso >= 100;

        if (!podePreencherDataFinalizada) {
            dataFinalizadaInput.value = "";
        }
        dataFinalizadaInput.disabled = !podePreencherDataFinalizada;
        dataFinalizadaInput.required = podePreencherDataFinalizada;
        dataFinalizadaInput.setCustomValidity("");

        if (podePreencherDataFinalizada && !dataFinalizadaInput.value) {
            dataFinalizadaInput.setCustomValidity("Com progresso 100%, preencha a Data Finalizada.");
        }

        dataFinalizadaInput.title = podePreencherDataFinalizada
            ? "Com progresso 100%, o preenchimento da Data Finalizada e obrigatorio."
            : "A data finalizada so pode ser preenchida com progresso 100%.";
    }

    document.querySelectorAll("[data-atividade-form]").forEach(function (form) {
        var progressoInput = form.querySelector("[data-progresso]");
        var dataFinalizadaInput = form.querySelector("[data-data-finalizada]");
        if (!progressoInput || !dataFinalizadaInput) return;

        atualizarEstadoDataFinalizada(form);
        progressoInput.addEventListener("input", function () {
            atualizarEstadoDataFinalizada(form);
        });
        progressoInput.addEventListener("change", function () {
            atualizarEstadoDataFinalizada(form);
        });
        dataFinalizadaInput.addEventListener("input", function () {
            atualizarEstadoDataFinalizada(form);
        });
        dataFinalizadaInput.addEventListener("change", function () {
            atualizarEstadoDataFinalizada(form);
        });
        form.addEventListener("submit", function () {
            atualizarEstadoDataFinalizada(form);
        });
    });
})();
