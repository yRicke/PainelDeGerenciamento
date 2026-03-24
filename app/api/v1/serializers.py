from rest_framework import serializers

from ...models import Atividade, Colaborador, Projeto


class ProjetoResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projeto
        fields = ("id", "nome")


class ColaboradorResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Colaborador
        fields = ("id", "nome")


class AtividadeSerializer(serializers.ModelSerializer):
    projeto = ProjetoResumoSerializer(read_only=True)
    usuario = serializers.SerializerMethodField()
    gestor = ColaboradorResumoSerializer(read_only=True)
    responsavel = ColaboradorResumoSerializer(read_only=True)
    indicador = serializers.CharField(read_only=True)

    class Meta:
        model = Atividade
        fields = (
            "id",
            "projeto",
            "usuario",
            "gestor",
            "responsavel",
            "interlocutor",
            "semana_de_prazo",
            "data_previsao_inicio",
            "data_previsao_termino",
            "data_finalizada",
            "historico",
            "tarefa",
            "progresso",
            "indicador",
        )

    def get_usuario(self, obj):
        if not obj.usuario:
            return None
        nome_usuario = obj.usuario.get_full_name().strip() or obj.usuario.username
        return {
            "id": obj.usuario.id,
            "nome": nome_usuario,
        }

