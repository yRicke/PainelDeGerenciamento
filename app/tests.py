from django.test import TestCase
from django.test import override_settings
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
import shutil
from uuid import uuid4
from pathlib import Path
from unittest.mock import patch
from .models import Atividade, Cargas, Carteira, Cidade, Colaborador, Empresa, Parceiro, Permissao, Projeto, Regiao, Usuario, Venda
from .services import (
    atualizar_carga_por_post,
    criar_carga_por_post,
    preparar_diretorios_cargas,
    preparar_diretorios_vendas,
    importar_upload_cargas,
    importar_upload_vendas,
)

# Create your tests here.

class EmpresaModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")

    def test_criar_empresa(self):
        self.assertEqual(self.empresa.nome, "Empresa Teste")

    def test_atualizar_nome(self):
        self.empresa.atualizar_nome(novo_nome="Nova Empresa")
        self.assertEqual(self.empresa.nome, "Nova Empresa")

    def test_excluir_empresa(self):
        self.empresa.excluir_empresa()
        self.assertFalse(Empresa.objects.filter(id=self.empresa.id).exists())

class UsuarioModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")
        self.permissao_menu = Permissao.objects.create(nome="Menu Inicial")
        self.permissao_dre = Permissao.objects.create(nome="DRE")
        self.usuario = Usuario.criar_usuario(
            username="usuario_teste",
            password="senha123",
            empresa=self.empresa,
            permissoes=[self.permissao_menu],
        )
    
    def test_criar_usuario(self):
        self.assertEqual(self.usuario.username, "usuario_teste")
        self.assertTrue(self.usuario.check_password("senha123"))
        self.assertEqual(self.usuario.empresa, self.empresa)
        self.assertIn(self.permissao_menu, self.usuario.permissoes.all())
        self.assertNotIn(self.permissao_dre, self.usuario.permissoes.all())

    def test_atualizar_usuario(self):
        self.usuario.atualizar_usuario(
            username="novo_usuario",
            password="nova_senha",
            permissoes=[self.permissao_dre]
        )
        self.assertEqual(self.usuario.username, "novo_usuario")
        self.assertTrue(self.usuario.check_password("nova_senha"))
        self.assertNotIn(self.permissao_menu, self.usuario.permissoes.all())
        self.assertIn(self.permissao_dre, self.usuario.permissoes.all())

    def test_listar_usuarios_por_empresa(self):
        usuario2 = Usuario.criar_usuario(
            username="usuario_teste2",
            password="senha123",
            empresa=self.empresa,
            permissoes=[self.permissao_dre],
        )
        usuarios = Usuario.listar_usuarios_por_empresa(self.empresa)
        self.assertIn(self.usuario, usuarios)
        self.assertIn(usuario2, usuarios)
        self.assertIn(self.permissao_dre, usuario2.permissoes.all())

    def test_excluir_usuario(self):
        self.usuario.excluir_usuario()
        self.assertFalse(Usuario.objects.filter(id=self.usuario.id).exists())

    def test_criar_usuario_sem_permissoes(self):
        usuario = Usuario.criar_usuario(
            username="sem_permissoes",
            password="senha123",
            empresa=self.empresa,
        )
        self.assertEqual(usuario.permissoes.count(), 0)

class ColaboradorModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")
        self.colaborador = Colaborador.criar_colaborador(empresa=self.empresa, nome="Colaborador Teste")

    def test_criar_colaborador(self):
        self.assertEqual(self.colaborador.nome, "Colaborador Teste")
        self.assertEqual(self.colaborador.empresa, self.empresa)

    def test_atualizar_colaborador(self):
        self.colaborador.atualizar_colaborador(novo_nome="Novo Colaborador")
        self.assertEqual(self.colaborador.nome, "Novo Colaborador")

    def test_listar_colaboradores_por_empresa(self):
        colaborador2 = Colaborador.criar_colaborador(empresa=self.empresa, nome="Colaborador Teste 2")
        colaboradores = Colaborador.listar_colaboradores_por_empresa(self.empresa)
        self.assertIn(self.colaborador, colaboradores)
        self.assertIn(colaborador2, colaboradores)

    def test_excluir_colaborador(self):
        self.colaborador.excluir_colaborador()
        self.assertFalse(Colaborador.objects.filter(id=self.colaborador.id).exists())

class ProjetoModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")
        self.projeto = Projeto.criar_projeto(empresa=self.empresa, nome="Projeto Teste", codigo="PRJ")

    def test_criar_projeto(self):
        self.assertEqual(self.projeto.nome, "Projeto Teste")
        self.assertEqual(self.projeto.codigo, "PRJ")
        self.assertEqual(self.projeto.empresa, self.empresa)

    def test_atualizar_projeto(self):
        self.projeto.atualizar_projeto(novo_nome="Novo Projeto", novo_codigo="NPRJ")
        self.assertEqual(self.projeto.nome, "Novo Projeto")
        self.assertEqual(self.projeto.codigo, "NPRJ")

    def test_listar_projetos_por_empresa(self):
        projeto2 = Projeto.criar_projeto(empresa=self.empresa, nome="Projeto Teste 2", codigo="PRJ2")
        projetos = Projeto.listar_projetos_por_empresa(self.empresa)
        self.assertIn(self.projeto, projetos)
        self.assertIn(projeto2, projetos)

    def test_excluir_projeto(self):
        self.projeto.excluir_projeto()
        self.assertFalse(Projeto.objects.filter(id=self.projeto.id).exists())

class AtividadeModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")
        self.projeto = Projeto.criar_projeto(empresa=self.empresa, nome="Projeto Teste", codigo="PRJ")
        self.colaborador1 = Colaborador.criar_colaborador(empresa=self.empresa, nome="Colaborador 1")
        self.colaborador2 = Colaborador.criar_colaborador(empresa=self.empresa, nome="Colaborador 2")
        self.atividade = Atividade.criar_atividade(
            projeto=self.projeto,
            gestor=self.colaborador1,
            responsavel=self.colaborador2,
            interlocutor="Interlocutor Teste",
            semana_de_prazo=27,
            data_previsao_inicio="2024-07-01",
            data_previsao_termino="2024-07-31",
            data_finalizada=None,
            historico="",
            tarefa="Tarefa Teste",
            progresso=0
        )

    def test_criar_atividade(self):
        self.assertEqual(self.atividade.projeto, self.projeto)
        self.assertEqual(self.atividade.gestor, self.colaborador1)
        self.assertEqual(self.atividade.responsavel, self.colaborador2)
        self.assertEqual(self.atividade.interlocutor, "Interlocutor Teste")
        self.assertEqual(self.atividade.semana_de_prazo, 27)
        self.assertEqual(str(self.atividade.data_previsao_inicio), "2024-07-01")
        self.assertEqual(str(self.atividade.data_previsao_termino), "2024-07-31")
        self.assertIsNone(self.atividade.data_finalizada)
        self.assertEqual(self.atividade.historico, "")
        self.assertEqual(self.atividade.tarefa, "Tarefa Teste")
        self.assertEqual(self.atividade.progresso, 0)

    def test_atualizar_atividade(self):
        projeto2 = Projeto.criar_projeto(empresa=self.empresa, nome="Projeto Atualizado", codigo="PRJ2")
        colaborador3 = Colaborador.criar_colaborador(empresa=self.empresa, nome="Colaborador 3")
        colaborador4 = Colaborador.criar_colaborador(empresa=self.empresa, nome="Colaborador 4")
        self.atividade.atualizar_atividade(
            projeto= projeto2,
            gestor= colaborador4,
            responsavel=colaborador3,
            interlocutor="Novo Interlocutor",
            semana_de_prazo=31,
            data_previsao_inicio="2024-08-01",
            data_previsao_termino="2024-08-31",
            data_finalizada="2024-08-15",
            historico="Histórico atualizado",
            tarefa="Tarefa atualizada",
            progresso=100
        )
        self.assertEqual(self.atividade.projeto, projeto2)
        self.assertEqual(self.atividade.gestor, colaborador4)
        self.assertEqual(self.atividade.responsavel, colaborador3)
        self.assertEqual(self.atividade.interlocutor, "Novo Interlocutor")
        self.assertEqual(self.atividade.semana_de_prazo, 31)
        self.assertEqual(str(self.atividade.data_previsao_inicio), "2024-08-01")
        self.assertEqual(str(self.atividade.data_previsao_termino), "2024-08-31")
        self.assertEqual(str(self.atividade.data_finalizada), "2024-08-15")
        self.assertEqual(self.atividade.historico, "Histórico atualizado")
        self.assertEqual(self.atividade.tarefa, "Tarefa atualizada")
        self.assertEqual(self.atividade.progresso, 100)
        
    def test_excluir_atividade(self):
        self.atividade.excluir_atividade()
        self.assertFalse(Atividade.objects.filter(id=self.atividade.id).exists())

    def test_indicador_concluido(self):
        self.atividade.progresso = 100
        self.assertEqual(self.atividade.indicador, Atividade.INDICADOR_CONCLUIDO)

    def test_indicador_atrasado(self):
        self.atividade.progresso = 50
        self.atividade.data_previsao_termino = timezone.localdate() - timedelta(days=1)
        self.assertEqual(self.atividade.indicador, Atividade.INDICADOR_ATRASADO)

    def test_indicador_alerta(self):
        self.atividade.progresso = 50
        hoje = timezone.localdate()
        inicio_semana_atual = hoje - timedelta(days=hoje.isoweekday() - 1)
        fim_proxima_semana = inicio_semana_atual + timedelta(days=13)
        self.atividade.data_previsao_termino = fim_proxima_semana
        self.assertEqual(self.atividade.indicador, Atividade.INDICADOR_ALERTA)

    def test_indicador_a_fazer(self):
        self.atividade.progresso = 50
        hoje = timezone.localdate()
        inicio_semana_atual = hoje - timedelta(days=hoje.isoweekday() - 1)
        inicio_duas_semanas_apos = inicio_semana_atual + timedelta(days=14)
        self.atividade.data_previsao_termino = inicio_duas_semanas_apos
        self.assertEqual(self.atividade.indicador, Atividade.INDICADOR_A_FAZER)

    def test_nao_permite_data_finalizada_com_progresso_menor_que_100_em_criacao(self):
        with self.assertRaises(ValidationError):
            Atividade.criar_atividade(
                projeto=self.projeto,
                gestor=self.colaborador1,
                responsavel=self.colaborador2,
                data_finalizada=timezone.localdate(),
                progresso=50,
            )

    def test_nao_permite_data_finalizada_com_progresso_menor_que_100_em_atualizacao(self):
        with self.assertRaises(ValidationError):
            self.atividade.atualizar_atividade(
                data_finalizada=timezone.localdate(),
                progresso=80,
            )

    def test_limpar_data_finalizada_na_atualizacao(self):
        hoje = timezone.localdate()
        self.atividade.atualizar_atividade(data_finalizada=hoje, progresso=100)
        self.assertEqual(self.atividade.data_finalizada, hoje)

        self.atividade.atualizar_atividade(data_finalizada=None, progresso=80)
        self.assertIsNone(self.atividade.data_finalizada)


class CidadeModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")
        self.cidade = Cidade.criar_cidade(nome="Sao Paulo", empresa=self.empresa, codigo="1001")

    def test_criar_cidade(self):
        self.assertEqual(self.cidade.nome, "Sao Paulo")
        self.assertEqual(self.cidade.codigo, "1001")
        self.assertEqual(self.cidade.empresa, self.empresa)

    def test_atualizar_cidade(self):
        self.cidade.atualizar_cidade(novo_nome="Campinas", novo_codigo="1002")
        self.assertEqual(self.cidade.nome, "Campinas")
        self.assertEqual(self.cidade.codigo, "1002")

    def test_excluir_cidade(self):
        self.cidade.excluir_cidade()
        self.assertFalse(Cidade.objects.filter(id=self.cidade.id).exists())


class RegiaoModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")
        self.regiao = Regiao.criar_regiao(nome="Sudeste", empresa=self.empresa, codigo="RG0001")

    def test_criar_regiao(self):
        self.assertEqual(self.regiao.nome, "Sudeste")
        self.assertEqual(self.regiao.codigo, "RG0001")
        self.assertEqual(self.regiao.empresa, self.empresa)

    def test_atualizar_regiao(self):
        self.regiao.atualizar_regiao(novo_nome="Centro-Oeste", novo_codigo="RG0002")
        self.assertEqual(self.regiao.nome, "Centro-Oeste")
        self.assertEqual(self.regiao.codigo, "RG0002")

    def test_excluir_regiao(self):
        self.regiao.excluir_regiao()
        self.assertFalse(Regiao.objects.filter(id=self.regiao.id).exists())


class ParceiroModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")
        self.parceiro = Parceiro.criar_parceiro(nome="Parceiro Teste", codigo="100", empresa=self.empresa)

    def test_criar_parceiro(self):
        self.assertEqual(self.parceiro.nome, "Parceiro Teste")
        self.assertEqual(self.parceiro.codigo, "100")
        self.assertEqual(self.parceiro.empresa, self.empresa)

    def test_atualizar_parceiro(self):
        self.parceiro.atualizar_parceiro(novo_nome="Parceiro Novo", novo_codigo="101")
        self.assertEqual(self.parceiro.nome, "Parceiro Novo")
        self.assertEqual(self.parceiro.codigo, "101")

    def test_excluir_parceiro(self):
        self.parceiro.excluir_parceiro()
        self.assertFalse(Parceiro.objects.filter(id=self.parceiro.id).exists())


class CarteiraModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")
        self.regiao = Regiao.criar_regiao(nome="Sudeste", empresa=self.empresa, codigo="RG1001")
        self.cidade = Cidade.criar_cidade(nome="Sao Paulo", empresa=self.empresa, codigo="2001")
        self.parceiro = Parceiro.criar_parceiro(nome="Parceiro 1", codigo="3001", empresa=self.empresa)
        self.carteira = Carteira.criar_carteira(
            empresa=self.empresa,
            regiao=self.regiao,
            cidade=self.cidade,
            parceiro=self.parceiro,
            gerente="Gerente 1",
            vendedor="Vendedor 1",
            ativo_indicador=True,
        )

    def test_criar_carteira(self):
        self.assertEqual(self.carteira.parceiro, self.parceiro)
        self.assertEqual(self.carteira.regiao, self.regiao)
        self.assertEqual(self.carteira.cidade, self.cidade)
        self.assertEqual(self.carteira.vendedor, "Vendedor 1")

    def test_atualizar_carteira(self):
        parceiro_2 = Parceiro.criar_parceiro(nome="Parceiro 2", codigo="3002", empresa=self.empresa)
        self.carteira.atualizar_carteira(
            parceiro=parceiro_2,
            gerente="Gerente 2",
            vendedor="Vendedor 2",
            cliente_indicador=True,
        )
        self.assertEqual(self.carteira.parceiro, parceiro_2)
        self.assertEqual(self.carteira.gerente, "Gerente 2")
        self.assertEqual(self.carteira.vendedor, "Vendedor 2")
        self.assertTrue(self.carteira.cliente_indicador)

    def test_excluir_carteira(self):
        self.carteira.excluir_carteira()
        self.assertFalse(Carteira.objects.filter(id=self.carteira.id).exists())


class VendaModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")
        self.venda = Venda.criar_venda(
            empresa=self.empresa,
            codigo="VD001",
            descricao="Venda categoria A",
            valor_venda=1000,
            qtd_notas=2,
            custo_medio_icms_cmv=850,
            peso_bruto=100,
            peso_liquido=95,
            data_venda=timezone.localdate(),
        )

    def test_criar_venda(self):
        self.assertEqual(self.venda.codigo, "VD001")
        self.assertEqual(self.venda.descricao, "Venda categoria A")
        self.assertEqual(self.venda.qtd_notas, 2)
        self.assertEqual(round(float(self.venda.lucro), 2), 150.0)
        self.assertEqual(round(float(self.venda.margem), 2), 15.0)

    def test_atualizar_venda(self):
        self.venda.atualizar_venda(
            codigo="VD002",
            descricao="Venda categoria B",
            valor_venda=2000,
            custo_medio_icms_cmv=1700,
            qtd_notas=4,
            peso_bruto=210,
            peso_liquido=200,
        )
        self.assertEqual(self.venda.codigo, "VD002")
        self.assertEqual(self.venda.descricao, "Venda categoria B")
        self.assertEqual(self.venda.qtd_notas, 4)
        self.assertEqual(round(float(self.venda.lucro), 2), 300.0)
        self.assertEqual(round(float(self.venda.margem), 2), 15.0)

    def test_excluir_venda(self):
        venda_id = self.venda.id
        self.venda.excluir_venda()
        self.assertFalse(Venda.objects.filter(id=venda_id).exists())


class CargasModelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste")
        self.regiao = Regiao.criar_regiao(nome="Sul", empresa=self.empresa, codigo="RG2001")
        self.data_inicio = timezone.localdate() - timedelta(days=10)
        self.carga = Cargas.criar_carga(
            empresa=self.empresa,
            situacao="Em Aberto",
            ordem_de_carga_codigo="OC123",
            data_inicio=self.data_inicio,
            data_prevista_saida=timezone.localdate(),
            nome_motorista="Motorista Teste",
            nome_fantasia_empresa="Cliente Teste",
            regiao=self.regiao,
            prazo_maximo_dias=7,
        )

    def test_criar_carga_calcula_indicadores(self):
        self.assertEqual(self.carga.idade_dias, 10)
        self.assertTrue(self.carga.verificacao)
        self.assertEqual(self.carga.critica, 3)

    def test_atualizar_carga_recalcula_indicadores(self):
        self.carga.atualizar_carga(
            data_inicio=timezone.localdate() - timedelta(days=2),
            prazo_maximo_dias=5,
        )
        self.assertEqual(self.carga.idade_dias, 2)
        self.assertFalse(self.carga.verificacao)
        self.assertEqual(self.carga.critica, -3)

    def test_verificacao_true_quando_critica_maior_que_zero(self):
        self.assertGreater(self.carga.critica, 0)
        self.assertTrue(self.carga.verificacao)

    def test_verificacao_false_quando_critica_menor_que_zero(self):
        self.carga.atualizar_carga(
            data_inicio=timezone.localdate() - timedelta(days=1),
            prazo_maximo_dias=5,
        )
        self.assertLess(self.carga.critica, 0)
        self.assertFalse(self.carga.verificacao)

    def test_prazo_maximo_padrao_deve_ser_dez(self):
        carga_padrao = Cargas.criar_carga(
            empresa=self.empresa,
            situacao="Aberta",
            ordem_de_carga_codigo="OCPADRAO",
            data_inicio=timezone.localdate(),
            data_prevista_saida=timezone.localdate(),
            nome_fantasia_empresa="Cliente",
        )
        self.assertEqual(carga_padrao.prazo_maximo_dias, 10)

    def test_excluir_carga(self):
        carga_id = self.carga.id
        self.carga.excluir_carga()
        self.assertFalse(Cargas.objects.filter(id=carga_id).exists())


class VendasImportacaoServiceTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste Importacao")
        self.base_dir = str((Path(settings.BASE_DIR) / f".tmp_test_vendas_{uuid4().hex}"))
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(self.base_dir, ignore_errors=True))

    def test_preparar_diretorios_vendas_cria_estrutura(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_vendas()
            self.assertTrue(diretorio_importacao.exists())
            self.assertTrue(diretorio_subscritos.exists())
            self.assertEqual(diretorio_subscritos.parent, diretorio_importacao)

    def test_importar_upload_vendas_mantem_apenas_novos_e_move_antigos(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_vendas()
            antigo = diretorio_importacao / "01.01.2026.xls"
            antigo.write_bytes(b"arquivo-antigo")

            arquivo_a = SimpleUploadedFile("02.01.2026.xls", b"novo-a", content_type="application/vnd.ms-excel")
            arquivo_b = SimpleUploadedFile("03.01.2026.xls", b"novo-b", content_type="application/vnd.ms-excel")
            arquivo_invalido = SimpleUploadedFile("nao_importar.txt", b"xx", content_type="text/plain")

            with patch("app.services.importar_vendas_do_diretorio") as importar_mock:
                importar_mock.return_value = {"arquivos": 2, "linhas": 2, "vendas": 2}
                ok, mensagem = importar_upload_vendas(
                    empresa=self.empresa,
                    arquivos=[arquivo_a, arquivo_b, arquivo_invalido],
                    diretorio_importacao=diretorio_importacao,
                    diretorio_subscritos=diretorio_subscritos,
                )

            self.assertTrue(ok)
            self.assertIn("Importacao concluida", mensagem)
            self.assertTrue((diretorio_importacao / "02.01.2026.xls").exists())
            self.assertTrue((diretorio_importacao / "03.01.2026.xls").exists())
            self.assertFalse((diretorio_importacao / "nao_importar.txt").exists())
            self.assertTrue((diretorio_subscritos / "01.01.2026.xls").exists())
            importar_mock.assert_called_once()

    def test_importar_upload_vendas_sem_xls_retorna_erro(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_vendas()
            arquivo_invalido = SimpleUploadedFile("arquivo.csv", b"1,2,3", content_type="text/csv")

            ok, mensagem = importar_upload_vendas(
                empresa=self.empresa,
                arquivos=[arquivo_invalido],
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
            )

            self.assertFalse(ok)
            self.assertIn("arquivo .xls", mensagem)


class CargasImportacaoServiceTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste Importacao Cargas")
        self.base_dir = str((Path(settings.BASE_DIR) / f".tmp_test_cargas_{uuid4().hex}"))
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(self.base_dir, ignore_errors=True))

    def test_preparar_diretorios_cargas_cria_estrutura(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_cargas()
            self.assertTrue(diretorio_importacao.exists())
            self.assertTrue(diretorio_subscritos.exists())
            self.assertEqual(diretorio_subscritos.parent, diretorio_importacao)

    def test_importar_upload_cargas_mantem_apenas_novo_e_move_antigo(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_cargas()
            antigo = diretorio_importacao / "cargas_antigo.xls"
            antigo.write_bytes(b"arquivo-antigo")

            arquivo = SimpleUploadedFile("cargas_novo.xls", b"novo", content_type="application/vnd.ms-excel")

            with patch("app.services.importar_cargas_do_diretorio") as importar_mock:
                importar_mock.return_value = {"arquivos": 1, "linhas": 1, "cargas": 1}
                ok, mensagem = importar_upload_cargas(
                    empresa=self.empresa,
                    arquivo=arquivo,
                    confirmar_substituicao=True,
                    diretorio_importacao=diretorio_importacao,
                    diretorio_subscritos=diretorio_subscritos,
                )

            self.assertTrue(ok)
            self.assertIn("Importacao concluida", mensagem)
            self.assertTrue((diretorio_importacao / "cargas_novo.xls").exists())
            self.assertTrue((diretorio_subscritos / "cargas_antigo.xls").exists())
            importar_mock.assert_called_once()

    def test_importar_upload_cargas_sem_confirmacao_retorna_erro(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_cargas()
            (diretorio_importacao / "cargas_antigo.xls").write_bytes(b"arquivo-antigo")
            arquivo = SimpleUploadedFile("cargas_novo.xls", b"novo", content_type="application/vnd.ms-excel")

            ok, mensagem = importar_upload_cargas(
                empresa=self.empresa,
                arquivo=arquivo,
                confirmar_substituicao=False,
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
            )

            self.assertFalse(ok)
            self.assertIn("Confirme a substituicao", mensagem)


class CargasCrudServiceTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Service Cargas")
        self.regiao = Regiao.criar_regiao(nome="Nordeste", empresa=self.empresa, codigo="RG5555")

    def test_criar_carga_por_post(self):
        erro = criar_carga_por_post(
            self.empresa,
            {
                "situacao": "Aberta",
                "ordem_de_carga_codigo": "OC900",
                "data_inicio": timezone.localdate().strftime("%Y-%m-%d"),
                "data_prevista_saida": timezone.localdate().strftime("%Y-%m-%d"),
                "nome_motorista": "Motorista X",
                "nome_fantasia_empresa": "Empresa X",
                "regiao_id": str(self.regiao.id),
                "prazo_maximo_dias": "",
            },
        )
        self.assertEqual(erro, "")
        carga = Cargas.objects.get(ordem_de_carga_codigo="OC900", empresa=self.empresa)
        self.assertEqual(carga.prazo_maximo_dias, 10)

    def test_atualizar_carga_por_post(self):
        carga = Cargas.criar_carga(
            empresa=self.empresa,
            situacao="Aberta",
            ordem_de_carga_codigo="OC901",
            data_inicio=timezone.localdate(),
            data_prevista_saida=timezone.localdate(),
            nome_fantasia_empresa="Empresa Y",
            prazo_maximo_dias=10,
        )
        erro = atualizar_carga_por_post(
            carga,
            self.empresa,
            {
                "situacao": "Fechada",
                "ordem_de_carga_codigo": "OC901A",
                "data_inicio": timezone.localdate().strftime("%Y-%m-%d"),
                "data_prevista_saida": timezone.localdate().strftime("%Y-%m-%d"),
                "nome_motorista": "Motorista Y",
                "nome_fantasia_empresa": "Empresa Y",
                "regiao_id": str(self.regiao.id),
                "prazo_maximo_dias": "15",
            },
        )
        self.assertEqual(erro, "")
        carga.refresh_from_db()
        self.assertEqual(carga.situacao, "Fechada")
        self.assertEqual(carga.ordem_de_carga_codigo, "OC901A")
        self.assertEqual(carga.prazo_maximo_dias, 15)

    def test_nao_permite_data_finalizacao_sem_data_chegada(self):
        erro = criar_carga_por_post(
            self.empresa,
            {
                "situacao": "Aberta",
                "ordem_de_carga_codigo": "OC902",
                "data_inicio": timezone.localdate().strftime("%Y-%m-%d"),
                "data_prevista_saida": timezone.localdate().strftime("%Y-%m-%d"),
                "data_finalizacao": timezone.localdate().strftime("%Y-%m-%d"),
                "nome_fantasia_empresa": "Empresa Z",
            },
        )
        self.assertIn("Data de finalizacao", erro)
