from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .utils.comercial_transformers import _definir_margem, _definir_lucro

UNSET = object()

class Empresa(models.Model):
    nome = models.CharField(max_length=150)
    possui_sistema = models.BooleanField(default=False)

    def __str__(self):
        return self.nome

    @classmethod
    def criar_empresa(cls, nome, possui_sistema=False):
        empresa = cls(nome=nome, possui_sistema=possui_sistema)
        empresa.save()
        return empresa

    def atualizar_nome(self, novo_nome=UNSET, possui_sistema=UNSET):
        if novo_nome is not UNSET:
            self.nome = novo_nome
        if possui_sistema is not UNSET:
            self.possui_sistema = bool(possui_sistema)
        self.save()

    def excluir_empresa(self):
        self.delete()

class Permissao(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome

class Usuario(AbstractUser):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="usuarios",
    )
    permissoes = models.ManyToManyField(Permissao, blank=True)

    def __str__(self):
        return f"{self.username} ({self.empresa})"

    @classmethod
    def criar_usuario(cls, username, password, empresa, permissoes=None, is_staff=False):
        usuario = cls.objects.create_user(
            username=username,
            password=password,
            empresa=empresa,
            is_staff=bool(is_staff),
        )
        if permissoes:
            usuario.permissoes.set(permissoes)
        return usuario

    @classmethod
    def listar_usuarios_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_usuario(self, username=None, password=None, permissoes=None, is_staff=UNSET):
        if username:
            self.username = username
        if password:
            self.set_password(password)
        if is_staff is not UNSET:
            self.is_staff = bool(is_staff)
        self.save()
        if permissoes is not None:
            self.permissoes.set(permissoes)

    def excluir_usuario(self):
        self.delete()

class Colaborador(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="colaboradores",
    )
    nome = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome}"

    @classmethod
    def criar_colaborador(cls, nome, empresa):
        colaborador = cls(nome=nome, empresa=empresa)
        colaborador.save()
        return colaborador

    @classmethod
    def listar_colaboradores_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_colaborador(self, novo_nome):
        self.nome = novo_nome
        self.save()

    def excluir_colaborador(self):
        self.delete()

class Projeto(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="projetos",
    )
    nome = models.CharField(max_length=150)
    codigo = models.CharField(max_length=50, blank=True, default="")

    def __str__(self):
        return f"{self.nome} ({self.codigo})"

    @classmethod
    def criar_projeto(cls, nome, empresa, codigo=""):
        projeto = cls(nome=nome, empresa=empresa, codigo=codigo)
        projeto.save()
        return projeto

    @classmethod
    def listar_projetos_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_projeto(self, novo_nome=None, novo_codigo=None):
        if novo_nome:
            self.nome = novo_nome
        if novo_codigo is not None:
            self.codigo = novo_codigo
        self.save()

    def excluir_projeto(self):
        self.delete()

class Atividade(models.Model):
    INDICADOR_CONCLUIDO = "Concluido"
    INDICADOR_ALERTA = "Alerta"
    INDICADOR_A_FAZER = "A Fazer"
    INDICADOR_ATRASADO = "Atrasado"

    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name="atividades",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="atividades_criadas",
    )

    # Pelo seu DER: Atividade tem 2 relacionamentos com Colaborador
    gestor = models.ForeignKey(
        Colaborador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="atividades_como_gestor",
    )
    responsavel = models.ForeignKey(
        Colaborador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="atividades_como_responsavel",
    )

    interlocutor = models.CharField(max_length=150, blank=True, default="")

    semana_de_prazo = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(53)],
    )
    data_previsao_inicio = models.DateField(null=True, blank=True)
    data_previsao_termino = models.DateField(null=True, blank=True)
    data_finalizada = models.DateField(null=True, blank=True)

    historico = models.TextField(blank=True, default="")
    tarefa = models.TextField(blank=True, default="")
    progresso = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"Atividade #{self.id} - {self.projeto.nome}"

    def clean(self):
        if self.data_finalizada and self.progresso < 100:
            raise ValidationError(
                {"data_finalizada": "A data finalizada so pode ser preenchida quando o progresso for 100%."}
            )

    def pode_ser_editada_por(self, usuario):
        if not usuario:
            return False
        if getattr(usuario, "is_staff", False) or getattr(usuario, "is_superuser", False):
            return True
        return bool(self.usuario_id and self.usuario_id == getattr(usuario, "id", None))

    @property
    def indicador(self):
        hoje = timezone.localdate()
        inicio_semana_atual = hoje - timedelta(days=hoje.isoweekday() - 1)
        fim_proxima_semana = inicio_semana_atual + timedelta(days=13)
        inicio_duas_semanas_apos = inicio_semana_atual + timedelta(days=14)

        if self.progresso >= 100:
            return self.INDICADOR_CONCLUIDO
        if self.data_previsao_termino and self.data_previsao_termino < hoje:
            return self.INDICADOR_ATRASADO
        if (
            self.data_previsao_termino
            and self.data_previsao_termino <= fim_proxima_semana
        ):
            return self.INDICADOR_ALERTA
        if (
            self.data_previsao_termino
            and self.data_previsao_termino >= inicio_duas_semanas_apos
        ):
            return self.INDICADOR_A_FAZER
        return self.INDICADOR_A_FAZER

    @classmethod
    def criar_atividade(
        cls,
        projeto,
        usuario=None,
        gestor=None,
        responsavel=None,
        interlocutor="",
        semana_de_prazo=None,
        data_previsao_inicio=None,
        data_previsao_termino=None,
        data_finalizada=None,
        historico="",
        tarefa="",
        progresso=0,
    ):
        atividade = cls(
            projeto=projeto,
            usuario=usuario,
            gestor=gestor,
            responsavel=responsavel,
            interlocutor=interlocutor,
            semana_de_prazo=semana_de_prazo,
            data_previsao_inicio=data_previsao_inicio,
            data_previsao_termino=data_previsao_termino,
            data_finalizada=data_finalizada,
            historico=historico,
            tarefa=tarefa,
            progresso=progresso
        )
        atividade.full_clean()
        atividade.save()
        return atividade

    @classmethod
    def listar_atividades_por_empresa(cls, empresa):
        return cls.objects.filter(projeto__empresa=empresa)

    def atualizar_atividade(
        self,
        projeto=UNSET,
        gestor=UNSET,
        responsavel=UNSET,
        interlocutor=UNSET,
        semana_de_prazo=UNSET,
        data_previsao_inicio=UNSET,
        data_previsao_termino=UNSET,
        data_finalizada=UNSET,
        historico=UNSET,
        tarefa=UNSET,
        progresso=UNSET,
    ):
        if projeto is not UNSET:
            self.projeto = projeto
        if gestor is not UNSET:
            self.gestor = gestor
        if responsavel is not UNSET:
            self.responsavel = responsavel
        if interlocutor is not UNSET:
            self.interlocutor = interlocutor
        if semana_de_prazo is not UNSET:
            self.semana_de_prazo = semana_de_prazo
        if data_previsao_inicio is not UNSET:
            self.data_previsao_inicio = data_previsao_inicio
        if data_previsao_termino is not UNSET:
            self.data_previsao_termino = data_previsao_termino
        if data_finalizada is not UNSET:
            self.data_finalizada = data_finalizada
        if historico is not UNSET:
            self.historico = historico
        if tarefa is not UNSET:
            self.tarefa = tarefa
        if progresso is not UNSET:
            self.progresso = progresso
        self.full_clean()
        self.save()

    def excluir_atividade(self):
        self.delete()

class Cidade(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="cidades")
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, default="", unique=True)

    def __str__(self):
        return self.nome
    
    @classmethod
    def criar_cidade(cls, nome, empresa, codigo):
        cidade = cls(nome=nome, empresa=empresa, codigo=codigo)
        cidade.save()
        return cidade
    
    @classmethod
    def listar_cidades_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)
    
    @classmethod
    def verificar_cidade_existe(cls, codigo, empresa):
        return cls.objects.filter(codigo=codigo, empresa=empresa).exists()

    def atualizar_cidade(self, novo_nome=None, novo_codigo=None):
        if novo_nome:
            self.nome = novo_nome
        if novo_codigo is not None:
            self.codigo = novo_codigo
        self.save()

    def excluir_cidade(self):
        self.delete()
    
class Regiao(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="regioes")
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=7, default="", unique=True)

    def __str__(self):
        return self.nome
    
    @classmethod
    def criar_regiao(cls, nome, empresa, codigo):
        regiao = cls(nome=nome, empresa=empresa, codigo=codigo)
        regiao.save()
        return regiao
    
    @classmethod
    def listar_regioes_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)
    
    @classmethod
    def verificar_regiao_existe(cls, nome, empresa):
        return cls.objects.filter(nome=nome, empresa=empresa).exists()

    def atualizar_regiao(self, novo_nome=None, novo_codigo=None):
        if novo_nome:
            self.nome = novo_nome
        if novo_codigo is not None:
            self.codigo = novo_codigo
        self.save()

    def excluir_regiao(self):
        self.delete()


class UnidadeFederativa(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="unidades_federativas")
    codigo = models.CharField(max_length=10, default="", unique=True)
    sigla = models.CharField(max_length=5)

    def __str__(self):
        return f"{self.sigla} ({self.codigo})"

    @classmethod
    def criar_unidade_federativa(cls, empresa, codigo, sigla):
        item = cls(empresa=empresa, codigo=codigo, sigla=sigla)
        item.save()
        return item

    @classmethod
    def listar_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_unidade_federativa(self, codigo=UNSET, sigla=UNSET):
        if codigo is not UNSET:
            self.codigo = codigo
        if sigla is not UNSET:
            self.sigla = sigla
        self.save()

    def excluir_unidade_federativa(self):
        self.delete()


class Rota(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="rotas")
    codigo_rota = models.CharField(max_length=50)
    uf = models.ForeignKey(UnidadeFederativa, on_delete=models.SET_NULL, null=True, blank=True, related_name="rotas")
    nome = models.CharField(max_length=150)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo_rota"], name="uq_rota_empresa_codigo"),
        ]

    def __str__(self):
        return f"{self.codigo_rota} - {self.nome}"

    @classmethod
    def criar_rota(cls, empresa, codigo_rota, nome, uf=None):
        item = cls(empresa=empresa, codigo_rota=codigo_rota, nome=nome, uf=uf)
        item.save()
        return item

    @classmethod
    def listar_rotas_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_rota(self, codigo_rota=UNSET, nome=UNSET, uf=UNSET):
        if codigo_rota is not UNSET:
            self.codigo_rota = codigo_rota
        if nome is not UNSET:
            self.nome = nome
        if uf is not UNSET:
            self.uf = uf
        self.save()

    def excluir_rota(self):
        self.delete()


class Motorista(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="motoristas")
    codigo_motorista = models.CharField(max_length=50)
    nome = models.CharField(max_length=150)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo_motorista"], name="uq_motorista_empresa_codigo"),
        ]

    def __str__(self):
        return f"{self.nome} ({self.codigo_motorista})"

    @classmethod
    def criar_motorista(cls, empresa, codigo_motorista, nome):
        item = cls(empresa=empresa, codigo_motorista=codigo_motorista, nome=nome)
        item.save()
        return item

    @classmethod
    def listar_motoristas_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_motorista(self, codigo_motorista=UNSET, nome=UNSET):
        if codigo_motorista is not UNSET:
            self.codigo_motorista = codigo_motorista
        if nome is not UNSET:
            self.nome = nome
        self.save()

    def excluir_motorista(self):
        self.delete()


