from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from datetime import timedelta
from .utils.comercial_transformers import _definir_margem, _definir_lucro

UNSET = object()

class Empresa(models.Model):
    nome = models.CharField(max_length=150)

    def __str__(self):
        return self.nome

    @classmethod
    def criar_empresa(cls, nome):
        empresa = cls(nome=nome)
        empresa.save()
        return empresa

    def atualizar_nome(self, novo_nome):
        self.nome = novo_nome
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
    def criar_usuario(cls, username, password, empresa, permissoes=None):
        usuario = cls.objects.create_user(
            username=username,
            password=password,
            empresa=empresa,
        )
        if permissoes:
            usuario.permissoes.set(permissoes)
        return usuario

    @classmethod
    def listar_usuarios_por_empresa(cls, empresa):
        return cls.objects.filter(empresa=empresa)

    def atualizar_usuario(self, username=None, password=None, permissoes=None):
        if username:
            self.username = username
        if password:
            self.set_password(password)
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

class Carteira(models.Model):
    empresa = models.ForeignKey( Empresa, on_delete=models.CASCADE, related_name="carteiras")
    regiao = models.ForeignKey(Regiao, on_delete=models.SET_NULL, null=True, blank=True)
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True, blank=True)
    valor_faturado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    limite_credito = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ultima_venda = models.DateField(null=True, blank=True)
    qtd_dias_sem_venda = models.PositiveIntegerField(default=0)
    intervalo = models.CharField(max_length=20, blank=True, default="")
    data_cadastro = models.DateField(default=timezone.localdate)
    gerente = models.CharField(max_length=150, blank=True, default="")
    vendedor = models.CharField(max_length=150, blank=True, default="")
    descricao_perfil = models.CharField(max_length=200, blank=True, default="")
    nome_parceiro = models.CharField(max_length=150, blank=True, default="")
    ativo_indicador = models.BooleanField(default=True)
    cliente_indicador = models.BooleanField(default=False)
    fornecedor_indicador = models.BooleanField(default=False)
    transporte_indicador = models.BooleanField(default=False)

    def __str__(self):
        return f"Carteira #{self.id} - {self.nome_parceiro}"
    
    @classmethod
    def criar_carteira(
        cls,
        empresa,
        regiao=None,
        cidade=None,
        valor_faturado=0,
        limite_credito=0,
        ultima_venda=None,
        qtd_dias_sem_venda=0,
        intervalo="",
        data_cadastro=None,
        gerente=None,
        vendedor="",
        descricao_perfil="",
        nome_parceiro="",
        ativo_indicador=True,
        cliente_indicador=False,
        fornecedor_indicador=False,
        transporte_indicador=False
    ):
        carteira = cls(
            empresa=empresa,
            regiao=regiao,
            cidade=cidade,
            valor_faturado=valor_faturado,
            limite_credito=limite_credito,
            ultima_venda=ultima_venda,
            qtd_dias_sem_venda=qtd_dias_sem_venda,
            intervalo=intervalo,
            data_cadastro=data_cadastro or timezone.localdate(),
            gerente=gerente,
            vendedor=vendedor,
            descricao_perfil=descricao_perfil,
            nome_parceiro=nome_parceiro,
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
        valor_faturado=UNSET,
        limite_credito=UNSET,
        ultima_venda=UNSET,
        qtd_dias_sem_venda=UNSET,
        intervalo=UNSET,
        data_cadastro=UNSET,
        gerente=UNSET,
        vendedor=UNSET,
        descricao_perfil=UNSET,
        nome_parceiro=UNSET,
        ativo_indicador=UNSET,
        cliente_indicador=UNSET,
        fornecedor_indicador=UNSET,
        transporte_indicador=UNSET,
    ):
        if regiao is not UNSET:
            self.regiao = regiao
        if cidade is not UNSET:
            self.cidade = cidade
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
        if nome_parceiro is not UNSET:
            self.nome_parceiro = nome_parceiro
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
