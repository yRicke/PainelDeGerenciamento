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
import app.views.core as views_core
import app.views.financeiro as views_financeiro
import app.views.comercial as views_comercial
import app.views.administrativo as views_administrativo
import app.views.operacional as views_operacional
import app.views.parametros as views_parametros
import app.views.admin as views_admin
import app.views.dashboard_pdf as views_dashboard_pdf
import app.api.v1.views as views_api_v1

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views_core.index, name='index'),
    path(
        'api/v1/empresas/<int:empresa_id>/atividades/',
        views_api_v1.AtividadeListAPIView.as_view(),
        name='api_v1_atividades_list',
    ),

    path('financeiro/', views_core.financeiro_home, name='financeiro'),
    path('administrativo/', views_administrativo.administrativo, name='administrativo'),
    path('comercial/', views_core.comercial_home, name='comercial'),
    path('parametros/', views_parametros.parametros, name='parametros'),
    path('operacional/', views_operacional.operacional, name='operacional'),

    path('entrar/', views_core.entrar, name='entrar'),
    path('sair/', views_core.sair, name='sair'),
    path(
        'dashboard-pdf/<int:empresa_id>/<slug:dashboard_slug>/',
        views_dashboard_pdf.dashboard_pdf_generico,
        name='dashboard_pdf_generico',
    ),

    path('painel_admin/', views_admin.painel_admin, name='painel_admin'),

    path('criar_empresa/', views_admin.criar_empresa, name='criar_empresa'),
    path('editar_empresa/<int:empresa_id>/', views_admin.editar_empresa, name='editar_empresa'),
    path('excluir_empresa/<int:empresa_id>/', views_admin.excluir_empresa, name='excluir_empresa'),

    path('usuarios_permissoes/<int:empresa_id>', views_admin.usuarios_permissoes, name='usuarios_permissoes'),
    path('arquivos_subscritos/<int:empresa_id>/', views_admin.arquivos_subscritos, name='arquivos_subscritos'),
    
    path('cadastrar_usuario/<int:empresa_id>', views_admin.cadastrar_usuario, name='cadastrar_usuario'),
    path('editar_usuario/<int:usuario_id>/', views_admin.editar_usuario, name='editar_usuario'),
    path('excluir_usuario/<int:usuario_id>/', views_admin.excluir_usuario, name='excluir_usuario'),


    # Modulos - Financeiro
    path('comite_diario/<int:empresa_id>/', views_financeiro.comite_diario, name='comite_diario'),
    path('balanco_patrimonial/<int:empresa_id>/', views_financeiro.balanco_patrimonial, name='balanco_patrimonial'),
    path('dre/<int:empresa_id>/', views_financeiro.dre, name='dre'),
    path('contas_a_receber/<int:empresa_id>/', views_financeiro.contas_a_receber, name='contas_a_receber'),
    path('contas_a_receber/<int:empresa_id>/dados/', views_financeiro.contas_a_receber_dados, name='contas_a_receber_dados'),
    path(
        'contas_a_receber/<int:empresa_id>/dashboard-faturamento/',
        views_financeiro.contas_a_receber_dashboard_faturamento,
        name='contas_a_receber_dashboard_faturamento',
    ),
    path(
        'contas_a_receber/<int:empresa_id>/dashboard-pdf/',
        views_financeiro.contas_a_receber_dashboard_pdf,
        name='contas_a_receber_dashboard_pdf',
    ),
    path('contas_a_receber/<int:empresa_id>/editar/<int:conta_id>/', views_financeiro.editar_contas_a_receber_modulo, name='editar_contas_a_receber_modulo'),
    path('contas_a_receber/<int:empresa_id>/excluir/<int:conta_id>/', views_financeiro.excluir_contas_a_receber_modulo, name='excluir_contas_a_receber_modulo'),
    path('dfc/<int:empresa_id>/', views_financeiro.dfc, name='dfc'),
    path('dfc/<int:empresa_id>/editar/<int:dfc_id>/', views_financeiro.editar_dfc_modulo, name='editar_dfc_modulo'),
    path('dfc/<int:empresa_id>/excluir/<int:dfc_id>/', views_financeiro.excluir_dfc_modulo, name='excluir_dfc_modulo'),
    path('titulos/<int:empresa_id>/', views_financeiro.titulos, name='titulos'),
    path('titulos/<int:empresa_id>/criar/', views_financeiro.criar_titulo_modulo, name='criar_titulo_modulo'),
    path('titulos/<int:empresa_id>/editar/<int:titulo_id>/', views_financeiro.editar_titulo_modulo, name='editar_titulo_modulo'),
    path('titulos/<int:empresa_id>/excluir/<int:titulo_id>/', views_financeiro.excluir_titulo_modulo, name='excluir_titulo_modulo'),
    path('naturezas/<int:empresa_id>/', views_financeiro.naturezas, name='naturezas'),
    path('naturezas/<int:empresa_id>/criar/', views_financeiro.criar_natureza_modulo, name='criar_natureza_modulo'),
    path('naturezas/<int:empresa_id>/editar/<int:natureza_id>/', views_financeiro.editar_natureza_modulo, name='editar_natureza_modulo'),
    path('naturezas/<int:empresa_id>/excluir/<int:natureza_id>/', views_financeiro.excluir_natureza_modulo, name='excluir_natureza_modulo'),
    path('operacoes/<int:empresa_id>/', views_financeiro.operacoes, name='operacoes'),
    path('operacoes/<int:empresa_id>/criar/', views_financeiro.criar_operacao_modulo, name='criar_operacao_modulo'),
    path('operacoes/<int:empresa_id>/editar/<int:operacao_id>/', views_financeiro.editar_operacao_modulo, name='editar_operacao_modulo'),
    path('operacoes/<int:empresa_id>/excluir/<int:operacao_id>/', views_financeiro.excluir_operacao_modulo, name='excluir_operacao_modulo'),
    path('parceiros/<int:empresa_id>/', views_parametros.parceiros, name='parceiros'),
    path('parceiros/<int:empresa_id>/criar/', views_parametros.criar_parceiro_modulo, name='criar_parceiro_modulo'),
    path('parceiros/<int:empresa_id>/editar/<int:parceiro_id>/', views_parametros.editar_parceiro_modulo, name='editar_parceiro_modulo'),
    path('parceiros/<int:empresa_id>/excluir/<int:parceiro_id>/', views_parametros.excluir_parceiro_modulo, name='excluir_parceiro_modulo'),
    path('produtos/<int:empresa_id>/', views_parametros.produtos, name='produtos'),
    path('produtos/<int:empresa_id>/criar/', views_parametros.criar_produto_modulo, name='criar_produto_modulo'),
    path('produtos/<int:empresa_id>/editar/<int:produto_id>/', views_parametros.editar_produto_modulo, name='editar_produto_modulo'),
    path('produtos/<int:empresa_id>/excluir/<int:produto_id>/', views_parametros.excluir_produto_modulo, name='excluir_produto_modulo'),
    path('unidades_federativas/<int:empresa_id>/', views_parametros.unidades_federativas, name='unidades_federativas'),
    path('unidades_federativas/<int:empresa_id>/criar/', views_parametros.criar_unidade_federativa_modulo, name='criar_unidade_federativa_modulo'),
    path('unidades_federativas/<int:empresa_id>/editar/<int:unidade_federativa_id>/', views_parametros.editar_unidade_federativa_modulo, name='editar_unidade_federativa_modulo'),
    path('unidades_federativas/<int:empresa_id>/excluir/<int:unidade_federativa_id>/', views_parametros.excluir_unidade_federativa_modulo, name='excluir_unidade_federativa_modulo'),
    path('rotas/<int:empresa_id>/', views_parametros.rotas, name='rotas'),
    path('rotas/<int:empresa_id>/criar/', views_parametros.criar_rota_modulo, name='criar_rota_modulo'),
    path('rotas/<int:empresa_id>/editar/<int:rota_id>/', views_parametros.editar_rota_modulo, name='editar_rota_modulo'),
    path('rotas/<int:empresa_id>/excluir/<int:rota_id>/', views_parametros.excluir_rota_modulo, name='excluir_rota_modulo'),
    path('motoristas/<int:empresa_id>/', views_parametros.motoristas, name='motoristas'),
    path('motoristas/<int:empresa_id>/criar/', views_parametros.criar_motorista_modulo, name='criar_motorista_modulo'),
    path('motoristas/<int:empresa_id>/editar/<int:motorista_id>/', views_parametros.editar_motorista_modulo, name='editar_motorista_modulo'),
    path('motoristas/<int:empresa_id>/excluir/<int:motorista_id>/', views_parametros.excluir_motorista_modulo, name='excluir_motorista_modulo'),
    path('transportadoras/<int:empresa_id>/', views_parametros.transportadoras, name='transportadoras'),
    path('transportadoras/<int:empresa_id>/criar/', views_parametros.criar_transportadora_modulo, name='criar_transportadora_modulo'),
    path('transportadoras/<int:empresa_id>/editar/<int:transportadora_id>/', views_parametros.editar_transportadora_modulo, name='editar_transportadora_modulo'),
    path('transportadoras/<int:empresa_id>/excluir/<int:transportadora_id>/', views_parametros.excluir_transportadora_modulo, name='excluir_transportadora_modulo'),
    path('descricoes_perfil/<int:empresa_id>/', views_parametros.descricoes_perfil, name='descricoes_perfil'),
    path('descricoes_perfil/<int:empresa_id>/criar/', views_parametros.criar_descricao_perfil_modulo, name='criar_descricao_perfil_modulo'),
    path('descricoes_perfil/<int:empresa_id>/editar/<int:descricao_perfil_id>/', views_parametros.editar_descricao_perfil_modulo, name='editar_descricao_perfil_modulo'),
    path('descricoes_perfil/<int:empresa_id>/excluir/<int:descricao_perfil_id>/', views_parametros.excluir_descricao_perfil_modulo, name='excluir_descricao_perfil_modulo'),
    path('parametros_metas/<int:empresa_id>/', views_parametros.parametros_metas, name='parametros_metas'),
    path('parametros_metas/<int:empresa_id>/criar/', views_parametros.criar_parametro_meta_modulo, name='criar_parametro_meta_modulo'),
    path('parametros_metas/<int:empresa_id>/editar/<int:parametro_meta_id>/', views_parametros.editar_parametro_meta_modulo, name='editar_parametro_meta_modulo'),
    path('parametros_metas/<int:empresa_id>/excluir/<int:parametro_meta_id>/', views_parametros.excluir_parametro_meta_modulo, name='excluir_parametro_meta_modulo'),
    path('parametros_vendas/<int:empresa_id>/', views_parametros.parametros_vendas, name='parametros_vendas'),
    path('parametros_logistica/<int:empresa_id>/', views_parametros.parametros_logistica, name='parametros_logistica'),
    path('parametros_administracao/<int:empresa_id>/', views_parametros.parametros_administracao, name='parametros_administracao'),
    path('parametros_financeiro/<int:empresa_id>/', views_financeiro.parametros_financeiro, name='parametros_financeiro'),
    path('parametros_negocios/<int:empresa_id>/', views_parametros.parametros_negocios, name='parametros_negocios'),
    path('centros_resultado/<int:empresa_id>/', views_financeiro.centros_resultado, name='centros_resultado'),
    path('centros_resultado/<int:empresa_id>/criar/', views_financeiro.criar_centro_resultado_modulo, name='criar_centro_resultado_modulo'),
    path('centros_resultado/<int:empresa_id>/editar/<int:centro_resultado_id>/', views_financeiro.editar_centro_resultado_modulo, name='editar_centro_resultado_modulo'),
    path('centros_resultado/<int:empresa_id>/excluir/<int:centro_resultado_id>/', views_financeiro.excluir_centro_resultado_modulo, name='excluir_centro_resultado_modulo'),
    path('orcamento/<int:empresa_id>/', views_financeiro.orcamento, name='orcamento'),
    path('orcamentos_realizados/<int:empresa_id>/', views_financeiro.orcamentos_realizados, name='orcamentos_realizados'),
    path('orcamentos/<int:empresa_id>/', views_financeiro.orcamentos, name='orcamentos'),
    path('orcamento/<int:empresa_id>/editar/<int:orcamento_id>/', views_financeiro.editar_orcamento_modulo, name='editar_orcamento_modulo'),
    path('orcamento/<int:empresa_id>/excluir/<int:orcamento_id>/', views_financeiro.excluir_orcamento_modulo, name='excluir_orcamento_modulo'),
    path('orcamentos/<int:empresa_id>/editar/<int:orcamento_planejado_id>/', views_financeiro.editar_orcamento_planejado_modulo, name='editar_orcamento_planejado_modulo'),
    path('orcamentos/<int:empresa_id>/excluir/<int:orcamento_planejado_id>/', views_financeiro.excluir_orcamento_planejado_modulo, name='excluir_orcamento_planejado_modulo'),
    path('adiantamentos/<int:empresa_id>/', views_financeiro.adiantamentos, name='adiantamentos'),
    path('adiantamentos/<int:empresa_id>/editar/<int:adiantamento_id>/', views_financeiro.editar_adiantamento_modulo, name='editar_adiantamento_modulo'),
    path('adiantamentos/<int:empresa_id>/excluir/<int:adiantamento_id>/', views_financeiro.excluir_adiantamento_modulo, name='excluir_adiantamento_modulo'),
    path('contratos_redes/<int:empresa_id>/', views_financeiro.contratos_redes, name='contratos_redes'),
    path('contratos_redes/<int:empresa_id>/mascara/', views_financeiro.mascara_contrato_rede, name='mascara_contrato_rede'),
    path('contratos_redes/<int:empresa_id>/criar/', views_financeiro.criar_contrato_rede_modulo, name='criar_contrato_rede_modulo'),
    path('contratos_redes/<int:empresa_id>/editar/<int:contrato_id>/', views_financeiro.editar_contrato_rede_modulo, name='editar_contrato_rede_modulo'),
    path('contratos_redes/<int:empresa_id>/excluir/<int:contrato_id>/', views_financeiro.excluir_contrato_rede_modulo, name='excluir_contrato_rede_modulo'),


    # Modulos - Administrativo
    path('plano_de_cargos_e_salarios/<int:empresa_id>/', views_administrativo.plano_de_cargos_e_salarios, name='plano_de_cargos_e_salarios'),
    path('plano_de_cargos_e_salarios/<int:empresa_id>/criar/', views_administrativo.criar_plano_cargo_salario_modulo, name='criar_plano_cargo_salario_modulo'),
    path('plano_de_cargos_e_salarios/<int:empresa_id>/editar/<int:plano_cargo_salario_id>/', views_administrativo.editar_plano_cargo_salario_modulo, name='editar_plano_cargo_salario_modulo'),
    path('plano_de_cargos_e_salarios/<int:empresa_id>/excluir/<int:plano_cargo_salario_id>/', views_administrativo.excluir_plano_cargo_salario_modulo, name='excluir_plano_cargo_salario_modulo'),
    path('descritivos/<int:empresa_id>/', views_administrativo.descritivos, name='descritivos'),
    path('descritivos/<int:empresa_id>/criar/', views_administrativo.criar_descritivo_modulo, name='criar_descritivo_modulo'),
    path('descritivos/<int:empresa_id>/editar/<int:descritivo_id>/', views_administrativo.editar_descritivo_modulo, name='editar_descritivo_modulo'),
    path('descritivos/<int:empresa_id>/excluir/<int:descritivo_id>/', views_administrativo.excluir_descritivo_modulo, name='excluir_descritivo_modulo'),
    #TOFU
    path('tofu_lista_de_atividades/<int:empresa_id>/', views_administrativo.tofu_lista_de_atividades, name='tofu_lista_de_atividades'),
    path('tofu_lista_de_atividades/<int:empresa_id>/criar/', views_administrativo.criar_atividade_tofu, name='criar_atividade_tofu'),
    path('tofu_lista_de_atividades/<int:empresa_id>/editar/<int:atividade_id>/', views_administrativo.editar_atividade_tofu, name='editar_atividade_tofu'),
    path('tofu_lista_de_atividades/<int:empresa_id>/excluir/<int:atividade_id>/', views_administrativo.excluir_atividade_tofu, name='excluir_atividade_tofu'),

    path('fiscal_e_contabil/<int:empresa_id>/', views_administrativo.fiscal_e_contabil, name='fiscal_e_contabil'),
    path('faturamento/<int:empresa_id>/', views_administrativo.faturamento, name='faturamento'),
    path(
        'faturamento/<int:empresa_id>/dashboard-pdf/',
        views_administrativo.faturamento_dashboard_pdf,
        name='faturamento_dashboard_pdf',
    ),
    path('faturamento/<int:empresa_id>/editar/<int:faturamento_id>/', views_administrativo.editar_faturamento_modulo, name='editar_faturamento_modulo'),
    path('faturamento/<int:empresa_id>/excluir/<int:faturamento_id>/', views_administrativo.excluir_faturamento_modulo, name='excluir_faturamento_modulo'),
    path('apuracao_de_resultados/<int:empresa_id>/', views_administrativo.apuracao_de_resultados, name='apuracao_de_resultados'),
    path('orcamento_x_realizado/<int:empresa_id>/', views_administrativo.orcamento_x_realizado, name='orcamento_x_realizado'),
    #Colaboradores
    path('colaboradores/<int:empresa_id>/', views_administrativo.colaboradores, name='colaboradores'),
    path('colaboradores/<int:empresa_id>/criar/', views_administrativo.criar_colaborador_modulo, name='criar_colaborador_modulo'),
    path('colaboradores/<int:empresa_id>/editar/<int:colaborador_id>/', views_administrativo.editar_colaborador_modulo, name='editar_colaborador_modulo'),
    path('colaboradores/<int:empresa_id>/excluir/<int:colaborador_id>/', views_administrativo.excluir_colaborador_modulo, name='excluir_colaborador_modulo'),
    #Projetos
    path('projetos/<int:empresa_id>/', views_administrativo.projetos, name='projetos'),
    path('projetos/<int:empresa_id>/criar/', views_administrativo.criar_projeto_modulo, name='criar_projeto_modulo'),
    path('projetos/<int:empresa_id>/editar/<int:projeto_id>/', views_administrativo.editar_projeto_modulo, name='editar_projeto_modulo'),
    path('projetos/<int:empresa_id>/excluir/<int:projeto_id>/', views_administrativo.excluir_projeto_modulo, name='excluir_projeto_modulo'),
    # Modulos - Comercial
    path('carteira/<int:empresa_id>/', views_comercial.carteira, name='carteira'),
    path('carteira/<int:empresa_id>/editar/<int:carteira_id>/', views_comercial.editar_carteira_modulo, name='editar_carteira_modulo'),
    path('carteira/<int:empresa_id>/excluir/<int:carteira_id>/', views_comercial.excluir_carteira_modulo, name='excluir_carteira_modulo'),
    path('cidades/<int:empresa_id>/', views_comercial.cidades, name='cidades'),
    path('cidades/<int:empresa_id>/criar/', views_comercial.criar_cidade_modulo, name='criar_cidade_modulo'),
    path('cidades/<int:empresa_id>/editar/<int:cidade_id>/', views_comercial.editar_cidade_modulo, name='editar_cidade_modulo'),
    path('cidades/<int:empresa_id>/excluir/<int:cidade_id>/', views_comercial.excluir_cidade_modulo, name='excluir_cidade_modulo'),
    path('regioes/<int:empresa_id>/', views_comercial.regioes, name='regioes'),
    path('regioes/<int:empresa_id>/criar/', views_comercial.criar_regiao_modulo, name='criar_regiao_modulo'),
    path('regioes/<int:empresa_id>/editar/<int:regiao_id>/', views_comercial.editar_regiao_modulo, name='editar_regiao_modulo'),
    path('regioes/<int:empresa_id>/excluir/<int:regiao_id>/', views_comercial.excluir_regiao_modulo, name='excluir_regiao_modulo'),
    path('pedidos_pendentes/<int:empresa_id>/', views_comercial.pedidos_pendentes, name='pedidos_pendentes'),
    path('pedidos_pendentes/<int:empresa_id>/editar/<int:pedido_id>/', views_comercial.editar_pedido_pendente_modulo, name='editar_pedido_pendente_modulo'),
    path('pedidos_pendentes/<int:empresa_id>/excluir/<int:pedido_id>/', views_comercial.excluir_pedido_pendente_modulo, name='excluir_pedido_pendente_modulo'),
    path('agenda/<int:empresa_id>/', views_comercial.agenda, name='agenda'),
    path('agenda/<int:empresa_id>/editar/<int:agenda_id>/', views_comercial.editar_agenda_modulo, name='editar_agenda_modulo'),
    path('agenda/<int:empresa_id>/excluir/<int:agenda_id>/', views_comercial.excluir_agenda_modulo, name='excluir_agenda_modulo'),
    path('vendas_por_categoria/<int:empresa_id>/', views_comercial.vendas_por_categoria, name='vendas_por_categoria'),
    path('vendas_por_categoria/<int:empresa_id>/editar/<int:venda_id>/', views_comercial.editar_venda_modulo, name='editar_venda_modulo'),
    path('vendas_por_categoria/<int:empresa_id>/excluir/<int:venda_id>/', views_comercial.excluir_venda_modulo, name='excluir_venda_modulo'),
    path('precificacao/<int:empresa_id>/', views_comercial.precificacao, name='precificacao'),
    path('controle_de_margem/<int:empresa_id>/', views_comercial.controle_de_margem, name='controle_de_margem'),
    path('controle_de_margem/<int:empresa_id>/editar/<int:controle_id>/', views_comercial.editar_controle_margem_modulo, name='editar_controle_margem_modulo'),
    path('controle_de_margem/<int:empresa_id>/excluir/<int:controle_id>/', views_comercial.excluir_controle_margem_modulo, name='excluir_controle_margem_modulo'),


    # Modulos - Operacional
    path('cargas_em_aberto/<int:empresa_id>/', views_operacional.cargas_em_aberto, name='cargas_em_aberto'),
    path('cargas_em_aberto/<int:empresa_id>/editar/<int:carga_id>/', views_operacional.editar_carga_modulo, name='editar_carga_modulo'),
    path('cargas_em_aberto/<int:empresa_id>/excluir/<int:carga_id>/', views_operacional.excluir_carga_modulo, name='excluir_carga_modulo'),
    path('operador_logistico/<int:empresa_id>/', views_operacional.operador_logistico, name='operador_logistico'),
    path('tabela_de_fretes/<int:empresa_id>/', views_operacional.tabela_de_fretes, name='tabela_de_fretes'),
    path('tabela_de_fretes/<int:empresa_id>/editar/<int:frete_id>/', views_operacional.editar_frete_modulo, name='editar_frete_modulo'),
    path('tabela_de_fretes/<int:empresa_id>/excluir/<int:frete_id>/', views_operacional.excluir_frete_modulo, name='excluir_frete_modulo'),
    path('estoque_pcp/<int:empresa_id>/', views_operacional.estoque_pcp, name='estoque_pcp'),
    path('estoque_pcp/<int:empresa_id>/editar/<int:estoque_id>/', views_operacional.editar_estoque_modulo, name='editar_estoque_modulo'),
    path('estoque_pcp/<int:empresa_id>/excluir/<int:estoque_id>/', views_operacional.excluir_estoque_modulo, name='excluir_estoque_modulo'),
    path('producao/<int:empresa_id>/', views_operacional.producao, name='producao'),
    path('producao/<int:empresa_id>/editar/<int:producao_id>/', views_operacional.editar_producao_modulo, name='editar_producao_modulo'),
    path('producao/<int:empresa_id>/excluir/<int:producao_id>/', views_operacional.excluir_producao_modulo, name='excluir_producao_modulo'),
]