class Transportadora(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="transportadoras")
    codigo_transportadora = models.CharField(max_length=50)
    nome = models.CharField(max_length=150)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo_transportadora"], name="uq_transportadora_empresa_codigo"),
        ]

    def __str__(self):
        return f"{self.nome} ({self.codigo_transportadora})"

    @classmethod
    def criar_transportadora(cls, empresa, codigo_transportadora, nome):
        item = cls(empresa=empresa, codigo_transportadora=codigo_transportadora, nome=nome)
        item.save()
        return item

    @classmethod
    def listar_transportadoras_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_transportadora(self, codigo_transportadora=UNSET, nome=UNSET):
        if codigo_transportadora is not UNSET:
            self.codigo_transportadora = codigo_transportadora
        if nome is not UNSET:
            self.nome = nome
        self.save()

    def excluir_transportadora(self):
        self.delete()


class Agenda(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="agendas")
    data_registro = models.DateField(default=timezone.localdate)
    numero_unico = models.CharField(max_length=80)
    previsao_carregamento = models.DateField()
    motorista = models.ForeignKey(Motorista, on_delete=models.PROTECT, related_name="agendas")
    transportadora = models.ForeignKey(Transportadora, on_delete=models.PROTECT, related_name="agendas")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "numero_unico"], name="uq_agenda_empresa_numero_unico"),
        ]

    def __str__(self):
        return f"Agenda {self.numero_unico}"

    @classmethod
    def criar_agenda(
        cls,
        empresa,
        numero_unico,
        previsao_carregamento,
        motorista,
        transportadora,
        data_registro=None,
    ):
        item = cls(
            empresa=empresa,
            data_registro=data_registro or timezone.localdate(),
            numero_unico=numero_unico,
            previsao_carregamento=previsao_carregamento,
            motorista=motorista,
            transportadora=transportadora,
        )
        item.save()
        return item

    @classmethod
    def listar_agendas_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_agenda(
        self,
        numero_unico=UNSET,
        previsao_carregamento=UNSET,
        motorista=UNSET,
        transportadora=UNSET,
        data_registro=UNSET,
    ):
        if numero_unico is not UNSET:
            self.numero_unico = numero_unico
        if previsao_carregamento is not UNSET:
            self.previsao_carregamento = previsao_carregamento
        if motorista is not UNSET:
            self.motorista = motorista
        if transportadora is not UNSET:
            self.transportadora = transportadora
        if data_registro is not UNSET:
            self.data_registro = data_registro
        self.save()

    def excluir_agenda(self):
        self.delete()


