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

class Parceiro(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="parceiros")
    nome = models.CharField(max_length=150)
    codigo = models.CharField(max_length=50)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], name="uq_parceiro_empresa_codigo"),
        ]

    def __str__(self):
        return f"{self.nome} ({self.codigo})"
    
    @classmethod
    def criar_parceiro(cls, nome, codigo, empresa):
        parceiro = cls(nome=nome, codigo=codigo, empresa=empresa)
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

    def atualizar_parceiro(self, novo_nome=None, novo_codigo=None):
        if novo_nome:
            self.nome = novo_nome
        if novo_codigo:
            self.codigo = novo_codigo
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

    def __str__(self):
        parceiro_nome = self.parceiro.nome if self.parceiro else "Sem parceiro"
        return f"Carteira #{self.id} - {parceiro_nome}"
    
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
    descricao_produto = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo_produto"], name="uq_produto_empresa_codigo"),
        ]

    def __str__(self):
        return f"{self.codigo_produto} - {self.descricao_produto}"

    @classmethod
    def criar_produto(cls, empresa, codigo_produto, descricao_produto=""):
        item = cls(
            empresa=empresa,
            codigo_produto=codigo_produto,
            descricao_produto=descricao_produto,
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

    def atualizar_produto(self, codigo_produto=UNSET, descricao_produto=UNSET):
        if codigo_produto is not UNSET:
            self.codigo_produto = codigo_produto
        if descricao_produto is not UNSET:
            self.descricao_produto = descricao_produto
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
        self.save()

    def excluir_producao(self):
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
