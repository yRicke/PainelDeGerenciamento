(function () {
    function atualizarFormularioUsuario(form) {
        var staffToggle = form.querySelector(".js-staff-toggle");
        var permissionsGrid = form.querySelector(".js-permissions-grid");
        if (!staffToggle || !permissionsGrid) {
            return;
        }

        var ocultarPermissoes = !!staffToggle.checked;
        permissionsGrid.hidden = ocultarPermissoes;
        permissionsGrid.setAttribute("aria-hidden", ocultarPermissoes ? "true" : "false");

        permissionsGrid
            .querySelectorAll("input[name='permissoes']")
            .forEach(function (checkboxPermissao) {
                checkboxPermissao.disabled = ocultarPermissoes;
            });
    }

    document.querySelectorAll(".js-user-form").forEach(function (form) {
        var staffToggle = form.querySelector(".js-staff-toggle");
        if (!staffToggle) {
            return;
        }

        staffToggle.addEventListener("change", function () {
            atualizarFormularioUsuario(form);
        });

        atualizarFormularioUsuario(form);
    });
})();
