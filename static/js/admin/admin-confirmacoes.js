(function () {
    const defaultMessage = "Confirma esta acao?";

    document.querySelectorAll("form[data-confirm-submit]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const message = form.dataset.confirmMessage || defaultMessage;
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll(".js-confirm-link").forEach(function (link) {
        link.addEventListener("click", function (event) {
            const message = link.dataset.confirmMessage || defaultMessage;
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    const checkboxesModulos = Array.from(document.querySelectorAll('input[name="modulos"]'));
    function marcarTodosModulos(valor) {
        checkboxesModulos.forEach(function (checkbox) {
            checkbox.checked = valor;
        });
    }

    const botaoMarcarTodos = document.querySelector(".js-marcar-todos");
    if (botaoMarcarTodos && checkboxesModulos.length) {
        botaoMarcarTodos.addEventListener("click", function () {
            marcarTodosModulos(true);
        });
    }

    const botaoDesmarcarTodos = document.querySelector(".js-desmarcar-todos");
    if (botaoDesmarcarTodos && checkboxesModulos.length) {
        botaoDesmarcarTodos.addEventListener("click", function () {
            marcarTodosModulos(false);
        });
    }
})();
