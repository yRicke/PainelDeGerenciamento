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
})();
