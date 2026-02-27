(function () {
    function pad2(value) {
        return String(value).padStart(2, "0");
    }

    function dateToInputValue(date) {
        return [
            date.getUTCFullYear(),
            pad2(date.getUTCMonth() + 1),
            pad2(date.getUTCDate()),
        ].join("-");
    }

    function parseWeekValue(weekValue) {
        var match = /^(\d{4})-W(\d{2})$/.exec(weekValue || "");
        if (!match) return null;
        return {
            year: parseInt(match[1], 10),
            week: parseInt(match[2], 10),
        };
    }

    function getWeekBounds(year, week) {
        var jan4 = new Date(Date.UTC(year, 0, 4));
        var jan4WeekDay = jan4.getUTCDay() || 7;
        var mondayWeek1 = new Date(jan4);
        mondayWeek1.setUTCDate(jan4.getUTCDate() - jan4WeekDay + 1);

        var start = new Date(mondayWeek1);
        start.setUTCDate(mondayWeek1.getUTCDate() + (week - 1) * 7);

        var end = new Date(start);
        end.setUTCDate(start.getUTCDate() + 6);

        return { start: start, end: end };
    }

    function atualizarDatasPrevistas(form) {
        var semanaPrazoInput = form.querySelector("[data-semana-prazo]");
        var dataPrevInicioInput = form.querySelector("[data-data-previsao-inicio]");
        var dataPrevTerminoInput = form.querySelector("[data-data-previsao-termino]");
        if (!semanaPrazoInput || !dataPrevInicioInput || !dataPrevTerminoInput) return;

        var parsedWeek = parseWeekValue(semanaPrazoInput.value);
        if (!parsedWeek) {
            dataPrevInicioInput.value = "";
            dataPrevTerminoInput.value = "";
            return;
        }

        var bounds = getWeekBounds(parsedWeek.year, parsedWeek.week);
        dataPrevInicioInput.value = dateToInputValue(bounds.start);
        dataPrevTerminoInput.value = dateToInputValue(bounds.end);
    }

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
            ? "Com progresso 100%, o preenchimento da Data Finalizada é obrigatório."
            : "A Data Finalizada só pode ser preenchida com progresso 100%.";
    }

    document.querySelectorAll("[data-atividade-form]").forEach(function (form) {
        var semanaPrazoInput = form.querySelector("[data-semana-prazo]");
        var dataPrevInicioInput = form.querySelector("[data-data-previsao-inicio]");
        var dataPrevTerminoInput = form.querySelector("[data-data-previsao-termino]");
        var progressoInput = form.querySelector("[data-progresso]");
        var dataFinalizadaInput = form.querySelector("[data-data-finalizada]");
        if (
            !semanaPrazoInput ||
            !dataPrevInicioInput ||
            !dataPrevTerminoInput ||
            !progressoInput ||
            !dataFinalizadaInput
        ) return;

        atualizarDatasPrevistas(form);
        atualizarEstadoDataFinalizada(form);
        semanaPrazoInput.addEventListener("input", function () {
            atualizarDatasPrevistas(form);
        });
        semanaPrazoInput.addEventListener("change", function () {
            atualizarDatasPrevistas(form);
        });
        semanaPrazoInput.addEventListener("blur", function () {
            atualizarDatasPrevistas(form);
        });
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
            atualizarDatasPrevistas(form);
            atualizarEstadoDataFinalizada(form);
        });
    });
})();