class PedidoPendente(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="pedidos_pendentes")
    numero_unico = models.CharField(max_length=80)
    rota = models.ForeignKey(Rota, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_pendentes")
    regiao = models.ForeignKey(Regiao, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_pendentes")
    parceiro = models.ForeignKey("Parceiro", on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_pendentes")
    rota_texto = models.CharField(max_length=200, blank=True, default="")
    regiao_texto = models.CharField(max_length=200, blank=True, default="")
    valor_tonelada_frete_safia = models.CharField(max_length=80, blank=True, default="")
    pendente = models.CharField(max_length=30, blank=True, default="")
    nome_cidade_parceiro_safia = models.CharField(max_length=150, blank=True, default="")
    previsao_entrega = models.DateField(null=True, blank=True)
    dt_neg = models.DateField(null=True, blank=True)
    prazo_maximo = models.PositiveSmallIntegerField(default=3)
    tipo_venda = models.CharField(max_length=80, blank=True, default="")
    nome_empresa = models.CharField(max_length=220, blank=True, default="")
    cod_nome_parceiro = models.CharField(max_length=220, blank=True, default="")
    vlr_nota = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    peso_bruto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    peso = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    peso_liq_itens = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    apelido_vendedor = models.CharField(max_length=150, blank=True, default="")
    gerente = models.CharField(max_length=150, blank=True, default="")
    data_para_calculo = models.DateField(null=True, blank=True)
    descricao_tipo_negociacao = models.CharField(max_length=220, blank=True, default="")
    nro_nota = models.BigIntegerField(default=0)

    def __str__(self):
        return f"Pedido Pendente {self.numero_unico}"

    @property
    def dias_negociados(self):
        data_base = self.data_para_calculo or self.previsao_entrega or self.dt_neg
        if not data_base:
            return None
        return (timezone.localdate() - data_base).days

    @property
    def status_dias_negociados(self):
        if self.dias_negociados is None:
            return ""
        saldo = int(self.prazo_maximo or 0) - int(self.dias_negociados or 0)
        if saldo < 0:
            return "Atrasado"
        if saldo == 0:
            return "Atenção"
        return "No Prazo"

    @classmethod
    def criar_pedido_pendente(
        cls,
        empresa,
        numero_unico,
        rota=None,
        regiao=None,
        parceiro=None,
        rota_texto="",
        regiao_texto="",
        valor_tonelada_frete_safia="",
        pendente="",
        nome_cidade_parceiro_safia="",
        previsao_entrega=None,
        dt_neg=None,
        prazo_maximo=3,
        tipo_venda="",
        nome_empresa="",
        cod_nome_parceiro="",
        vlr_nota=0,
        peso_bruto=0,
        peso=0,
        peso_liq_itens=0,
        apelido_vendedor="",
        gerente="",
        data_para_calculo=None,
        descricao_tipo_negociacao="",
        nro_nota=0,
    ):
        item = cls(
            empresa=empresa,
            numero_unico=numero_unico,
            rota=rota,
            regiao=regiao,
            parceiro=parceiro,
            rota_texto=rota_texto,
            regiao_texto=regiao_texto,
            valor_tonelada_frete_safia=valor_tonelada_frete_safia,
            pendente=pendente,
            nome_cidade_parceiro_safia=nome_cidade_parceiro_safia,
            previsao_entrega=previsao_entrega,
            dt_neg=dt_neg,
            prazo_maximo=prazo_maximo,
            tipo_venda=tipo_venda,
            nome_empresa=nome_empresa,
            cod_nome_parceiro=cod_nome_parceiro,
            vlr_nota=vlr_nota,
            peso_bruto=peso_bruto,
            peso=peso,
            peso_liq_itens=peso_liq_itens,
            apelido_vendedor=apelido_vendedor,
            gerente=gerente,
            data_para_calculo=data_para_calculo,
            descricao_tipo_negociacao=descricao_tipo_negociacao,
            nro_nota=nro_nota,
        )
        item.save()
        return item

    @classmethod
    def listar_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_pedido_pendente(
        self,
        numero_unico=UNSET,
        rota=UNSET,
        regiao=UNSET,
        parceiro=UNSET,
        rota_texto=UNSET,
        regiao_texto=UNSET,
        valor_tonelada_frete_safia=UNSET,
        pendente=UNSET,
        nome_cidade_parceiro_safia=UNSET,
        previsao_entrega=UNSET,
        dt_neg=UNSET,
        prazo_maximo=UNSET,
        tipo_venda=UNSET,
        nome_empresa=UNSET,
        cod_nome_parceiro=UNSET,
        vlr_nota=UNSET,
        peso_bruto=UNSET,
        peso=UNSET,
        peso_liq_itens=UNSET,
        apelido_vendedor=UNSET,
        gerente=UNSET,
        data_para_calculo=UNSET,
        descricao_tipo_negociacao=UNSET,
        nro_nota=UNSET,
    ):
        if numero_unico is not UNSET:
            self.numero_unico = numero_unico
        if rota is not UNSET:
            self.rota = rota
        if regiao is not UNSET:
            self.regiao = regiao
        if parceiro is not UNSET:
            self.parceiro = parceiro
        if rota_texto is not UNSET:
            self.rota_texto = rota_texto
        if regiao_texto is not UNSET:
            self.regiao_texto = regiao_texto
        if valor_tonelada_frete_safia is not UNSET:
            self.valor_tonelada_frete_safia = valor_tonelada_frete_safia
        if pendente is not UNSET:
            self.pendente = pendente
        if nome_cidade_parceiro_safia is not UNSET:
            self.nome_cidade_parceiro_safia = nome_cidade_parceiro_safia
        if previsao_entrega is not UNSET:
            self.previsao_entrega = previsao_entrega
        if dt_neg is not UNSET:
            self.dt_neg = dt_neg
        if prazo_maximo is not UNSET:
            self.prazo_maximo = prazo_maximo
        if tipo_venda is not UNSET:
            self.tipo_venda = tipo_venda
        if nome_empresa is not UNSET:
            self.nome_empresa = nome_empresa
        if cod_nome_parceiro is not UNSET:
            self.cod_nome_parceiro = cod_nome_parceiro
        if vlr_nota is not UNSET:
            self.vlr_nota = vlr_nota
        if peso_bruto is not UNSET:
            self.peso_bruto = peso_bruto
        if peso is not UNSET:
            self.peso = peso
        if peso_liq_itens is not UNSET:
            self.peso_liq_itens = peso_liq_itens
        if apelido_vendedor is not UNSET:
            self.apelido_vendedor = apelido_vendedor
        if gerente is not UNSET:
            self.gerente = gerente
        if data_para_calculo is not UNSET:
            self.data_para_calculo = data_para_calculo
        if descricao_tipo_negociacao is not UNSET:
            self.descricao_tipo_negociacao = descricao_tipo_negociacao
        if nro_nota is not UNSET:
            self.nro_nota = nro_nota
        self.save()

    def excluir_pedido_pendente(self):
        self.delete()


class ControleMargem(models.Model):
    SITUACAO_AMARELO = "AMARELO"
    SITUACAO_ROXO = "ROXO"
    SITUACAO_VERDE = "VERDE"
    SITUACAO_VERMELHO = "VERMELHO"
    SITUACAO_CHOICES = [
        (SITUACAO_AMARELO, "Amarelo"),
        (SITUACAO_ROXO, "Roxo"),
        (SITUACAO_VERDE, "Verde"),
        (SITUACAO_VERMELHO, "Vermelho"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="controles_margem")
    data_origem = models.CharField(max_length=120, blank=True, default="")

    nro_unico = models.BigIntegerField(db_index=True)
    nome_empresa = models.CharField(max_length=220, blank=True, default="")

    parceiro = models.ForeignKey(
        "Parceiro",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="controles_margem",
    )
    cod_nome_parceiro = models.CharField(max_length=220, blank=True, default="")

    descricao_perfil = models.CharField(max_length=220, null=True, blank=True)
    apelido_vendedor = models.CharField(max_length=150, null=True, blank=True)
    gerente = models.CharField(max_length=150, null=True, blank=True)

    dt_neg = models.DateField(null=True, blank=True)
    previsao_entrega = models.DateField(null=True, blank=True)
    tipo_venda = models.CharField(max_length=80, null=True, blank=True)

    vlr_nota = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    custo_total_produto = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    margem_bruta = models.DecimalField(max_digits=16, decimal_places=9, default=0)
    lucro_bruto = models.DecimalField(max_digits=16, decimal_places=6, default=0)

    valor_tonelada_frete_safia = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    peso_bruto = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    custo_por_kg = models.DecimalField(max_digits=16, decimal_places=9, default=0)

    vendas = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    producao = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    operador_logistica = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    frete_distribuicao = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    total_logistica = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    administracao = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    financeiro = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    total_setores = models.DecimalField(max_digits=16, decimal_places=6, default=0)

    valor_liquido = models.DecimalField(max_digits=16, decimal_places=6, default=0)
    margem_liquida = models.DecimalField(max_digits=16, decimal_places=9, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nro_unico"], name="uq_controle_margem_empresa_nro_unico"),
        ]

    def __str__(self):
        return f"Controle Margem #{self.nro_unico} - {self.empresa.nome}"

    @property
    def situacao(self):
        valor = self.margem_bruta if self.margem_bruta is not None else Decimal("0")
        if valor < Decimal("0"):
            return self.SITUACAO_ROXO
        if valor < Decimal("0.10"):
            return self.SITUACAO_ROXO
        if valor < Decimal("0.12"):
            return self.SITUACAO_VERMELHO
        if valor < Decimal("0.14"):
            return self.SITUACAO_AMARELO
        return self.SITUACAO_VERDE

    @classmethod
    def criar_controle_margem(
        cls,
        empresa,
        nro_unico,
        data_origem="",
        nome_empresa="",
        parceiro=None,
        cod_nome_parceiro="",
        descricao_perfil=None,
        apelido_vendedor=None,
        gerente=None,
        dt_neg=None,
        previsao_entrega=None,
        tipo_venda=None,
        vlr_nota=0,
        custo_total_produto=0,
        margem_bruta=0,
        lucro_bruto=0,
        valor_tonelada_frete_safia=0,
        peso_bruto=0,
        custo_por_kg=0,
        vendas=0,
        producao=0,
        operador_logistica=0,
        frete_distribuicao=0,
        total_logistica=0,
        administracao=0,
        financeiro=0,
        total_setores=0,
        valor_liquido=0,
        margem_liquida=0,
    ):
        item = cls(
            empresa=empresa,
            data_origem=data_origem,
            nro_unico=nro_unico,
            nome_empresa=nome_empresa,
            parceiro=parceiro,
            cod_nome_parceiro=cod_nome_parceiro,
            descricao_perfil=descricao_perfil,
            apelido_vendedor=apelido_vendedor,
            gerente=gerente,
            dt_neg=dt_neg,
            previsao_entrega=previsao_entrega,
            tipo_venda=tipo_venda,
            vlr_nota=vlr_nota,
            custo_total_produto=custo_total_produto,
            margem_bruta=margem_bruta,
            lucro_bruto=lucro_bruto,
            valor_tonelada_frete_safia=valor_tonelada_frete_safia,
            peso_bruto=peso_bruto,
            custo_por_kg=custo_por_kg,
            vendas=vendas,
            producao=producao,
            operador_logistica=operador_logistica,
            frete_distribuicao=frete_distribuicao,
            total_logistica=total_logistica,
            administracao=administracao,
            financeiro=financeiro,
            total_setores=total_setores,
            valor_liquido=valor_liquido,
            margem_liquida=margem_liquida,
        )
        item.save()
        return item

    @classmethod
    def listar_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_controle_margem(
        self,
        data_origem=UNSET,
        nro_unico=UNSET,
        nome_empresa=UNSET,
        parceiro=UNSET,
        cod_nome_parceiro=UNSET,
        descricao_perfil=UNSET,
        apelido_vendedor=UNSET,
        gerente=UNSET,
        dt_neg=UNSET,
        previsao_entrega=UNSET,
        tipo_venda=UNSET,
        vlr_nota=UNSET,
        custo_total_produto=UNSET,
        margem_bruta=UNSET,
        lucro_bruto=UNSET,
        valor_tonelada_frete_safia=UNSET,
        peso_bruto=UNSET,
        custo_por_kg=UNSET,
        vendas=UNSET,
        producao=UNSET,
        operador_logistica=UNSET,
        frete_distribuicao=UNSET,
        total_logistica=UNSET,
        administracao=UNSET,
        financeiro=UNSET,
        total_setores=UNSET,
        valor_liquido=UNSET,
        margem_liquida=UNSET,
    ):
        if data_origem is not UNSET:
            self.data_origem = data_origem
        if nro_unico is not UNSET:
            self.nro_unico = nro_unico
        if nome_empresa is not UNSET:
            self.nome_empresa = nome_empresa
        if parceiro is not UNSET:
            self.parceiro = parceiro
        if cod_nome_parceiro is not UNSET:
            self.cod_nome_parceiro = cod_nome_parceiro
        if descricao_perfil is not UNSET:
            self.descricao_perfil = descricao_perfil
        if apelido_vendedor is not UNSET:
            self.apelido_vendedor = apelido_vendedor
        if gerente is not UNSET:
            self.gerente = gerente
        if dt_neg is not UNSET:
            self.dt_neg = dt_neg
        if previsao_entrega is not UNSET:
            self.previsao_entrega = previsao_entrega
        if tipo_venda is not UNSET:
            self.tipo_venda = tipo_venda
        if vlr_nota is not UNSET:
            self.vlr_nota = vlr_nota
        if custo_total_produto is not UNSET:
            self.custo_total_produto = custo_total_produto
        if margem_bruta is not UNSET:
            self.margem_bruta = margem_bruta
        if lucro_bruto is not UNSET:
            self.lucro_bruto = lucro_bruto
        if valor_tonelada_frete_safia is not UNSET:
            self.valor_tonelada_frete_safia = valor_tonelada_frete_safia
        if peso_bruto is not UNSET:
            self.peso_bruto = peso_bruto
        if custo_por_kg is not UNSET:
            self.custo_por_kg = custo_por_kg
        if vendas is not UNSET:
            self.vendas = vendas
        if producao is not UNSET:
            self.producao = producao
        if operador_logistica is not UNSET:
            self.operador_logistica = operador_logistica
        if frete_distribuicao is not UNSET:
            self.frete_distribuicao = frete_distribuicao
        if total_logistica is not UNSET:
            self.total_logistica = total_logistica
        if administracao is not UNSET:
            self.administracao = administracao
        if financeiro is not UNSET:
            self.financeiro = financeiro
        if total_setores is not UNSET:
            self.total_setores = total_setores
        if valor_liquido is not UNSET:
            self.valor_liquido = valor_liquido
        if margem_liquida is not UNSET:
            self.margem_liquida = margem_liquida
        self.save()

    def excluir_controle_margem(self):
        self.delete()


class ParametroMargemVendas(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="parametros_margem_vendas")
    parametro = models.CharField(max_length=80, default="Vendas")
    criterio = models.CharField(max_length=120, default="Geral")
    remuneracao_percentual = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    def __str__(self):
        return f"Parametro Vendas - {self.empresa.nome}"


class ParametroMargemLogistica(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="parametros_margem_logistica")
    parametro = models.CharField(max_length=80, default="Operador Logistico")
    criterio = models.CharField(max_length=120, default="Entrega+Balcao")
    remuneracao_rs = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    def __str__(self):
        return f"Parametro Logistica - {self.empresa.nome}"


class ParametroMargemAdministracao(models.Model):
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name="parametro_margem_administracao")
    parametro = models.CharField(max_length=80, default="Administracao")
    remuneracao_percentual = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    def __str__(self):
        return f"Parametro Administracao - {self.empresa.nome}"


class ParametroMargemFinanceiro(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="parametros_margem_financeiro")
    parametro = models.CharField(max_length=80, default="Contas a Receber")
    taxa_ao_mes = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    remuneracao_percentual = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    def __str__(self):
        return f"Parametro Financeiro - {self.empresa.nome}"


class Parceiro(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="parceiros")
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True, blank=True, related_name="parceiros")
    nome = models.CharField(max_length=150)
    codigo = models.CharField(max_length=50)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], name="uq_parceiro_empresa_codigo"),
        ]

    def __str__(self):
        return f"{self.nome} ({self.codigo})"
    
    @classmethod
    def criar_parceiro(cls, nome, codigo, empresa, cidade=None):
        parceiro = cls(nome=nome, codigo=codigo, empresa=empresa, cidade=cidade)
        parceiro.save()
        return parceiro
    
    @classmethod
    def listar_parceiros_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    @classmethod
    def obter_ou_criar_por_codigo_nome(cls, empresa, codigo, nome):
        defaults = {"nome": nome}
        parceiro, created = cls.objects.get_or_create(
            empresa=empresa,
            codigo=codigo,
            defaults=defaults,
        )
        if not created and nome and parceiro.nome != nome:
            parceiro.nome = nome
            parceiro.save(update_fields=["nome"])
        return parceiro

    def atualizar_parceiro(self, novo_nome=None, novo_codigo=None, cidade=UNSET):
        if novo_nome:
            self.nome = novo_nome
        if novo_codigo:
            self.codigo = novo_codigo
        if cidade is not UNSET:
            self.cidade = cidade
        self.save()

    def excluir_parceiro(self):
        self.delete()

