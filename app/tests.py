from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from .models import Empresa, Usuario, Permissao, Colaborador, Projeto, Atividade

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
            data_previsao_inicio="2024-08-01",
            data_previsao_termino="2024-08-31",
            data_finalizada="2024-08-15",
            historico="Histórico atualizado",
            tarefa="Tarefa atualizada",
            progresso=50
        )
        self.assertEqual(self.atividade.projeto, projeto2)
        self.assertEqual(self.atividade.gestor, colaborador4)
        self.assertEqual(self.atividade.responsavel, colaborador3)
        self.assertEqual(self.atividade.interlocutor, "Novo Interlocutor")
        self.assertEqual(str(self.atividade.data_previsao_inicio), "2024-08-01")
        self.assertEqual(str(self.atividade.data_previsao_termino), "2024-08-31")
        self.assertEqual(str(self.atividade.data_finalizada), "2024-08-15")
        self.assertEqual(self.atividade.historico, "Histórico atualizado")
        self.assertEqual(self.atividade.tarefa, "Tarefa atualizada")
        self.assertEqual(self.atividade.progresso, 50)
        
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

    def test_indicador_atencao(self):
        self.atividade.progresso = 50
        self.atividade.data_previsao_termino = timezone.localdate() + timedelta(days=2)
        self.assertEqual(self.atividade.indicador, Atividade.INDICADOR_ATENCAO)

    def test_indicador_em_andamento(self):
        self.atividade.progresso = 50
        self.atividade.data_previsao_termino = timezone.localdate() + timedelta(days=10)
        self.assertEqual(self.atividade.indicador, Atividade.INDICADOR_EM_ANDAMENTO)

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
