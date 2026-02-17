(function () {
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
        var tokenFromInput = input ? input.value : "";
        return tokenFromInput || getCookie("csrftoken") || "";
    }

    function submitPost(url, fields, confirmMsg) {
        if (!url) return;
        if (confirmMsg && !window.confirm(confirmMsg)) return;

        var form = document.createElement("form");
        form.method = "POST";
        form.action = url;

        var csrfToken = getCsrfToken();
        if (csrfToken) {
            var csrfInput = document.createElement("input");
            csrfInput.type = "hidden";
            csrfInput.name = "csrfmiddlewaretoken";
            csrfInput.value = csrfToken;
            form.appendChild(csrfInput);
        }

        Object.keys(fields || {}).forEach(function (key) {
            var input = document.createElement("input");
            input.type = "hidden";
            input.name = key;
            input.value = fields[key];
            form.appendChild(input);
        });

        document.body.appendChild(form);
        form.submit();
    }

    window.FinanceiroCrudUtils = {
        submitPost: submitPost,
    };
})();