class Carteira(models.Model):
    empresa = models.ForeignKey( Empresa, on_delete=models.CASCADE, related_name="carteiras")
    regiao = models.ForeignKey(Regiao, on_delete=models.SET_NULL, null=True, blank=True)
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True, blank=True)
    parceiro = models.ForeignKey(Parceiro, on_delete=models.SET_NULL, null=True, blank=True, related_name="carteiras")
    valor_faturado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    limite_credito = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ultima_venda = models.DateField(null=True, blank=True)
    qtd_dias_sem_venda = models.PositiveIntegerField(default=0)
    intervalo = models.CharField(max_length=20, blank=True, default="")
    data_cadastro = models.DateField(default=timezone.localdate)
    gerente = models.CharField(max_length=150, blank=True, default="")
    vendedor = models.CharField(max_length=150, blank=True, default="")
    descricao_perfil = models.CharField(max_length=200, blank=True, default="")
    ativo_indicador = models.BooleanField(default=True)
    cliente_indicador = models.BooleanField(default=False)
    fornecedor_indicador = models.BooleanField(default=False)
    transporte_indicador = models.BooleanField(default=False)

    INTERVALO_0_5 = "0 a 5"
    INTERVALO_6_30 = "6 a 30"
    INTERVALO_31_60 = "31 a 60"
    INTERVALO_61_90 = "61 a 90"
    INTERVALO_91_120 = "91 a 120"
    INTERVALO_121_180 = "121 a 180"
    INTERVALO_180_MAIS = "180+"
    INTERVALO_SEM_VENDA = "Sem venda"

    def __str__(self):
        parceiro_nome = self.parceiro.nome if self.parceiro else "Sem parceiro"
        return f"Carteira #{self.id} - {parceiro_nome}"

    @property
    def dias_sem_venda(self):
        if not self.ultima_venda:
            return self.INTERVALO_SEM_VENDA
        dias = (timezone.localdate() - self.ultima_venda).days
        return max(0, int(dias))

    @property
    def intervalo_calculado(self):
        dias = self.dias_sem_venda
        if isinstance(dias, str):
            return self.INTERVALO_SEM_VENDA
        if dias <= 5:
            return self.INTERVALO_0_5
        if dias <= 30:
            return self.INTERVALO_6_30
        if dias <= 60:
            return self.INTERVALO_31_60
        if dias <= 90:
            return self.INTERVALO_61_90
        if dias <= 120:
            return self.INTERVALO_91_120
        if dias <= 180:
            return self.INTERVALO_121_180
        return self.INTERVALO_180_MAIS

    @property
    def Intervalo(self):
        return self.intervalo_calculado

    def _sincronizar_campos_dias_intervalo(self):
        dias = self.dias_sem_venda
        self.qtd_dias_sem_venda = 0 if isinstance(dias, str) else int(dias)
        self.intervalo = self.intervalo_calculado

    def save(self, *args, **kwargs):
        self._sincronizar_campos_dias_intervalo()
        return super().save(*args, **kwargs)
    
    @classmethod
    def criar_carteira(
        cls,
        empresa,
        regiao=None,
        cidade=None,
        parceiro=None,
        valor_faturado=0,
        limite_credito=0,
        ultima_venda=None,
        qtd_dias_sem_venda=0,
        intervalo="",
        data_cadastro=None,
        gerente=None,
        vendedor="",
        descricao_perfil="",
        ativo_indicador=True,
        cliente_indicador=False,
        fornecedor_indicador=False,
        transporte_indicador=False
    ):
        carteira = cls(
            empresa=empresa,
            regiao=regiao,
            cidade=cidade,
            parceiro=parceiro,
            valor_faturado=valor_faturado,
            limite_credito=limite_credito,
            ultima_venda=ultima_venda,
            qtd_dias_sem_venda=qtd_dias_sem_venda,
            intervalo=intervalo,
            data_cadastro=data_cadastro or timezone.localdate(),
            gerente=gerente,
            vendedor=vendedor,
            descricao_perfil=descricao_perfil,
            ativo_indicador=ativo_indicador,
            cliente_indicador=cliente_indicador,
            fornecedor_indicador=fornecedor_indicador,
            transporte_indicador=transporte_indicador
        )
        carteira.save()
        return carteira
    
    @classmethod
    def listar_carteiras_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_carteira(
        self,
        regiao=UNSET,
        cidade=UNSET,
        parceiro=UNSET,
        valor_faturado=UNSET,
        limite_credito=UNSET,
        ultima_venda=UNSET,
        qtd_dias_sem_venda=UNSET,
        intervalo=UNSET,
        data_cadastro=UNSET,
        gerente=UNSET,
        vendedor=UNSET,
        descricao_perfil=UNSET,
        ativo_indicador=UNSET,
        cliente_indicador=UNSET,
        fornecedor_indicador=UNSET,
        transporte_indicador=UNSET,
    ):
        if regiao is not UNSET:
            self.regiao = regiao
        if cidade is not UNSET:
            self.cidade = cidade
        if parceiro is not UNSET:
            self.parceiro = parceiro
        if valor_faturado is not UNSET:
            self.valor_faturado = valor_faturado
        if limite_credito is not UNSET:
            self.limite_credito = limite_credito
        if ultima_venda is not UNSET:
            self.ultima_venda = ultima_venda
        if qtd_dias_sem_venda is not UNSET:
            self.qtd_dias_sem_venda = qtd_dias_sem_venda
        if intervalo is not UNSET:
            self.intervalo = intervalo
        if data_cadastro is not UNSET:
            self.data_cadastro = data_cadastro
        if gerente is not UNSET:
            self.gerente = gerente
        if vendedor is not UNSET:
            self.vendedor = vendedor
        if descricao_perfil is not UNSET:
            self.descricao_perfil = descricao_perfil
        if ativo_indicador is not UNSET:
            self.ativo_indicador = ativo_indicador
        if cliente_indicador is not UNSET:
            self.cliente_indicador = cliente_indicador
        if fornecedor_indicador is not UNSET:
            self.fornecedor_indicador = fornecedor_indicador
        if transporte_indicador is not UNSET:
            self.transporte_indicador = transporte_indicador
        self.save()

    def excluir_carteira(self):
        self.delete()

class Venda(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="vendas")
    codigo = models.CharField(max_length=50)
    descricao = models.CharField(max_length=200, default="")
    valor_venda = models.DecimalField(max_digits=10, decimal_places=2)
    qtd_notas = models.PositiveIntegerField()
    custo_medio_icms_cmv = models.DecimalField(max_digits=10, decimal_places=2)
    lucro = models.DecimalField(max_digits=10, decimal_places=2)
    peso_bruto = models.DecimalField(max_digits=10, decimal_places=2)
    peso_liquido = models.DecimalField(max_digits=10, decimal_places=2)
    margem = models.DecimalField(max_digits=5, decimal_places=2)
    data_venda = models.DateField(default=timezone.localdate)

    def __str__(self):
        return f"Venda #{self.codigo} - {self.empresa.nome}"
    
    @classmethod
    def criar_venda(
        cls,
        empresa,
        codigo,
        descricao,
        valor_venda,
        qtd_notas,
        custo_medio_icms_cmv,
        peso_bruto,
        peso_liquido,
        data_venda=None
    ):
        lucro = _definir_lucro(valor_venda, custo_medio_icms_cmv)
        margem = _definir_margem(lucro, valor_venda)
        venda = cls(
            empresa=empresa,
            codigo=codigo,
            descricao=descricao,
            valor_venda=valor_venda,
            qtd_notas=qtd_notas,
            custo_medio_icms_cmv=custo_medio_icms_cmv,
            lucro=lucro,
            peso_bruto=peso_bruto,
            peso_liquido=peso_liquido,
            margem=margem,
            data_venda=data_venda or timezone.localdate()
        )
        venda.save()
        return venda
    
    @classmethod
    def listar_vendas_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)
    
    def atualizar_venda(
        self,
        codigo=UNSET,
        descricao=UNSET,
        valor_venda=UNSET,
        qtd_notas=UNSET,
        custo_medio_icms_cmv=UNSET,
        peso_bruto=UNSET,
        peso_liquido=UNSET,
        data_venda=UNSET
    ):
        if codigo is not UNSET:
            self.codigo = codigo
        if descricao is not UNSET:
            self.descricao = descricao
        if valor_venda is not UNSET:
            self.valor_venda = valor_venda
        if qtd_notas is not UNSET:
            self.qtd_notas = qtd_notas
        if custo_medio_icms_cmv is not UNSET:
            self.custo_medio_icms_cmv = custo_medio_icms_cmv
        if peso_bruto is not UNSET:
            self.peso_bruto = peso_bruto
        if peso_liquido is not UNSET:
            self.peso_liquido = peso_liquido
        if data_venda is not UNSET:
            self.data_venda = data_venda
        
        # Recalcular lucro e margem se valor_venda ou custo_medio_icms_cmv foram atualizados
        if valor_venda is not UNSET or custo_medio_icms_cmv is not UNSET:
            self.lucro = _definir_lucro(self.valor_venda, self.custo_medio_icms_cmv)
            self.margem = _definir_margem(self.lucro, self.valor_venda)
        
        self.save()
    
    def excluir_venda(self):
        self.delete()

class Cargas(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="cargas")
    situacao = models.CharField(max_length=20)
    ordem_de_carga_codigo = models.CharField(max_length=50)
    data_inicio = models.DateField()
    data_prevista_saida = models.DateField()
    data_chegada = models.DateField(null=True, blank=True)
    data_finalizacao = models.DateField(null=True, blank=True)
    nome_motorista = models.CharField(max_length=150, blank=True, default="")
    nome_fantasia_empresa = models.CharField(max_length=150)
    regiao = models.ForeignKey(Regiao, on_delete=models.SET_NULL, null=True, blank=True)
    prazo_maximo_dias = models.PositiveIntegerField(default=10)

    def __str__(self):
        return f"Carga #{self.ordem_de_carga_codigo} - {self.nome_fantasia_empresa}"

    def _calcular_idade_dias(self):
        hoje = timezone.localdate()
        if not self.data_inicio:
            return 0
        return max(0, (hoje - self.data_inicio).days)

    @property
    def idade_dias(self):
        return self._calcular_idade_dias()

    @property
    def critica(self):
        return self.idade_dias - int(self.prazo_maximo_dias or 0)

    @property
    def verificacao(self):
        return self.critica > 0

    @classmethod
    def criar_carga(
        cls,
        empresa,
        situacao,
        ordem_de_carga_codigo,
        data_inicio,
        data_prevista_saida,
        data_chegada=None,
        data_finalizacao=None,
        nome_motorista="",
        nome_fantasia_empresa="",
        regiao=None,
        prazo_maximo_dias=10,
    ):
        carga = cls(
            empresa=empresa,
            situacao=situacao,
            ordem_de_carga_codigo=ordem_de_carga_codigo,
            data_inicio=data_inicio,
            data_prevista_saida=data_prevista_saida,
            data_chegada=data_chegada,
            data_finalizacao=data_finalizacao,
            nome_motorista=nome_motorista,
            nome_fantasia_empresa=nome_fantasia_empresa,
            regiao=regiao,
            prazo_maximo_dias=prazo_maximo_dias,
        )
        carga.save()
        return carga

    @classmethod
    def listar_cargas_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_carga(
        self,
        situacao=UNSET,
        ordem_de_carga_codigo=UNSET,
        data_inicio=UNSET,
        data_prevista_saida=UNSET,
        data_chegada=UNSET,
        data_finalizacao=UNSET,
        nome_motorista=UNSET,
        nome_fantasia_empresa=UNSET,
        regiao=UNSET,
        prazo_maximo_dias=UNSET,
    ):
        if situacao is not UNSET:
            self.situacao = situacao
        if ordem_de_carga_codigo is not UNSET:
            self.ordem_de_carga_codigo = ordem_de_carga_codigo
        if data_inicio is not UNSET:
            self.data_inicio = data_inicio
        if data_prevista_saida is not UNSET:
            self.data_prevista_saida = data_prevista_saida
        if data_chegada is not UNSET:
            self.data_chegada = data_chegada
        if data_finalizacao is not UNSET:
            self.data_finalizacao = data_finalizacao
        if nome_motorista is not UNSET:
            self.nome_motorista = nome_motorista
        if nome_fantasia_empresa is not UNSET:
            self.nome_fantasia_empresa = nome_fantasia_empresa
        if regiao is not UNSET:
            self.regiao = regiao
        if prazo_maximo_dias is not UNSET:
            self.prazo_maximo_dias = prazo_maximo_dias
        self.save()

    def excluir_carga(self):
        self.delete()

