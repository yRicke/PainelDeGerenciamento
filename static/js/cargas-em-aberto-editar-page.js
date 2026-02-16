(function () {
    var dataInicio = document.getElementById("data-inicio-editar");
    var prazoMaximo = document.getElementById("prazo-maximo-editar");
    var idadePreview = document.getElementById("idade-dias-preview");
    var criticaPreview = document.getElementById("critica-preview");
    var verificacaoPreview = document.getElementById("verificacao-preview");
    var dataChegada = document.getElementById("data-chegada-editar");
    var dataFinalizacao = document.getElementById("data-finalizacao-editar");

    if (
        !dataInicio
        || !prazoMaximo
        || !idadePreview
        || !criticaPreview
        || !verificacaoPreview
        || !dataChegada
        || !dataFinalizacao
    ) {
        return;
    }

    function parseISODate(iso) {
        if (!iso) return null;
        var parts = iso.split("-");
        if (parts.length !== 3) return null;
        var y = Number(parts[0]);
        var m = Number(parts[1]) - 1;
        var d = Number(parts[2]);
        if (!y || m < 0 || d <= 0) return null;
        return new Date(y, m, d);
    }

    function diasEntre(inicio, fim) {
        var msDia = 24 * 60 * 60 * 1000;
        var utcInicio = Date.UTC(inicio.getFullYear(), inicio.getMonth(), inicio.getDate());
        var utcFim = Date.UTC(fim.getFullYear(), fim.getMonth(), fim.getDate());
        return Math.max(0, Math.floor((utcFim - utcInicio) / msDia));
    }

    function atualizarResumo() {
        var inicio = parseISODate(dataInicio.value);
        var prazo = Number(prazoMaximo.value || 0);
        if (!Number.isFinite(prazo) || prazo < 0) prazo = 0;

        var idade = 0;
        if (inicio) {
            idade = diasEntre(inicio, new Date());
        }
        var critica = idade - prazo;
        var verificar = critica > 0;

        idadePreview.value = String(idade);
        criticaPreview.value = String(critica);
        verificacaoPreview.value = verificar ? "Verificar" : "Ok";
    }

    function atualizarBloqueioFinalizacao() {
        var temChegada = Boolean(dataChegada.value);
        dataFinalizacao.disabled = !temChegada;
        dataFinalizacao.min = dataChegada.value || "";
        if (!temChegada) {
            dataFinalizacao.value = "";
        }
    }

    dataInicio.addEventListener("change", atualizarResumo);
    dataInicio.addEventListener("input", atualizarResumo);
    prazoMaximo.addEventListener("change", atualizarResumo);
    prazoMaximo.addEventListener("input", atualizarResumo);
    dataChegada.addEventListener("change", atualizarBloqueioFinalizacao);
    dataChegada.addEventListener("input", atualizarBloqueioFinalizacao);

    atualizarResumo();
    atualizarBloqueioFinalizacao();
})();
