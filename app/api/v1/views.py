from rest_framework import generics
from rest_framework.response import Response

from ...models import Atividade
from .permissions import HasTofuAccessOrFixedToken
from .serializers import AtividadeSerializer


class AtividadeListAPIView(generics.ListAPIView):
    serializer_class = AtividadeSerializer
    permission_classes = [HasTofuAccessOrFixedToken]

    def get_queryset(self):
        empresa = getattr(self, "empresa", None)
        if not empresa:
            return Atividade.objects.none()
        return (
            Atividade.objects.filter(projeto__empresa=empresa)
            .select_related("projeto", "usuario", "gestor", "responsavel")
            .order_by("-id")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "data": serializer.data,
                "total": queryset.count(),
            }
        )