class Produto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="produtos")
    codigo_produto = models.CharField(max_length=80)
    status = models.CharField(max_length=20, blank=True, default="Ativo")
    descricao_produto = models.CharField(max_length=255, blank=True, default="")
    kg = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    remuneracao_por_fardo = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    ppm = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    peso_kg = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    pacote_por_fardo = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    turno = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    horas = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    setup = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    horas_uteis = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    empacotadeiras = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    producao_por_dia_fd = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    estoque_minimo_pacote = models.DecimalField(max_digits=18, decimal_places=3, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo_produto"], name="uq_produto_empresa_codigo"),
        ]

    def __str__(self):
        return f"{self.codigo_produto} - {self.descricao_produto}"

    @classmethod
    def criar_produto(
        cls,
        empresa,
        codigo_produto,
        descricao_produto="",
        status="Ativo",
        kg=0,
        remuneracao_por_fardo=0,
        ppm=0,
        peso_kg=0,
        pacote_por_fardo=0,
        turno=0,
        horas=0,
        setup=0,
        horas_uteis=0,
        empacotadeiras=0,
        producao_por_dia_fd=0,
        estoque_minimo_pacote=0,
    ):
        item = cls(
            empresa=empresa,
            codigo_produto=codigo_produto,
            descricao_produto=descricao_produto,
            status=status,
            kg=kg,
            remuneracao_por_fardo=remuneracao_por_fardo,
            ppm=ppm,
            peso_kg=peso_kg,
            pacote_por_fardo=pacote_por_fardo,
            turno=turno,
            horas=horas,
            setup=setup,
            horas_uteis=horas_uteis,
            empacotadeiras=empacotadeiras,
            producao_por_dia_fd=producao_por_dia_fd,
            estoque_minimo_pacote=estoque_minimo_pacote,
        )
        item.save()
        return item

    @classmethod
    def listar_produtos_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    @classmethod
    def obter_ou_criar_por_codigo_descricao(cls, empresa, codigo_produto, descricao_produto):
        codigo_produto = (codigo_produto or "").strip()
        descricao_produto = (descricao_produto or "").strip()
        if not codigo_produto:
            return None

        defaults = {"descricao_produto": descricao_produto}
        produto, created = cls.objects.get_or_create(
            empresa=empresa,
            codigo_produto=codigo_produto,
            defaults=defaults,
        )
        if not created and descricao_produto and produto.descricao_produto != descricao_produto:
            produto.descricao_produto = descricao_produto
            produto.save(update_fields=["descricao_produto"])
        return produto

    def atualizar_produto(
        self,
        codigo_produto=UNSET,
        descricao_produto=UNSET,
        status=UNSET,
        kg=UNSET,
        remuneracao_por_fardo=UNSET,
        ppm=UNSET,
        peso_kg=UNSET,
        pacote_por_fardo=UNSET,
        turno=UNSET,
        horas=UNSET,
        setup=UNSET,
        horas_uteis=UNSET,
        empacotadeiras=UNSET,
        producao_por_dia_fd=UNSET,
        estoque_minimo_pacote=UNSET,
    ):
        if codigo_produto is not UNSET:
            self.codigo_produto = codigo_produto
        if descricao_produto is not UNSET:
            self.descricao_produto = descricao_produto
        if status is not UNSET:
            self.status = status
        if kg is not UNSET:
            self.kg = kg
        if remuneracao_por_fardo is not UNSET:
            self.remuneracao_por_fardo = remuneracao_por_fardo
        if ppm is not UNSET:
            self.ppm = ppm
        if peso_kg is not UNSET:
            self.peso_kg = peso_kg
        if pacote_por_fardo is not UNSET:
            self.pacote_por_fardo = pacote_por_fardo
        if turno is not UNSET:
            self.turno = turno
        if horas is not UNSET:
            self.horas = horas
        if setup is not UNSET:
            self.setup = setup
        if horas_uteis is not UNSET:
            self.horas_uteis = horas_uteis
        if empacotadeiras is not UNSET:
            self.empacotadeiras = empacotadeiras
        if producao_por_dia_fd is not UNSET:
            self.producao_por_dia_fd = producao_por_dia_fd
        if estoque_minimo_pacote is not UNSET:
            self.estoque_minimo_pacote = estoque_minimo_pacote
        self.save()

    def excluir_produto(self):
        self.delete()

class Producao(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="producoes")
    data_origem = models.CharField(max_length=255, blank=True, default="")
    numero_operacao = models.PositiveIntegerField()
    situacao = models.CharField(max_length=100, blank=True, default="")
    produto = models.ForeignKey(Produto, on_delete=models.SET_NULL, null=True, blank=True, related_name="producoes")
    tamanho_lote = models.CharField(max_length=80, blank=True, default="")
    numero_lote = models.CharField(max_length=80, blank=True, default="")
    data_hora_entrada_atividade = models.DateTimeField(null=True, blank=True)
    data_hora_aceite_atividade = models.DateTimeField(null=True, blank=True)
    data_hora_inicio_atividade = models.DateTimeField(null=True, blank=True)
    data_hora_fim_atividade = models.DateTimeField(null=True, blank=True)
    kg = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    producao_por_dia = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    kg_por_lote = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    estoque_minimo_pacote = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    def __str__(self):
        return f"Producao #{self.id} - Operacao {self.numero_operacao}"

    @classmethod
    def criar_producao(
        cls,
        empresa,
        data_origem="",
        numero_operacao=0,
        situacao="",
        produto=None,
        tamanho_lote="",
        numero_lote="",
        data_hora_entrada_atividade=None,
        data_hora_aceite_atividade=None,
        data_hora_inicio_atividade=None,
        data_hora_fim_atividade=None,
        kg=0,
        producao_por_dia=0,
        kg_por_lote=0,
        estoque_minimo_pacote=0,
    ):
        item = cls(
            empresa=empresa,
            data_origem=data_origem,
            numero_operacao=numero_operacao,
            situacao=situacao,
            produto=produto,
            tamanho_lote=tamanho_lote,
            numero_lote=numero_lote,
            data_hora_entrada_atividade=data_hora_entrada_atividade,
            data_hora_aceite_atividade=data_hora_aceite_atividade,
            data_hora_inicio_atividade=data_hora_inicio_atividade,
            data_hora_fim_atividade=data_hora_fim_atividade,
            kg=kg,
            producao_por_dia=producao_por_dia,
            kg_por_lote=kg_por_lote,
            estoque_minimo_pacote=estoque_minimo_pacote,
        )
        item.save()
        return item

    @classmethod
    def listar_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_producao(
        self,
        data_origem=UNSET,
        numero_operacao=UNSET,
        situacao=UNSET,
        produto=UNSET,
        tamanho_lote=UNSET,
        numero_lote=UNSET,
        data_hora_entrada_atividade=UNSET,
        data_hora_aceite_atividade=UNSET,
        data_hora_inicio_atividade=UNSET,
        data_hora_fim_atividade=UNSET,
        kg=UNSET,
        producao_por_dia=UNSET,
        kg_por_lote=UNSET,
        estoque_minimo_pacote=UNSET,
    ):
        if data_origem is not UNSET:
            self.data_origem = data_origem
        if numero_operacao is not UNSET:
            self.numero_operacao = numero_operacao
        if situacao is not UNSET:
            self.situacao = situacao
        if produto is not UNSET:
            self.produto = produto
        if tamanho_lote is not UNSET:
            self.tamanho_lote = tamanho_lote
        if numero_lote is not UNSET:
            self.numero_lote = numero_lote
        if data_hora_entrada_atividade is not UNSET:
            self.data_hora_entrada_atividade = data_hora_entrada_atividade
        if data_hora_aceite_atividade is not UNSET:
            self.data_hora_aceite_atividade = data_hora_aceite_atividade
        if data_hora_inicio_atividade is not UNSET:
            self.data_hora_inicio_atividade = data_hora_inicio_atividade
        if data_hora_fim_atividade is not UNSET:
            self.data_hora_fim_atividade = data_hora_fim_atividade
        if kg is not UNSET:
            self.kg = kg
        if producao_por_dia is not UNSET:
            self.producao_por_dia = producao_por_dia
        if kg_por_lote is not UNSET:
            self.kg_por_lote = kg_por_lote
        if estoque_minimo_pacote is not UNSET:
            self.estoque_minimo_pacote = estoque_minimo_pacote
        self.save()

    def excluir_producao(self):
        self.delete()


class Frete(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="fretes")
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True, blank=True, related_name="fretes")
    unidade_federativa = models.ForeignKey(
        UnidadeFederativa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fretes",
    )
    regiao = models.ForeignKey(Regiao, on_delete=models.SET_NULL, null=True, blank=True, related_name="fretes")
    valor_frete_comercial = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    data_hora_alteracao = models.DateTimeField(null=True, blank=True)
    valor_frete_minimo = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_frete_tonelada = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tipo_frete = models.CharField(max_length=30, blank=True, default="")
    valor_frete_por_km = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    valor_taxa_entrada = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    venda_minima = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "cidade"], name="uq_frete_empresa_cidade"),
        ]

    def __str__(self):
        cidade_nome = self.cidade.nome if self.cidade else "-"
        return f"Frete {cidade_nome} - {self.empresa.nome}"

    @classmethod
    def criar_frete(
        cls,
        empresa,
        cidade=None,
        unidade_federativa=None,
        regiao=None,
        valor_frete_comercial=0,
        data_hora_alteracao=None,
        valor_frete_minimo=0,
        valor_frete_tonelada=0,
        tipo_frete="",
        valor_frete_por_km=0,
        valor_taxa_entrada=0,
        venda_minima=0,
    ):
        item = cls(
            empresa=empresa,
            cidade=cidade,
            unidade_federativa=unidade_federativa,
            regiao=regiao,
            valor_frete_comercial=valor_frete_comercial,
            data_hora_alteracao=data_hora_alteracao,
            valor_frete_minimo=valor_frete_minimo,
            valor_frete_tonelada=valor_frete_tonelada,
            tipo_frete=tipo_frete,
            valor_frete_por_km=valor_frete_por_km,
            valor_taxa_entrada=valor_taxa_entrada,
            venda_minima=venda_minima,
        )
        item.save()
        return item

    @classmethod
    def listar_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_frete(
        self,
        cidade=UNSET,
        unidade_federativa=UNSET,
        regiao=UNSET,
        valor_frete_comercial=UNSET,
        data_hora_alteracao=UNSET,
        valor_frete_minimo=UNSET,
        valor_frete_tonelada=UNSET,
        tipo_frete=UNSET,
        valor_frete_por_km=UNSET,
        valor_taxa_entrada=UNSET,
        venda_minima=UNSET,
    ):
        if cidade is not UNSET:
            self.cidade = cidade
        if unidade_federativa is not UNSET:
            self.unidade_federativa = unidade_federativa
        if regiao is not UNSET:
            self.regiao = regiao
        if valor_frete_comercial is not UNSET:
            self.valor_frete_comercial = valor_frete_comercial
        if data_hora_alteracao is not UNSET:
            self.data_hora_alteracao = data_hora_alteracao
        if valor_frete_minimo is not UNSET:
            self.valor_frete_minimo = valor_frete_minimo
        if valor_frete_tonelada is not UNSET:
            self.valor_frete_tonelada = valor_frete_tonelada
        if tipo_frete is not UNSET:
            self.tipo_frete = tipo_frete
        if valor_frete_por_km is not UNSET:
            self.valor_frete_por_km = valor_frete_por_km
        if valor_taxa_entrada is not UNSET:
            self.valor_taxa_entrada = valor_taxa_entrada
        if venda_minima is not UNSET:
            self.venda_minima = venda_minima
        self.save()

    def excluir_frete(self):
        self.delete()


