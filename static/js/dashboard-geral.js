(function () {
    var mesInput = document.getElementById("dashboard-geral-mes");
    var mesForm = document.getElementById("dashboard-geral-filtro-mes-form");
    if (mesInput && mesForm) {
        mesInput.addEventListener("change", function () {
            if (typeof mesForm.requestSubmit === "function") {
                mesForm.requestSubmit();
                return;
            }
            mesForm.submit();
        });
    }

    var target = document.getElementById("dashboard-geral-tipo-venda-chart");
    if (!target || !window.ApexCharts) return;

    function parsePayload(id, fallback) {
        var el = document.getElementById(id);
        if (!el) return fallback;
        try {
            return JSON.parse(el.textContent || "[]");
        } catch (_err) {
            return fallback;
        }
    }

    var labels = parsePayload("dashboard-geral-tipo-venda-labels", []);
    var series = parsePayload("dashboard-geral-tipo-venda-series", []);

    var chart = new window.ApexCharts(target, {
        chart: {
            type: "donut",
            height: 260,
            toolbar: {show: false},
        },
        labels: labels,
        series: series,
        legend: {
            position: "bottom",
        },
        dataLabels: {
            enabled: true,
        },
        tooltip: {
            y: {
                formatter: function (value) {
                    return Number(value || 0).toLocaleString("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                    });
                },
            },
        },
        noData: {
            text: "Sem dados",
        },
    });
    chart.render();
})();
