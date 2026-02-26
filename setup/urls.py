"""
URL configuration for setup project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),

    path('financeiro/', views.financeiro, name='financeiro'),
    path('administrativo/', views.administrativo, name='administrativo'),
    path('comercial/', views.comercial, name='comercial'),
    path('parametros/', views.parametros, name='parametros'),
    path('operacional/', views.operacional, name='operacional'),

    path('entrar/', views.entrar, name='entrar'),
    path('sair/', views.sair, name='sair'),

    path('painel_admin/', views.painel_admin, name='painel_admin'),

    path('criar_empresa/', views.criar_empresa, name='criar_empresa'),
    path('editar_empresa/<int:empresa_id>/', views.editar_empresa, name='editar_empresa'),
    path('excluir_empresa/<int:empresa_id>/', views.excluir_empresa, name='excluir_empresa'),

    path('usuarios_permissoes/<int:empresa_id>', views.usuarios_permissoes, name='usuarios_permissoes'),
    
    path('cadastrar_usuario/<int:empresa_id>', views.cadastrar_usuario, name='cadastrar_usuario'),
    path('editar_usuario/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),
    path('excluir_usuario/<int:usuario_id>/', views.excluir_usuario, name='excluir_usuario'),


    # Modulos - Financeiro
    path('comite_diario/<int:empresa_id>/', views.comite_diario, name='comite_diario'),
    path('balanco_patrimonial/<int:empresa_id>/', views.balanco_patrimonial, name='balanco_patrimonial'),
    path('dre/<int:empresa_id>/', views.dre, name='dre'),
    path('contas_a_receber/<int:empresa_id>/', views.contas_a_receber, name='contas_a_receber'),
    path('contas_a_receber/<int:empresa_id>/editar/<int:conta_id>/', views.editar_contas_a_receber_modulo, name='editar_contas_a_receber_modulo'),
    path('contas_a_receber/<int:empresa_id>/excluir/<int:conta_id>/', views.excluir_contas_a_receber_modulo, name='excluir_contas_a_receber_modulo'),
    path('dfc/<int:empresa_id>/', views.dfc, name='dfc'),
    path('dfc/<int:empresa_id>/editar/<int:dfc_id>/', views.editar_dfc_modulo, name='editar_dfc_modulo'),
    path('dfc/<int:empresa_id>/excluir/<int:dfc_id>/', views.excluir_dfc_modulo, name='excluir_dfc_modulo'),
    path('titulos/<int:empresa_id>/', views.titulos, name='titulos'),
    path('titulos/<int:empresa_id>/criar/', views.criar_titulo_modulo, name='criar_titulo_modulo'),
    path('titulos/<int:empresa_id>/editar/<int:titulo_id>/', views.editar_titulo_modulo, name='editar_titulo_modulo'),
    path('titulos/<int:empresa_id>/excluir/<int:titulo_id>/', views.excluir_titulo_modulo, name='excluir_titulo_modulo'),
    path('naturezas/<int:empresa_id>/', views.naturezas, name='naturezas'),
    path('naturezas/<int:empresa_id>/criar/', views.criar_natureza_modulo, name='criar_natureza_modulo'),
    path('naturezas/<int:empresa_id>/editar/<int:natureza_id>/', views.editar_natureza_modulo, name='editar_natureza_modulo'),
    path('naturezas/<int:empresa_id>/excluir/<int:natureza_id>/', views.excluir_natureza_modulo, name='excluir_natureza_modulo'),
    path('operacoes/<int:empresa_id>/', views.operacoes, name='operacoes'),
    path('operacoes/<int:empresa_id>/criar/', views.criar_operacao_modulo, name='criar_operacao_modulo'),
    path('operacoes/<int:empresa_id>/editar/<int:operacao_id>/', views.editar_operacao_modulo, name='editar_operacao_modulo'),
    path('operacoes/<int:empresa_id>/excluir/<int:operacao_id>/', views.excluir_operacao_modulo, name='excluir_operacao_modulo'),
    path('parceiros/<int:empresa_id>/', views.parceiros, name='parceiros'),
    path('parceiros/<int:empresa_id>/criar/', views.criar_parceiro_modulo, name='criar_parceiro_modulo'),
    path('parceiros/<int:empresa_id>/editar/<int:parceiro_id>/', views.editar_parceiro_modulo, name='editar_parceiro_modulo'),
    path('parceiros/<int:empresa_id>/excluir/<int:parceiro_id>/', views.excluir_parceiro_modulo, name='excluir_parceiro_modulo'),
    path('produtos/<int:empresa_id>/', views.produtos, name='produtos'),
    path('produtos/<int:empresa_id>/criar/', views.criar_produto_modulo, name='criar_produto_modulo'),
    path('produtos/<int:empresa_id>/editar/<int:produto_id>/', views.editar_produto_modulo, name='editar_produto_modulo'),
    path('produtos/<int:empresa_id>/excluir/<int:produto_id>/', views.excluir_produto_modulo, name='excluir_produto_modulo'),
    path('unidades_federativas/<int:empresa_id>/', views.unidades_federativas, name='unidades_federativas'),
    path('unidades_federativas/<int:empresa_id>/criar/', views.criar_unidade_federativa_modulo, name='criar_unidade_federativa_modulo'),
    path('unidades_federativas/<int:empresa_id>/editar/<int:unidade_federativa_id>/', views.editar_unidade_federativa_modulo, name='editar_unidade_federativa_modulo'),
    path('unidades_federativas/<int:empresa_id>/excluir/<int:unidade_federativa_id>/', views.excluir_unidade_federativa_modulo, name='excluir_unidade_federativa_modulo'),
    path('rotas/<int:empresa_id>/', views.rotas, name='rotas'),
    path('rotas/<int:empresa_id>/criar/', views.criar_rota_modulo, name='criar_rota_modulo'),
    path('rotas/<int:empresa_id>/editar/<int:rota_id>/', views.editar_rota_modulo, name='editar_rota_modulo'),
    path('rotas/<int:empresa_id>/excluir/<int:rota_id>/', views.excluir_rota_modulo, name='excluir_rota_modulo'),
    path('motoristas/<int:empresa_id>/', views.motoristas, name='motoristas'),
    path('motoristas/<int:empresa_id>/criar/', views.criar_motorista_modulo, name='criar_motorista_modulo'),
    path('motoristas/<int:empresa_id>/editar/<int:motorista_id>/', views.editar_motorista_modulo, name='editar_motorista_modulo'),
    path('motoristas/<int:empresa_id>/excluir/<int:motorista_id>/', views.excluir_motorista_modulo, name='excluir_motorista_modulo'),
    path('transportadoras/<int:empresa_id>/', views.transportadoras, name='transportadoras'),
    path('transportadoras/<int:empresa_id>/criar/', views.criar_transportadora_modulo, name='criar_transportadora_modulo'),
    path('transportadoras/<int:empresa_id>/editar/<int:transportadora_id>/', views.editar_transportadora_modulo, name='editar_transportadora_modulo'),
    path('transportadoras/<int:empresa_id>/excluir/<int:transportadora_id>/', views.excluir_transportadora_modulo, name='excluir_transportadora_modulo'),
    path('parametros_vendas/<int:empresa_id>/', views.parametros_vendas, name='parametros_vendas'),
    path('parametros_logistica/<int:empresa_id>/', views.parametros_logistica, name='parametros_logistica'),
    path('parametros_administracao/<int:empresa_id>/', views.parametros_administracao, name='parametros_administracao'),
    path('parametros_financeiro/<int:empresa_id>/', views.parametros_financeiro, name='parametros_financeiro'),
    path('centros_resultado/<int:empresa_id>/', views.centros_resultado, name='centros_resultado'),
    path('centros_resultado/<int:empresa_id>/criar/', views.criar_centro_resultado_modulo, name='criar_centro_resultado_modulo'),
    path('centros_resultado/<int:empresa_id>/editar/<int:centro_resultado_id>/', views.editar_centro_resultado_modulo, name='editar_centro_resultado_modulo'),
    path('centros_resultado/<int:empresa_id>/excluir/<int:centro_resultado_id>/', views.excluir_centro_resultado_modulo, name='excluir_centro_resultado_modulo'),
    path('orcamento/<int:empresa_id>/', views.orcamento, name='orcamento'),
    path('orcamentos_realizados/<int:empresa_id>/', views.orcamentos_realizados, name='orcamentos_realizados'),
    path('orcamentos/<int:empresa_id>/', views.orcamentos, name='orcamentos'),
    path('orcamento/<int:empresa_id>/editar/<int:orcamento_id>/', views.editar_orcamento_modulo, name='editar_orcamento_modulo'),
    path('orcamento/<int:empresa_id>/excluir/<int:orcamento_id>/', views.excluir_orcamento_modulo, name='excluir_orcamento_modulo'),
    path('orcamentos/<int:empresa_id>/editar/<int:orcamento_planejado_id>/', views.editar_orcamento_planejado_modulo, name='editar_orcamento_planejado_modulo'),
    path('orcamentos/<int:empresa_id>/excluir/<int:orcamento_planejado_id>/', views.excluir_orcamento_planejado_modulo, name='excluir_orcamento_planejado_modulo'),
    path('adiantamentos/<int:empresa_id>/', views.adiantamentos, name='adiantamentos'),
    path('contratos_redes/<int:empresa_id>/', views.contratos_redes, name='contratos_redes'),


    # Modulos - Administrativo
    path('plano_de_cargos_e_salarios/<int:empresa_id>/', views.plano_de_cargos_e_salarios, name='plano_de_cargos_e_salarios'),
    path('descritivos/<int:empresa_id>/', views.descritivos, name='descritivos'),
    #TOFU
    path('tofu_lista_de_atividades/<int:empresa_id>/', views.tofu_lista_de_atividades, name='tofu_lista_de_atividades'),
    path('tofu_lista_de_atividades/<int:empresa_id>/criar/', views.criar_atividade_tofu, name='criar_atividade_tofu'),
    path('tofu_lista_de_atividades/<int:empresa_id>/editar/<int:atividade_id>/', views.editar_atividade_tofu, name='editar_atividade_tofu'),
    path('tofu_lista_de_atividades/<int:empresa_id>/excluir/<int:atividade_id>/', views.excluir_atividade_tofu, name='excluir_atividade_tofu'),

    path('fiscal_e_contabil/<int:empresa_id>/', views.fiscal_e_contabil, name='fiscal_e_contabil'),
    path('faturamento/<int:empresa_id>/', views.faturamento, name='faturamento'),
    path('apuracao_de_resultados/<int:empresa_id>/', views.apuracao_de_resultados, name='apuracao_de_resultados'),
    path('orcamento_x_realizado/<int:empresa_id>/', views.orcamento_x_realizado, name='orcamento_x_realizado'),
    #Colaboradores
    path('colaboradores/<int:empresa_id>/', views.colaboradores, name='colaboradores'),
    path('colaboradores/<int:empresa_id>/criar/', views.criar_colaborador_modulo, name='criar_colaborador_modulo'),
    path('colaboradores/<int:empresa_id>/editar/<int:colaborador_id>/', views.editar_colaborador_modulo, name='editar_colaborador_modulo'),
    path('colaboradores/<int:empresa_id>/excluir/<int:colaborador_id>/', views.excluir_colaborador_modulo, name='excluir_colaborador_modulo'),
    #Projetos
    path('projetos/<int:empresa_id>/', views.projetos, name='projetos'),
    path('projetos/<int:empresa_id>/criar/', views.criar_projeto_modulo, name='criar_projeto_modulo'),
    path('projetos/<int:empresa_id>/editar/<int:projeto_id>/', views.editar_projeto_modulo, name='editar_projeto_modulo'),
    path('projetos/<int:empresa_id>/excluir/<int:projeto_id>/', views.excluir_projeto_modulo, name='excluir_projeto_modulo'),
    # Modulos - Comercial
    path('carteira/<int:empresa_id>/', views.carteira, name='carteira'),
    path('carteira/<int:empresa_id>/editar/<int:carteira_id>/', views.editar_carteira_modulo, name='editar_carteira_modulo'),
    path('carteira/<int:empresa_id>/excluir/<int:carteira_id>/', views.excluir_carteira_modulo, name='excluir_carteira_modulo'),
    path('cidades/<int:empresa_id>/', views.cidades, name='cidades'),
    path('cidades/<int:empresa_id>/criar/', views.criar_cidade_modulo, name='criar_cidade_modulo'),
    path('cidades/<int:empresa_id>/editar/<int:cidade_id>/', views.editar_cidade_modulo, name='editar_cidade_modulo'),
    path('cidades/<int:empresa_id>/excluir/<int:cidade_id>/', views.excluir_cidade_modulo, name='excluir_cidade_modulo'),
    path('regioes/<int:empresa_id>/', views.regioes, name='regioes'),
    path('regioes/<int:empresa_id>/criar/', views.criar_regiao_modulo, name='criar_regiao_modulo'),
    path('regioes/<int:empresa_id>/editar/<int:regiao_id>/', views.editar_regiao_modulo, name='editar_regiao_modulo'),
    path('regioes/<int:empresa_id>/excluir/<int:regiao_id>/', views.excluir_regiao_modulo, name='excluir_regiao_modulo'),
    path('pedidos_pendentes/<int:empresa_id>/', views.pedidos_pendentes, name='pedidos_pendentes'),
    path('pedidos_pendentes/<int:empresa_id>/editar/<int:pedido_id>/', views.editar_pedido_pendente_modulo, name='editar_pedido_pendente_modulo'),
    path('pedidos_pendentes/<int:empresa_id>/excluir/<int:pedido_id>/', views.excluir_pedido_pendente_modulo, name='excluir_pedido_pendente_modulo'),
    path('agenda/<int:empresa_id>/', views.agenda, name='agenda'),
    path('agenda/<int:empresa_id>/editar/<int:agenda_id>/', views.editar_agenda_modulo, name='editar_agenda_modulo'),
    path('agenda/<int:empresa_id>/excluir/<int:agenda_id>/', views.excluir_agenda_modulo, name='excluir_agenda_modulo'),
    path('vendas_por_categoria/<int:empresa_id>/', views.vendas_por_categoria, name='vendas_por_categoria'),
    path('vendas_por_categoria/<int:empresa_id>/editar/<int:venda_id>/', views.editar_venda_modulo, name='editar_venda_modulo'),
    path('vendas_por_categoria/<int:empresa_id>/excluir/<int:venda_id>/', views.excluir_venda_modulo, name='excluir_venda_modulo'),
    path('precificacao/<int:empresa_id>/', views.precificacao, name='precificacao'),
    path('controle_de_margem/<int:empresa_id>/', views.controle_de_margem, name='controle_de_margem'),
    path('controle_de_margem/<int:empresa_id>/editar/<int:controle_id>/', views.editar_controle_margem_modulo, name='editar_controle_margem_modulo'),
    path('controle_de_margem/<int:empresa_id>/excluir/<int:controle_id>/', views.excluir_controle_margem_modulo, name='excluir_controle_margem_modulo'),


    # Modulos - Operacional
    path('cargas_em_aberto/<int:empresa_id>/', views.cargas_em_aberto, name='cargas_em_aberto'),
    path('cargas_em_aberto/<int:empresa_id>/editar/<int:carga_id>/', views.editar_carga_modulo, name='editar_carga_modulo'),
    path('cargas_em_aberto/<int:empresa_id>/excluir/<int:carga_id>/', views.excluir_carga_modulo, name='excluir_carga_modulo'),
    path('operador_logistico/<int:empresa_id>/', views.operador_logistico, name='operador_logistico'),
    path('tabela_de_fretes/<int:empresa_id>/', views.tabela_de_fretes, name='tabela_de_fretes'),
    path('tabela_de_fretes/<int:empresa_id>/editar/<int:frete_id>/', views.editar_frete_modulo, name='editar_frete_modulo'),
    path('tabela_de_fretes/<int:empresa_id>/excluir/<int:frete_id>/', views.excluir_frete_modulo, name='excluir_frete_modulo'),
    path('estoque_pcp/<int:empresa_id>/', views.estoque_pcp, name='estoque_pcp'),
    path('estoque_pcp/<int:empresa_id>/editar/<int:estoque_id>/', views.editar_estoque_modulo, name='editar_estoque_modulo'),
    path('estoque_pcp/<int:empresa_id>/excluir/<int:estoque_id>/', views.excluir_estoque_modulo, name='excluir_estoque_modulo'),
    path('producao/<int:empresa_id>/', views.producao, name='producao'),
    path('producao/<int:empresa_id>/editar/<int:producao_id>/', views.editar_producao_modulo, name='editar_producao_modulo'),
    path('producao/<int:empresa_id>/excluir/<int:producao_id>/', views.excluir_producao_modulo, name='excluir_producao_modulo'),
]