class Estoque(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="estoques")
    nome_origem = models.DateField()
    data_contagem = models.DateField()
    status = models.CharField(max_length=30, blank=True, default="Ativo")
    codigo_empresa = models.CharField(max_length=20, blank=True, default="")
    produto = models.ForeignKey(Produto, on_delete=models.SET_NULL, null=True, blank=True, related_name="estoques")
    qtd_estoque = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    giro_mensal = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    lead_time_fornecimento = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    codigo_volume = models.CharField(max_length=20, blank=True, default="")
    custo_total = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    reservado = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    pacote_por_fardo = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    sub_total_est_pen = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    estoque_minimo = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    producao_por_dia_fd = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    total_pcp_pacote = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    total_pcp_fardo = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    dia_de_producao = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    codigo_local = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "nome_origem", "data_contagem", "codigo_empresa", "codigo_local", "produto"],
                name="uq_estoque_empresa_origem_contagem_local_produto",
            ),
        ]

    def __str__(self):
        produto_codigo = self.produto.codigo_produto if self.produto else "-"
        return f"Estoque {produto_codigo} ({self.nome_origem})"

    @classmethod
    def listar_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    @classmethod
    def criar_estoque(
        cls,
        empresa,
        nome_origem,
        data_contagem,
        status="Ativo",
        codigo_empresa="",
        produto=None,
        qtd_estoque=0,
        giro_mensal=0,
        lead_time_fornecimento=0,
        codigo_volume="",
        custo_total=0,
        reservado=0,
        pacote_por_fardo=0,
        sub_total_est_pen=0,
        estoque_minimo=0,
        producao_por_dia_fd=0,
        total_pcp_pacote=0,
        total_pcp_fardo=0,
        dia_de_producao=0,
        codigo_local="",
    ):
        item = cls(
            empresa=empresa,
            nome_origem=nome_origem,
            data_contagem=data_contagem,
            status=status,
            codigo_empresa=codigo_empresa,
            produto=produto,
            qtd_estoque=qtd_estoque,
            giro_mensal=giro_mensal,
            lead_time_fornecimento=lead_time_fornecimento,
            codigo_volume=codigo_volume,
            custo_total=custo_total,
            reservado=reservado,
            pacote_por_fardo=pacote_por_fardo,
            sub_total_est_pen=sub_total_est_pen,
            estoque_minimo=estoque_minimo,
            producao_por_dia_fd=producao_por_dia_fd,
            total_pcp_pacote=total_pcp_pacote,
            total_pcp_fardo=total_pcp_fardo,
            dia_de_producao=dia_de_producao,
            codigo_local=codigo_local,
        )
        item.save()
        return item

    def atualizar_estoque(
        self,
        nome_origem=UNSET,
        data_contagem=UNSET,
        status=UNSET,
        codigo_empresa=UNSET,
        produto=UNSET,
        qtd_estoque=UNSET,
        giro_mensal=UNSET,
        lead_time_fornecimento=UNSET,
        codigo_volume=UNSET,
        custo_total=UNSET,
        reservado=UNSET,
        pacote_por_fardo=UNSET,
        sub_total_est_pen=UNSET,
        estoque_minimo=UNSET,
        producao_por_dia_fd=UNSET,
        total_pcp_pacote=UNSET,
        total_pcp_fardo=UNSET,
        dia_de_producao=UNSET,
        codigo_local=UNSET,
    ):
        if nome_origem is not UNSET:
            self.nome_origem = nome_origem
        if data_contagem is not UNSET:
            self.data_contagem = data_contagem
        if status is not UNSET:
            self.status = status
        if codigo_empresa is not UNSET:
            self.codigo_empresa = codigo_empresa
        if produto is not UNSET:
            self.produto = produto
        if qtd_estoque is not UNSET:
            self.qtd_estoque = qtd_estoque
        if giro_mensal is not UNSET:
            self.giro_mensal = giro_mensal
        if lead_time_fornecimento is not UNSET:
            self.lead_time_fornecimento = lead_time_fornecimento
        if codigo_volume is not UNSET:
            self.codigo_volume = codigo_volume
        if custo_total is not UNSET:
            self.custo_total = custo_total
        if reservado is not UNSET:
            self.reservado = reservado
        if pacote_por_fardo is not UNSET:
            self.pacote_por_fardo = pacote_por_fardo
        if sub_total_est_pen is not UNSET:
            self.sub_total_est_pen = sub_total_est_pen
        if estoque_minimo is not UNSET:
            self.estoque_minimo = estoque_minimo
        if producao_por_dia_fd is not UNSET:
            self.producao_por_dia_fd = producao_por_dia_fd
        if total_pcp_pacote is not UNSET:
            self.total_pcp_pacote = total_pcp_pacote
        if total_pcp_fardo is not UNSET:
            self.total_pcp_fardo = total_pcp_fardo
        if dia_de_producao is not UNSET:
            self.dia_de_producao = dia_de_producao
        if codigo_local is not UNSET:
            self.codigo_local = codigo_local
        self.save()

    def excluir_estoque(self):
        self.delete()

class Titulo(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="titulos")
    tipo_titulo_codigo = models.CharField(max_length=50)
    descricao = models.CharField(max_length=200, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "tipo_titulo_codigo"], name="uq_titulo_empresa_codigo"),
        ]

    def __str__(self):
        return f"{self.tipo_titulo_codigo} - {self.descricao}"

    @classmethod
    def criar_titulo(cls, empresa, tipo_titulo_codigo, descricao=""):
        titulo = cls(
            empresa=empresa,
            tipo_titulo_codigo=tipo_titulo_codigo,
            descricao=descricao
        )
        titulo.save()
        return titulo
    
    @classmethod
    def listar_titulos_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    @classmethod
    def obter_ou_criar_por_codigo_descricao(cls, empresa, tipo_titulo_codigo, descricao):
        defaults = {"descricao": descricao}
        titulo, created = cls.objects.get_or_create(
            empresa=empresa,
            tipo_titulo_codigo=tipo_titulo_codigo,
            defaults=defaults,
        )
        if not created and descricao and titulo.descricao != descricao:
            titulo.descricao = descricao
            titulo.save(update_fields=["descricao"])
        return titulo
    
    def atualizar_titulo(self, tipo_titulo_codigo=UNSET, descricao=UNSET):
        if tipo_titulo_codigo is not UNSET:
            self.tipo_titulo_codigo = tipo_titulo_codigo
        if descricao is not UNSET:
            self.descricao = descricao
        self.save()

    def excluir_titulo(self):
        self.delete()

class Natureza(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="naturezas")
    codigo = models.CharField(max_length=50)
    descricao = models.CharField(max_length=200, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], name="uq_natureza_empresa_codigo"),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"

    @classmethod
    def criar_natureza(cls, empresa, codigo, descricao=""):
        natureza = cls(
            empresa=empresa,
            codigo=codigo,
            descricao=descricao
        )
        natureza.save()
        return natureza
    
    @classmethod
    def listar_naturezas_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    @classmethod
    def obter_ou_criar_por_codigo_descricao(cls, empresa, codigo, descricao):
        defaults = {"descricao": descricao}
        natureza, created = cls.objects.get_or_create(
            empresa=empresa,
            codigo=codigo,
            defaults=defaults,
        )
        if not created and descricao and natureza.descricao != descricao:
            natureza.descricao = descricao
            natureza.save(update_fields=["descricao"])
        return natureza
    
    def atualizar_natureza(self, codigo=UNSET, descricao=UNSET):
        if codigo is not UNSET:
            self.codigo = codigo
        if descricao is not UNSET:
            self.descricao = descricao
        self.save()

    def excluir_natureza(self):
        self.delete()

class Operacao(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="operacoes")
    tipo_operacao_codigo = models.CharField(max_length=50)
    descricao_receita_despesa = models.CharField(max_length=200, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "tipo_operacao_codigo"], name="uq_operacao_empresa_codigo"),
        ]

    def __str__(self):
        return f"{self.tipo_operacao_codigo} - {self.descricao_receita_despesa}"

    @classmethod
    def criar_operacao(cls, empresa, tipo_operacao_codigo, descricao_receita_despesa=""):
        operacao = cls(
            empresa=empresa,
            tipo_operacao_codigo=tipo_operacao_codigo,
            descricao_receita_despesa=descricao_receita_despesa,
        )
        operacao.save()
        return operacao

    @classmethod
    def listar_operacoes_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    @classmethod
    def obter_ou_criar_por_codigo_descricao(cls, empresa, tipo_operacao_codigo, descricao_receita_despesa):
        defaults = {"descricao_receita_despesa": descricao_receita_despesa}
        operacao, created = cls.objects.get_or_create(
            empresa=empresa,
            tipo_operacao_codigo=tipo_operacao_codigo,
            defaults=defaults,
        )
        if not created and descricao_receita_despesa and operacao.descricao_receita_despesa != descricao_receita_despesa:
            operacao.descricao_receita_despesa = descricao_receita_despesa
            operacao.save(update_fields=["descricao_receita_despesa"])
        return operacao

    def atualizar_operacao(self, tipo_operacao_codigo=UNSET, descricao_receita_despesa=UNSET):
        if tipo_operacao_codigo is not UNSET:
            self.tipo_operacao_codigo = tipo_operacao_codigo
        if descricao_receita_despesa is not UNSET:
            self.descricao_receita_despesa = descricao_receita_despesa
        self.save()

    def excluir_operacao(self):
        self.delete()

class CentroResultado(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="centros_resultado")
    descricao = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "descricao"], name="uq_centro_resultado_empresa_descricao"),
        ]

    def __str__(self):
        return self.descricao

    @classmethod
    def criar_centro_resultado(cls, empresa, descricao):
        centro_resultado = cls(empresa=empresa, descricao=descricao)
        centro_resultado.save()
        return centro_resultado

    @classmethod
    def listar_centros_resultado_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    @classmethod
    def obter_ou_criar_por_descricao(cls, empresa, descricao):
        descricao = (descricao or "").strip()
        if not descricao:
            return None
        centro_resultado, _ = cls.objects.get_or_create(
            empresa=empresa,
            descricao=descricao,
        )
        return centro_resultado

    def atualizar_centro_resultado(self, descricao=UNSET):
        if descricao is not UNSET:
            self.descricao = descricao
        self.save()

    def excluir_centro_resultado(self):
        self.delete()

class FluxoDeCaixaDFC(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="fluxos_de_caixa_dfc")
    data_negociacao = models.DateField()
    data_vencimento = models.DateField()
    valor_liquido = models.DecimalField(max_digits=10, decimal_places=2)
    numero_nota = models.CharField(max_length=50, blank=True, default="")
    titulo = models.ForeignKey(Titulo, on_delete=models.SET_NULL, null=True, blank=True)
    centro_resultado = models.ForeignKey(CentroResultado, on_delete=models.SET_NULL, null=True, blank=True)
    natureza = models.ForeignKey(Natureza, on_delete=models.SET_NULL, null=True, blank=True)
    historico = models.TextField(blank=True, default="")
    parceiro = models.ForeignKey(Parceiro, on_delete=models.SET_NULL, null=True, blank=True)
    operacao = models.ForeignKey(Operacao, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_movimento = models.CharField(max_length=20, blank=True, default="")

    def __str__(self):
        return f"DFC #{self.id} - {self.empresa.nome}"

    @classmethod
    def criar_fluxo_de_caixa_dfc(
        cls,
        empresa,
        data_negociacao,
        data_vencimento,
        valor_liquido=0,
        numero_nota="",
        titulo=None,
        centro_resultado=None,
        natureza=None,
        historico="",
        parceiro=None,
        operacao=None,
        tipo_movimento="",
    ):
        fluxo = cls(
            empresa=empresa,
            data_negociacao=data_negociacao,
            data_vencimento=data_vencimento,
            valor_liquido=valor_liquido,
            numero_nota=numero_nota,
            titulo=titulo,
            centro_resultado=centro_resultado,
            natureza=natureza,
            historico=historico,
            parceiro=parceiro,
            operacao=operacao,
            tipo_movimento=tipo_movimento,
        )
        fluxo.save()
        return fluxo

    @classmethod
    def listar_fluxos_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_fluxo_de_caixa_dfc(
        self,
        data_negociacao=UNSET,
        data_vencimento=UNSET,
        valor_liquido=UNSET,
        numero_nota=UNSET,
        titulo=UNSET,
        centro_resultado=UNSET,
        natureza=UNSET,
        historico=UNSET,
        parceiro=UNSET,
        operacao=UNSET,
        tipo_movimento=UNSET,
    ):
        if data_negociacao is not UNSET:
            self.data_negociacao = data_negociacao
        if data_vencimento is not UNSET:
            self.data_vencimento = data_vencimento
        if valor_liquido is not UNSET:
            self.valor_liquido = valor_liquido
        if numero_nota is not UNSET:
            self.numero_nota = numero_nota
        if titulo is not UNSET:
            self.titulo = titulo
        if centro_resultado is not UNSET:
            self.centro_resultado = centro_resultado
        if natureza is not UNSET:
            self.natureza = natureza
        if historico is not UNSET:
            self.historico = historico
        if parceiro is not UNSET:
            self.parceiro = parceiro
        if operacao is not UNSET:
            self.operacao = operacao
        if tipo_movimento is not UNSET:
            self.tipo_movimento = tipo_movimento
        self.save()

    def excluir_fluxo_de_caixa_dfc(self):
        self.delete()


class Faturamento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="faturamentos")
    nome_origem = models.CharField(max_length=120, blank=True, default="")
    data_faturamento = models.DateField()
    nome_empresa = models.CharField(max_length=220, blank=True, default="")
    parceiro = models.ForeignKey(Parceiro, on_delete=models.SET_NULL, null=True, blank=True, related_name="faturamentos")
    numero_nota = models.BigIntegerField(default=0, db_column="nro_nota")
    indice_produto = models.PositiveIntegerField(default=1, db_column="indice_produto")
    valor_nota = models.DecimalField(max_digits=16, decimal_places=2, default=0, db_column="vlr_nota")
    participacao_venda_geral = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    participacao_venda_cliente = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    valor_nota_unico = models.DecimalField(max_digits=16, decimal_places=2, default=0, db_column="vlr_nota_unico")
    peso_bruto = models.DecimalField(max_digits=16, decimal_places=2, default=0, db_column="peso_bruto")
    peso_bruto_unico = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    quantidade_volumes = models.DecimalField(max_digits=16, decimal_places=2, default=0, db_column="qtd_volumes")
    quantidade_saida = models.DecimalField(max_digits=16, decimal_places=2, default=0, db_column="qtd_saida")
    status_nfe = models.CharField(max_length=80, blank=True, default="")
    apelido_vendedor = models.CharField(max_length=150, blank=True, default="")
    operacao = models.ForeignKey(Operacao, on_delete=models.SET_NULL, null=True, blank=True)
    natureza = models.ForeignKey(Natureza, on_delete=models.SET_NULL, null=True, blank=True)
    centro_resultado = models.ForeignKey(CentroResultado, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_movimento = models.CharField(max_length=80, blank=True, default="")
    prazo_medio = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    media_unica = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    tipo_venda = models.CharField(max_length=120, blank=True, default="")
    produto = models.ForeignKey(Produto, on_delete=models.SET_NULL, null=True, blank=True, related_name="faturamentos")
    gerente = models.CharField(max_length=150, blank=True, default="")
    descricao_perfil = models.CharField(max_length=220, blank=True, default="")
    valor_frete = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_column="criado_em")
    atualizado_em = models.DateTimeField(auto_now=True, db_column="atualizado_em")

    def __str__(self):
        return f"Faturamento #{self.id} - {self.empresa.nome}"

    @classmethod
    def criar_faturamento(
        cls,
        empresa,
        nome_origem="",
        data_faturamento=None,
        nome_empresa="",
        parceiro=None,
        numero_nota=0,
        indice_produto=1,
        valor_nota=0,
        participacao_venda_geral=0,
        participacao_venda_cliente=0,
        valor_nota_unico=0,
        peso_bruto=0,
        peso_bruto_unico=0,
        quantidade_volumes=0,
        quantidade_saida=0,
        status_nfe="",
        apelido_vendedor="",
        operacao=None,
        natureza=None,
        centro_resultado=None,
        tipo_movimento="",
        prazo_medio=0,
        media_unica=None,
        tipo_venda="",
        produto=None,
        gerente="",
        descricao_perfil="",
        valor_frete=None,
    ):
        item = cls(
            empresa=empresa,
            nome_origem=nome_origem,
            data_faturamento=data_faturamento,
            nome_empresa=nome_empresa,
            parceiro=parceiro,
            numero_nota=numero_nota,
            indice_produto=indice_produto,
            valor_nota=valor_nota,
            participacao_venda_geral=participacao_venda_geral,
            participacao_venda_cliente=participacao_venda_cliente,
            valor_nota_unico=valor_nota_unico,
            peso_bruto=peso_bruto,
            peso_bruto_unico=peso_bruto_unico,
            quantidade_volumes=quantidade_volumes,
            quantidade_saida=quantidade_saida,
            status_nfe=status_nfe,
            apelido_vendedor=apelido_vendedor,
            operacao=operacao,
            natureza=natureza,
            centro_resultado=centro_resultado,
            tipo_movimento=tipo_movimento,
            prazo_medio=prazo_medio,
            media_unica=media_unica,
            tipo_venda=tipo_venda,
            produto=produto,
            gerente=gerente,
            descricao_perfil=descricao_perfil,
            valor_frete=valor_frete,
        )
        item.save()
        return item

    @classmethod
    def listar_faturamento_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_faturamento(
        self,
        nome_origem=UNSET,
        data_faturamento=UNSET,
        nome_empresa=UNSET,
        parceiro=UNSET,
        numero_nota=UNSET,
        indice_produto=UNSET,
        valor_nota=UNSET,
        participacao_venda_geral=UNSET,
        participacao_venda_cliente=UNSET,
        valor_nota_unico=UNSET,
        peso_bruto=UNSET,
        peso_bruto_unico=UNSET,
        quantidade_volumes=UNSET,
        quantidade_saida=UNSET,
        status_nfe=UNSET,
        apelido_vendedor=UNSET,
        operacao=UNSET,
        natureza=UNSET,
        centro_resultado=UNSET,
        tipo_movimento=UNSET,
        prazo_medio=UNSET,
        media_unica=UNSET,
        tipo_venda=UNSET,
        produto=UNSET,
        gerente=UNSET,
        descricao_perfil=UNSET,
        valor_frete=UNSET,
    ):
        if nome_origem is not UNSET:
            self.nome_origem = nome_origem
        if data_faturamento is not UNSET:
            self.data_faturamento = data_faturamento
        if nome_empresa is not UNSET:
            self.nome_empresa = nome_empresa
        if parceiro is not UNSET:
            self.parceiro = parceiro
        if numero_nota is not UNSET:
            self.numero_nota = numero_nota
        if indice_produto is not UNSET:
            self.indice_produto = indice_produto
        if valor_nota is not UNSET:
            self.valor_nota = valor_nota
        if participacao_venda_geral is not UNSET:
            self.participacao_venda_geral = participacao_venda_geral
        if participacao_venda_cliente is not UNSET:
            self.participacao_venda_cliente = participacao_venda_cliente
        if valor_nota_unico is not UNSET:
            self.valor_nota_unico = valor_nota_unico
        if peso_bruto is not UNSET:
            self.peso_bruto = peso_bruto
        if peso_bruto_unico is not UNSET:
            self.peso_bruto_unico = peso_bruto_unico
        if quantidade_volumes is not UNSET:
            self.quantidade_volumes = quantidade_volumes
        if quantidade_saida is not UNSET:
            self.quantidade_saida = quantidade_saida
        if status_nfe is not UNSET:
            self.status_nfe = status_nfe
        if apelido_vendedor is not UNSET:
            self.apelido_vendedor = apelido_vendedor
        if operacao is not UNSET:
            self.operacao = operacao
        if natureza is not UNSET:
            self.natureza = natureza
        if centro_resultado is not UNSET:
            self.centro_resultado = centro_resultado
        if tipo_movimento is not UNSET:
            self.tipo_movimento = tipo_movimento
        if prazo_medio is not UNSET:
            self.prazo_medio = prazo_medio
        if media_unica is not UNSET:
            self.media_unica = media_unica
        if tipo_venda is not UNSET:
            self.tipo_venda = tipo_venda
        if produto is not UNSET:
            self.produto = produto
        if gerente is not UNSET:
            self.gerente = gerente
        if descricao_perfil is not UNSET:
            self.descricao_perfil = descricao_perfil
        if valor_frete is not UNSET:
            self.valor_frete = valor_frete
        self.save()

    def excluir_faturamento(self):
        self.delete()


class Adiantamento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="adiantamentos")
    moeda = models.CharField(max_length=120, blank=True, default="")
    saldo_banco_em_reais = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    saldo_real_em_reais = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    saldo_real = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    conta_descricao = models.CharField(max_length=255)
    saldo_banco = models.BigIntegerField(default=0)
    banco = models.CharField(max_length=255, blank=True, default="")
    agencia = models.CharField(max_length=120, blank=True, default="")
    conta_bancaria = models.CharField(max_length=255, blank=True, default="")
    empresa_descricao = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f"Adiantamento #{self.id} - {self.empresa.nome}"

    @classmethod
    def criar_adiantamento(
        cls,
        empresa,
        moeda="",
        saldo_banco_em_reais=0,
        saldo_real_em_reais=0,
        saldo_real=0,
        conta_descricao="",
        saldo_banco=0,
        banco="",
        agencia="",
        conta_bancaria="",
        empresa_descricao="",
    ):
        item = cls(
            empresa=empresa,
            moeda=moeda,
            saldo_banco_em_reais=saldo_banco_em_reais,
            saldo_real_em_reais=saldo_real_em_reais,
            saldo_real=saldo_real,
            conta_descricao=conta_descricao,
            saldo_banco=saldo_banco,
            banco=banco,
            agencia=agencia,
            conta_bancaria=conta_bancaria,
            empresa_descricao=empresa_descricao,
        )
        item.save()
        return item

    @classmethod
    def listar_adiantamentos_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_adiantamento(
        self,
        moeda=UNSET,
        saldo_banco_em_reais=UNSET,
        saldo_real_em_reais=UNSET,
        saldo_real=UNSET,
        conta_descricao=UNSET,
        saldo_banco=UNSET,
        banco=UNSET,
        agencia=UNSET,
        conta_bancaria=UNSET,
        empresa_descricao=UNSET,
    ):
        if moeda is not UNSET:
            self.moeda = moeda
        if saldo_banco_em_reais is not UNSET:
            self.saldo_banco_em_reais = saldo_banco_em_reais
        if saldo_real_em_reais is not UNSET:
            self.saldo_real_em_reais = saldo_real_em_reais
        if saldo_real is not UNSET:
            self.saldo_real = saldo_real
        if conta_descricao is not UNSET:
            self.conta_descricao = conta_descricao
        if saldo_banco is not UNSET:
            self.saldo_banco = saldo_banco
        if banco is not UNSET:
            self.banco = banco
        if agencia is not UNSET:
            self.agencia = agencia
        if conta_bancaria is not UNSET:
            self.conta_bancaria = conta_bancaria
        if empresa_descricao is not UNSET:
            self.empresa_descricao = empresa_descricao
        self.save()

    def excluir_adiantamento(self):
        self.delete()


class ContasAReceber(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="contas_a_receber")
    data_negociacao = models.DateField()
    data_vencimento = models.DateField()
    data_arquivo = models.DateField(null=True, blank=True)
    nome_fantasia_empresa = models.CharField(max_length=200, blank=True, default="")
    parceiro = models.ForeignKey(Parceiro, on_delete=models.SET_NULL, null=True, blank=True)
    numero_nota = models.CharField(max_length=50, blank=True, default="")
    vendedor = models.CharField(max_length=150, blank=True, default="")
    valor_desdobramento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_liquido = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    titulo = models.ForeignKey(Titulo, on_delete=models.SET_NULL, null=True, blank=True)
    natureza = models.ForeignKey(Natureza, on_delete=models.SET_NULL, null=True, blank=True)
    centro_resultado = models.ForeignKey(CentroResultado, on_delete=models.SET_NULL, null=True, blank=True)
    operacao = models.ForeignKey(Operacao, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"ContasAReceber #{self.id} - {self.empresa.nome}"

    def _calcular_dias_diferenca(self):
        hoje = timezone.localdate()
        if not self.data_vencimento:
            return None
        return (hoje - self.data_vencimento).days

    @property
    def dias_diferenca(self):
        return self._calcular_dias_diferenca()

    @property
    def status(self):
        if not self.data_vencimento:
            return ""
        hoje = timezone.localdate()
        if self.data_vencimento < hoje:
            return "Vencido"
        return "A Vencer"

    @property
    def intervalo(self):
        dias = self.dias_diferenca
        if dias is None:
            return ""
        dias = abs(dias)
        if dias <= 5:
            return "0-5 (CML)"
        if dias <= 20:
            return "6-20 (FIN)"
        if dias <= 30:
            return "21-30 (POL)"
        if dias <= 60:
            return "31-60 (POL)"
        if dias <= 90:
            return "61-90 (POL)"
        if dias <= 120:
            return "91-120 (JUR1)"
        if dias <= 180:
            return "121-180 (JUR1)"
        return "+180 (JUR2)"

    @classmethod
    def criar_conta_a_receber(
        cls,
        empresa,
        data_negociacao,
        data_vencimento,
        data_arquivo=None,
        nome_fantasia_empresa="",
        parceiro=None,
        numero_nota="",
        vendedor="",
        valor_desdobramento=0,
        valor_liquido=0,
        titulo=None,
        natureza=None,
        centro_resultado=None,
        operacao=None,
    ):
        conta = cls(
            empresa=empresa,
            data_negociacao=data_negociacao,
            data_vencimento=data_vencimento,
            data_arquivo=data_arquivo,
            nome_fantasia_empresa=nome_fantasia_empresa,
            parceiro=parceiro,
            numero_nota=numero_nota,
            vendedor=vendedor,
            valor_desdobramento=valor_desdobramento,
            valor_liquido=valor_liquido,
            titulo=titulo,
            natureza=natureza,
            centro_resultado=centro_resultado,
            operacao=operacao,
        )
        conta.save()
        return conta

    @classmethod
    def listar_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_conta_a_receber(
        self,
        data_negociacao=UNSET,
        data_vencimento=UNSET,
        data_arquivo=UNSET,
        nome_fantasia_empresa=UNSET,
        parceiro=UNSET,
        numero_nota=UNSET,
        vendedor=UNSET,
        valor_desdobramento=UNSET,
        valor_liquido=UNSET,
        titulo=UNSET,
        natureza=UNSET,
        centro_resultado=UNSET,
        operacao=UNSET,
    ):
        if data_negociacao is not UNSET:
            self.data_negociacao = data_negociacao
        if data_vencimento is not UNSET:
            self.data_vencimento = data_vencimento
        if data_arquivo is not UNSET:
            self.data_arquivo = data_arquivo
        if nome_fantasia_empresa is not UNSET:
            self.nome_fantasia_empresa = nome_fantasia_empresa
        if parceiro is not UNSET:
            self.parceiro = parceiro
        if numero_nota is not UNSET:
            self.numero_nota = numero_nota
        if vendedor is not UNSET:
            self.vendedor = vendedor
        if valor_desdobramento is not UNSET:
            self.valor_desdobramento = valor_desdobramento
        if valor_liquido is not UNSET:
            self.valor_liquido = valor_liquido
        if titulo is not UNSET:
            self.titulo = titulo
        if natureza is not UNSET:
            self.natureza = natureza
        if centro_resultado is not UNSET:
            self.centro_resultado = centro_resultado
        if operacao is not UNSET:
            self.operacao = operacao
        self.save()

    def excluir_conta_a_receber(self):
        self.delete()

#importacao por pasta (semelhante de vendas)
class Orcamento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="orcamentos")
    nome_empresa = models.CharField(max_length=200, blank=True, default="")
    data_vencimento = models.DateField()
    data_baixa = models.DateField()
    valor_baixa = models.DecimalField(max_digits=10, decimal_places=2)
    valor_liquido = models.DecimalField(max_digits=10, decimal_places=2)
    valor_desdobramento = models.DecimalField(max_digits=10, decimal_places=2)
    natureza = models.ForeignKey(Natureza, on_delete=models.SET_NULL, null=True, blank=True) #descricao no front
    titulo = models.ForeignKey(Titulo, on_delete=models.SET_NULL, null=True, blank=True) #descricao no front
    centro_resultado = models.ForeignKey(CentroResultado, on_delete=models.PROTECT) #descricao no front
    operacao = models.ForeignKey(Operacao, on_delete=models.SET_NULL, null=True, blank=True) #receita ou despesa aparece na tabela do front
    parceiro = models.ForeignKey(Parceiro, on_delete=models.SET_NULL, null=True, blank=True) #cod e nome

    @classmethod
    def criar_orcamento(
        cls,
        empresa,
        data_vencimento,
        data_baixa,
        valor_baixa,
        valor_liquido,
        valor_desdobramento,
        natureza=None,
        titulo=None,
        centro_resultado=None,
        operacao=None,
        parceiro=None,
        nome_empresa="",
    ):
        item = cls(
            empresa=empresa,
            nome_empresa=nome_empresa,
            data_vencimento=data_vencimento,
            data_baixa=data_baixa,
            valor_baixa=valor_baixa,
            valor_liquido=valor_liquido,
            valor_desdobramento=valor_desdobramento,
            natureza=natureza,
            titulo=titulo,
            centro_resultado=centro_resultado,
            operacao=operacao,
            parceiro=parceiro,
        )
        item.save()
        return item

    def atualizar_orcamento(
        self,
        data_vencimento=UNSET,
        data_baixa=UNSET,
        valor_baixa=UNSET,
        valor_liquido=UNSET,
        valor_desdobramento=UNSET,
        natureza=UNSET,
        titulo=UNSET,
        centro_resultado=UNSET,
        operacao=UNSET,
        parceiro=UNSET,
        nome_empresa=UNSET,
    ):
        if nome_empresa is not UNSET:
            self.nome_empresa = nome_empresa
        if data_vencimento is not UNSET:
            self.data_vencimento = data_vencimento
        if data_baixa is not UNSET:
            self.data_baixa = data_baixa
        if valor_baixa is not UNSET:
            self.valor_baixa = valor_baixa
        if valor_liquido is not UNSET:
            self.valor_liquido = valor_liquido
        if valor_desdobramento is not UNSET:
            self.valor_desdobramento = valor_desdobramento
        if natureza is not UNSET:
            self.natureza = natureza
        if titulo is not UNSET:
            self.titulo = titulo
        if centro_resultado is not UNSET:
            self.centro_resultado = centro_resultado
        if operacao is not UNSET:
            self.operacao = operacao
        if parceiro is not UNSET:
            self.parceiro = parceiro
        self.save()

    def excluir_orcamento(self):
        self.delete()


class OrcamentoPlanejado(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="orcamentos_planejados")
    nome_empresa = models.CharField(max_length=200, blank=True, default="")
    ano = models.PositiveSmallIntegerField()
    natureza = models.ForeignKey(Natureza, on_delete=models.SET_NULL, null=True, blank=True)
    centro_resultado = models.ForeignKey(CentroResultado, on_delete=models.SET_NULL, null=True, blank=True)
    janeiro = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fevereiro = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    marco = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    abril = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    maio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    junho = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    julho = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    agosto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    setembro = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outubro = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    novembro = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dezembro = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @classmethod
    def criar_orcamento_planejado(
        cls,
        empresa,
        ano,
        nome_empresa="",
        natureza=None,
        centro_resultado=None,
        janeiro=0,
        fevereiro=0,
        marco=0,
        abril=0,
        maio=0,
        junho=0,
        julho=0,
        agosto=0,
        setembro=0,
        outubro=0,
        novembro=0,
        dezembro=0,
    ):
        item = cls(
            empresa=empresa,
            ano=ano,
            nome_empresa=nome_empresa,
            natureza=natureza,
            centro_resultado=centro_resultado,
            janeiro=janeiro,
            fevereiro=fevereiro,
            marco=marco,
            abril=abril,
            maio=maio,
            junho=junho,
            julho=julho,
            agosto=agosto,
            setembro=setembro,
            outubro=outubro,
            novembro=novembro,
            dezembro=dezembro,
        )
        item.save()
        return item

    def atualizar_orcamento_planejado(
        self,
        ano=UNSET,
        nome_empresa=UNSET,
        natureza=UNSET,
        centro_resultado=UNSET,
        janeiro=UNSET,
        fevereiro=UNSET,
        marco=UNSET,
        abril=UNSET,
        maio=UNSET,
        junho=UNSET,
        julho=UNSET,
        agosto=UNSET,
        setembro=UNSET,
        outubro=UNSET,
        novembro=UNSET,
        dezembro=UNSET,
    ):
        if ano is not UNSET:
            self.ano = ano
        if nome_empresa is not UNSET:
            self.nome_empresa = nome_empresa
        if natureza is not UNSET:
            self.natureza = natureza
        if centro_resultado is not UNSET:
            self.centro_resultado = centro_resultado
        if janeiro is not UNSET:
            self.janeiro = janeiro
        if fevereiro is not UNSET:
            self.fevereiro = fevereiro
        if marco is not UNSET:
            self.marco = marco
        if abril is not UNSET:
            self.abril = abril
        if maio is not UNSET:
            self.maio = maio
        if junho is not UNSET:
            self.junho = junho
        if julho is not UNSET:
            self.julho = julho
        if agosto is not UNSET:
            self.agosto = agosto
        if setembro is not UNSET:
            self.setembro = setembro
        if outubro is not UNSET:
            self.outubro = outubro
        if novembro is not UNSET:
            self.novembro = novembro
        if dezembro is not UNSET:
            self.dezembro = dezembro
        self.save()

    def excluir_orcamento_planejado(self):
        self.delete()
