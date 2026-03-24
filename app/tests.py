from django.test import TestCase
from django.test import override_settings
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
import json
import shutil
from uuid import uuid4
from pathlib import Path
from unittest.mock import patch
from .models import (
    Atividade,
    Cargas,
    Carteira,
    CentroResultado,
    Cidade,
    Colaborador,
    ContratoRede,
    DescricaoPerfil,
    Empresa,
    Natureza,
    Operacao,
    Orcamento,
    OrcamentoPlanejado,
    Parceiro,
    Permissao,
    ParametroMeta,
    Projeto,
    Regiao,
    Titulo,
    Usuario,
    Venda,
)
from .services import (
    atualizar_carga_por_post,
    atualizar_contrato_rede_por_post,
    criar_carga_por_post,
    criar_contrato_rede_por_post,
    preparar_diretorios_orcamento,
    preparar_diretorios_cargas,
    preparar_diretorios_vendas,
    importar_upload_orcamento,
    importar_upload_cargas,
    importar_upload_vendas,
)
from .utils.financeiro_importacao import importar_orcamento_do_diretorio, importar_orcamento_planejado_do_diretorio

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

    def test_excluir_empresa_com_parametro_meta_relacionado(self):
        descricao = DescricaoPerfil.criar_descricao_perfil(
            empresa=self.empresa,
            descricao="Perfil Teste",
        )
        parametro = ParametroMeta.criar_parametro_meta(
            empresa=self.empresa,
            descricao_perfil=descricao,
        )

        self.empresa.excluir_empresa()

        self.assertFalse(Empresa.objects.filter(id=self.empresa.id).exists())
        self.assertFalse(DescricaoPerfil.objects.filter(id=descricao.id).exists())
        self.assertFalse(ParametroMeta.objects.filter(id=parametro.id).exists())

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

    def test_criar_usuario_staff(self):
        usuario = Usuario.criar_usuario(
            username="usuario_staff",
            password="senha123",
            empresa=self.empresa,
            is_staff=True,
        )
        self.assertTrue(usuario.is_staff)

    def test_atualizar_usuario_is_staff(self):
        self.assertFalse(self.usuario.is_staff)
        self.usuario.atualizar_usuario(is_staff=True)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_staff)
        self.usuario.atualizar_usuario(is_staff=False)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_staff)

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
        self.usuario = Usuario.criar_usuario(
            username="usuario_atividade",
            password="senha123",
            empresa=self.empresa,
        )
        self.projeto = Projeto.criar_projeto(empresa=self.empresa, nome="Projeto Teste", codigo="PRJ")
        self.colaborador1 = Colaborador.criar_colaborador(empresa=self.empresa, nome="Colaborador 1")
        self.colaborador2 = Colaborador.criar_colaborador(empresa=self.empresa, nome="Colaborador 2")
        self.atividade = Atividade.criar_atividade(
            projeto=self.projeto,
            usuario=self.usuario,
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
        self.assertEqual(self.atividade.usuario, self.usuario)
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

    def test_pode_ser_editada_por_apenas_criador_ou_admin(self):
        outro_usuario = Usuario.criar_usuario(
            username="outro_usuario_atividade",
            password="senha123",
            empresa=self.empresa,
        )
        admin = Usuario.criar_usuario(
            username="admin_atividade",
            password="senha123",
            empresa=self.empresa,
        )
        admin.is_staff = True
        admin.save(update_fields=["is_staff"])

        self.assertTrue(self.atividade.pode_ser_editada_por(self.usuario))
        self.assertFalse(self.atividade.pode_ser_editada_por(outro_usuario))
        self.assertTrue(self.atividade.pode_ser_editada_por(admin))


class TofuAtividadePermissaoViewTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa TOFU")
        self.permissao_tofu = Permissao.objects.create(nome="TOFU Lista de Atividades")
        self.projeto = Projeto.criar_projeto(empresa=self.empresa, nome="Projeto TOFU", codigo="TOFU")

        self.criador = Usuario.criar_usuario(
            username="criador_tofu",
            password="senha123",
            empresa=self.empresa,
            permissoes=[self.permissao_tofu],
        )
        self.outro_usuario = Usuario.criar_usuario(
            username="outro_tofu",
            password="senha123",
            empresa=self.empresa,
            permissoes=[self.permissao_tofu],
        )
        self.admin = Usuario.criar_usuario(
            username="admin_tofu",
            password="senha123",
            empresa=self.empresa,
            permissoes=[self.permissao_tofu],
        )
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])

        self.atividade = Atividade.criar_atividade(
            projeto=self.projeto,
            usuario=self.criador,
            tarefa="Atividade do criador",
            progresso=10,
        )

        self.lista_url = reverse("tofu_lista_de_atividades", kwargs={"empresa_id": self.empresa.id})
        self.criar_url = reverse("criar_atividade_tofu", kwargs={"empresa_id": self.empresa.id})
        self.editar_url = reverse(
            "editar_atividade_tofu",
            kwargs={"empresa_id": self.empresa.id, "atividade_id": self.atividade.id},
        )
        self.excluir_url = reverse(
            "excluir_atividade_tofu",
            kwargs={"empresa_id": self.empresa.id, "atividade_id": self.atividade.id},
        )

    def test_criacao_define_usuario_logado_como_criador(self):
        self.client.login(username=self.criador.username, password="senha123")

        response = self.client.post(
            self.criar_url,
            {"projeto_id": self.projeto.id, "progresso": "0", "tarefa": "Nova atividade"},
        )

        self.assertEqual(response.status_code, 302)
        nova_atividade = Atividade.objects.exclude(id=self.atividade.id).latest("id")
        self.assertEqual(nova_atividade.usuario, self.criador)

    def test_outro_usuario_nao_pode_editar_atividade(self):
        self.client.login(username=self.outro_usuario.username, password="senha123")

        response = self.client.post(
            self.editar_url,
            {"projeto_id": self.projeto.id, "progresso": "77", "tarefa": "Tentativa indevida"},
        )

        self.assertRedirects(response, self.lista_url)
        self.atividade.refresh_from_db()
        self.assertNotEqual(self.atividade.progresso, 77)

    def test_outro_usuario_nao_pode_excluir_atividade(self):
        self.client.login(username=self.outro_usuario.username, password="senha123")

        response = self.client.post(self.excluir_url)

        self.assertRedirects(response, self.lista_url)
        self.assertTrue(Atividade.objects.filter(id=self.atividade.id).exists())

    def test_admin_pode_editar_e_excluir_atividade(self):
        self.client.login(username=self.admin.username, password="senha123")

        response_editar = self.client.post(
            self.editar_url,
            {"projeto_id": self.projeto.id, "progresso": "88", "tarefa": "Atualizado por admin"},
        )
        self.assertRedirects(response_editar, self.lista_url)

        self.atividade.refresh_from_db()
        self.assertEqual(self.atividade.progresso, 88)

        response_excluir = self.client.post(self.excluir_url)
        self.assertRedirects(response_excluir, self.lista_url)
        self.assertFalse(Atividade.objects.filter(id=self.atividade.id).exists())

    def test_lista_oculta_edicao_no_front_para_atividade_de_outro_usuario(self):
        self.client.login(username=self.outro_usuario.username, password="senha123")

        response = self.client.get(self.lista_url)

        self.assertEqual(response.status_code, 200)
        atividade_item = next(
            item for item in response.context["atividades_tabulator"] if item["id"] == self.atividade.id
        )
        self.assertNotIn("editar_url", atividade_item)


@override_settings(API_FIXED_TOKEN="token-fixo-api-teste")
class TofuAtividadeApiV1Test(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa API TOFU")
        self.permissao_tofu = Permissao.objects.create(nome="TOFU Lista de Atividades")
        self.projeto = Projeto.criar_projeto(empresa=self.empresa, nome="Projeto API", codigo="API")
        self.gestor = Colaborador.criar_colaborador(nome="Gestora API", empresa=self.empresa)
        self.responsavel = Colaborador.criar_colaborador(nome="Responsavel API", empresa=self.empresa)

        self.usuario_com_permissao = Usuario.criar_usuario(
            username="usuario_api_tofu",
            password="senha123",
            empresa=self.empresa,
            permissoes=[self.permissao_tofu],
        )
        self.usuario_sem_permissao = Usuario.criar_usuario(
            username="usuario_sem_permissao_api_tofu",
            password="senha123",
            empresa=self.empresa,
        )
        self.staff_mesma_empresa = Usuario.criar_usuario(
            username="staff_api_tofu",
            password="senha123",
            empresa=self.empresa,
            is_staff=True,
        )

        self.atividade = Atividade.criar_atividade(
            projeto=self.projeto,
            usuario=self.usuario_com_permissao,
            gestor=self.gestor,
            responsavel=self.responsavel,
            interlocutor="Interlocutor API",
            historico="Historico API",
            tarefa="Tarefa API",
            progresso=35,
        )

        self.api_url = reverse(
            "api_v1_atividades_list",
            kwargs={"empresa_id": self.empresa.id},
        )
        self.headers_token_valido = {
            "HTTP_AUTHORIZATION": f"Bearer {settings.API_FIXED_TOKEN}",
        }

    def test_api_lista_retorna_campos_fk_com_id_e_nome(self):
        self.client.login(username=self.usuario_com_permissao.username, password="senha123")

        response = self.client.get(self.api_url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("total"), 1)
        self.assertEqual(len(payload.get("data", [])), 1)

        item = payload["data"][0]
        self.assertEqual(item["id"], self.atividade.id)
        self.assertEqual(item["projeto"], {"id": self.projeto.id, "nome": self.projeto.nome})
        self.assertEqual(item["gestor"], {"id": self.gestor.id, "nome": self.gestor.nome})
        self.assertEqual(item["responsavel"], {"id": self.responsavel.id, "nome": self.responsavel.nome})
        self.assertEqual(
            item["usuario"],
            {"id": self.usuario_com_permissao.id, "nome": self.usuario_com_permissao.username},
        )

    def test_api_bloqueia_usuario_sem_permissao_tofu(self):
        self.client.login(username=self.usuario_sem_permissao.username, password="senha123")

        response = self.client.get(self.api_url)

        self.assertEqual(response.status_code, 403)

    def test_api_permite_staff_da_mesma_empresa(self):
        self.client.login(username=self.staff_mesma_empresa.username, password="senha123")

        response = self.client.get(self.api_url)

        self.assertEqual(response.status_code, 200)

    def test_api_permite_deslogado_com_token_fixo_valido(self):
        response = self.client.get(self.api_url, **self.headers_token_valido)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("total"), 1)

    def test_api_bloqueia_deslogado_sem_token(self):
        response = self.client.get(self.api_url)

        self.assertEqual(response.status_code, 403)

    def test_api_bloqueia_deslogado_com_token_invalido(self):
        response = self.client.get(
            self.api_url,
            HTTP_AUTHORIZATION="Bearer token-invalido",
        )

        self.assertEqual(response.status_code, 403)


class AdminStaffIsolamentoEmpresaTest(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.criar_empresa(nome="Empresa A")
        self.empresa_b = Empresa.criar_empresa(nome="Empresa B")
        self.permissao_a = Permissao.objects.create(nome="Permissao A")
        self.permissao_b = Permissao.objects.create(nome="Permissao B")
        self.superuser = Usuario.objects.create_superuser(
            username="super_admin",
            password="senha123",
        )

        self.staff_a = Usuario.criar_usuario(
            username="staff_empresa_a",
            password="senha123",
            empresa=self.empresa_a,
            is_staff=True,
        )
        self.usuario_b = Usuario.criar_usuario(
            username="usuario_empresa_b",
            password="senha123",
            empresa=self.empresa_b,
        )

    def test_painel_admin_lista_apenas_empresa_do_staff(self):
        self.client.login(username=self.staff_a.username, password="senha123")

        response = self.client.get(reverse("painel_admin"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Empresa A")
        self.assertNotContains(response, "Empresa B")

    def test_staff_nao_ve_checkbox_possui_sistema_no_painel_admin(self):
        self.client.login(username=self.staff_a.username, password="senha123")

        response = self.client.get(reverse("painel_admin"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="possui_sistema"')

    def test_staff_nao_altera_possui_sistema_mesmo_via_post(self):
        self.client.login(username=self.staff_a.username, password="senha123")

        response = self.client.post(
            reverse("editar_empresa", kwargs={"empresa_id": self.empresa_a.id}),
            {"nome": "Empresa A Atualizada", "possui_sistema": "on"},
        )

        self.assertRedirects(response, reverse("painel_admin"))
        self.empresa_a.refresh_from_db()
        self.assertEqual(self.empresa_a.nome, "Empresa A Atualizada")
        self.assertFalse(self.empresa_a.possui_sistema)

    def test_superuser_pode_alterar_possui_sistema(self):
        self.client.login(username=self.superuser.username, password="senha123")

        response = self.client.post(
            reverse("editar_empresa", kwargs={"empresa_id": self.empresa_a.id}),
            {"nome": self.empresa_a.nome, "possui_sistema": "on"},
        )

        self.assertRedirects(response, reverse("painel_admin"))
        self.empresa_a.refresh_from_db()
        self.assertTrue(self.empresa_a.possui_sistema)

    def test_staff_nao_acessa_usuarios_permissoes_de_outra_empresa(self):
        self.client.login(username=self.staff_a.username, password="senha123")

        response = self.client.get(
            reverse("usuarios_permissoes", kwargs={"empresa_id": self.empresa_b.id})
        )

        self.assertRedirects(response, reverse("painel_admin"))

    def test_staff_nao_edita_usuario_de_outra_empresa(self):
        self.client.login(username=self.staff_a.username, password="senha123")

        response = self.client.post(
            reverse("editar_usuario", kwargs={"usuario_id": self.usuario_b.id}),
            {"nome": "novo_nome_invalido", "senha": "", "is_staff": "on"},
        )

        self.assertRedirects(response, reverse("painel_admin"))
        self.usuario_b.refresh_from_db()
        self.assertEqual(self.usuario_b.username, "usuario_empresa_b")
        self.assertFalse(self.usuario_b.is_staff)

    def test_staff_nao_exclui_usuario_de_outra_empresa(self):
        self.client.login(username=self.staff_a.username, password="senha123")

        response = self.client.get(
            reverse("excluir_usuario", kwargs={"usuario_id": self.usuario_b.id})
        )

        self.assertRedirects(response, reverse("painel_admin"))
        self.assertTrue(Usuario.objects.filter(id=self.usuario_b.id).exists())

    def test_staff_nao_acessa_modulo_de_outra_empresa(self):
        self.client.login(username=self.staff_a.username, password="senha123")

        response = self.client.get(reverse("dre", kwargs={"empresa_id": self.empresa_b.id}))

        self.assertRedirects(response, reverse("index"))

    def test_staff_nao_remove_proprio_staff(self):
        self.client.login(username=self.staff_a.username, password="senha123")

        response = self.client.post(
            reverse("editar_usuario", kwargs={"usuario_id": self.staff_a.id}),
            {"nome": self.staff_a.username, "senha": ""},
        )

        self.assertRedirects(
            response,
            reverse("usuarios_permissoes", kwargs={"empresa_id": self.empresa_a.id}),
        )
        self.staff_a.refresh_from_db()
        self.assertTrue(self.staff_a.is_staff)

    def test_cadastro_staff_define_todas_permissoes(self):
        self.client.login(username=self.staff_a.username, password="senha123")
        permissoes_ids_existentes = set(Permissao.objects.values_list("id", flat=True))

        response = self.client.post(
            reverse("cadastrar_usuario", kwargs={"empresa_id": self.empresa_a.id}),
            {
                "nome": "novo_staff_empresa_a",
                "senha": "senha123",
                "is_staff": "on",
                "permissoes": [str(self.permissao_a.id)],
            },
        )

        self.assertRedirects(
            response,
            reverse("usuarios_permissoes", kwargs={"empresa_id": self.empresa_a.id}),
        )
        novo_staff = Usuario.objects.get(username="novo_staff_empresa_a")
        self.assertTrue(novo_staff.is_staff)
        self.assertSetEqual(
            set(novo_staff.permissoes.values_list("id", flat=True)),
            permissoes_ids_existentes,
        )

    def test_cadastro_usuario_com_username_existente_exibe_erro(self):
        self.client.login(username=self.staff_a.username, password="senha123")
        total_usuarios_antes = Usuario.objects.count()

        response = self.client.post(
            reverse("cadastrar_usuario", kwargs={"empresa_id": self.empresa_a.id}),
            {
                "nome": self.usuario_b.username,
                "senha": "senha123",
                "permissoes": [str(self.permissao_a.id)],
            },
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("usuarios_permissoes", kwargs={"empresa_id": self.empresa_a.id}),
        )
        self.assertEqual(Usuario.objects.count(), total_usuarios_antes)
        mensagens = [str(mensagem) for mensagem in get_messages(response.wsgi_request)]
        self.assertIn(
            "Ja existe um username igual ao cadastrado para outro usuario.",
            mensagens,
        )

    def test_edicao_para_staff_define_todas_permissoes(self):
        usuario_alvo = Usuario.criar_usuario(
            username="alvo_empresa_a",
            password="senha123",
            empresa=self.empresa_a,
            permissoes=[self.permissao_a],
        )
        self.client.login(username=self.staff_a.username, password="senha123")
        permissoes_ids_existentes = set(Permissao.objects.values_list("id", flat=True))

        response = self.client.post(
            reverse("editar_usuario", kwargs={"usuario_id": usuario_alvo.id}),
            {
                "nome": usuario_alvo.username,
                "senha": "",
                "is_staff": "on",
                "permissoes": [str(self.permissao_a.id)],
            },
        )

        self.assertRedirects(
            response,
            reverse("usuarios_permissoes", kwargs={"empresa_id": self.empresa_a.id}),
        )
        usuario_alvo.refresh_from_db()
        self.assertTrue(usuario_alvo.is_staff)
        self.assertSetEqual(
            set(usuario_alvo.permissoes.values_list("id", flat=True)),
            permissoes_ids_existentes,
        )


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


class ContratoRedeModelServiceTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Contratos Redes")
        self.parceiro = Parceiro.criar_parceiro(nome="Parceiro Rede", codigo="PR001", empresa=self.empresa)

    def test_criar_contrato_rede_por_post_com_sucesso(self):
        erro = criar_contrato_rede_por_post(
            self.empresa,
            {
                "codigo_registro": "REG-100",
                "numero_contrato": "CTR-900",
                "data_inicio": "2026-03-10",
                "data_encerramento": "2026-12-31",
                "parceiro_id": str(self.parceiro.id),
                "descricao_acordos": "Contrato de percentual de rede",
                "valor_acordo": "1,25%",
                "status_contrato": "Ativo",
            },
        )

        self.assertEqual(erro, "")
        contrato = ContratoRede.objects.get(empresa=self.empresa, codigo_registro="REG-100")
        self.assertEqual(contrato.numero_contrato, "CTR-900")
        self.assertEqual(str(contrato.data_inicio), "2026-03-10")
        self.assertEqual(str(contrato.data_encerramento), "2026-12-31")
        self.assertEqual(contrato.parceiro_id, self.parceiro.id)
        self.assertEqual(float(contrato.valor_acordo), 0.0125)
        self.assertEqual(contrato.status_contrato, "Ativo")

    def test_criar_contrato_rede_rejeita_campos_obrigatorios(self):
        erro = criar_contrato_rede_por_post(
            self.empresa,
            {
                "codigo_registro": "",
                "numero_contrato": "",
                "data_inicio": "",
                "descricao_acordos": "",
                "valor_acordo": "",
                "status_contrato": "",
            },
        )

        self.assertIn("Codigo de registro", erro)
        self.assertEqual(ContratoRede.objects.filter(empresa=self.empresa).count(), 0)

    def test_criar_contrato_rede_rejeita_data_encerramento_menor_que_inicio(self):
        erro = criar_contrato_rede_por_post(
            self.empresa,
            {
                "codigo_registro": "REG-200",
                "numero_contrato": "CTR-200",
                "data_inicio": "2026-04-10",
                "data_encerramento": "2026-04-01",
                "descricao_acordos": "Acordo invalido de datas",
                "valor_acordo": "0,75%",
                "status_contrato": "Ativo",
            },
        )

        self.assertIn("encerramento", erro)
        self.assertFalse(ContratoRede.objects.filter(empresa=self.empresa, codigo_registro="REG-200").exists())

    def test_atualizar_contrato_rede_por_post(self):
        contrato = ContratoRede.criar_contrato_rede(
            empresa=self.empresa,
            codigo_registro="REG-300",
            numero_contrato="CTR-300",
            data_inicio=timezone.localdate(),
            descricao_acordos="Descricao inicial",
            valor_acordo=0,
            status_contrato=ContratoRede.STATUS_ATIVO,
        )

        erro = atualizar_contrato_rede_por_post(
            contrato,
            self.empresa,
            {
                "codigo_registro": "REG-300A",
                "numero_contrato": "CTR-300A",
                "data_inicio": "2026-05-01",
                "data_encerramento": "",
                "parceiro_id": str(self.parceiro.id),
                "descricao_acordos": "Descricao atualizada",
                "valor_acordo": "2,50%",
                "status_contrato": "Inativo",
            },
        )

        self.assertEqual(erro, "")
        contrato.refresh_from_db()
        self.assertEqual(contrato.codigo_registro, "REG-300A")
        self.assertEqual(contrato.numero_contrato, "CTR-300A")
        self.assertEqual(str(contrato.data_inicio), "2026-05-01")
        self.assertIsNone(contrato.data_encerramento)
        self.assertEqual(contrato.parceiro_id, self.parceiro.id)
        self.assertEqual(float(contrato.valor_acordo), 0.025)
        self.assertEqual(contrato.status_contrato, "Inativo")

    def test_excluir_contrato_rede(self):
        contrato = ContratoRede.criar_contrato_rede(
            empresa=self.empresa,
            codigo_registro="REG-400",
            numero_contrato="CTR-400",
            data_inicio=timezone.localdate(),
            descricao_acordos="Contrato para excluir",
            valor_acordo=0,
            status_contrato=ContratoRede.STATUS_ATIVO,
        )
        contrato_id = contrato.id

        contrato.excluir_contrato_rede()
        self.assertFalse(ContratoRede.objects.filter(id=contrato_id).exists())


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

    def test_dias_sem_venda_sem_ultima_venda(self):
        self.carteira.ultima_venda = None
        self.carteira.save()
        self.assertEqual(self.carteira.dias_sem_venda, "Sem venda")
        self.assertEqual(self.carteira.Intervalo, "Sem venda")
        self.assertEqual(self.carteira.qtd_dias_sem_venda, 0)
        self.assertEqual(self.carteira.intervalo, "Sem venda")

    def test_intervalo_calculado_por_ultima_venda(self):
        self.carteira.ultima_venda = timezone.localdate() - timedelta(days=45)
        self.carteira.save()
        self.assertEqual(self.carteira.dias_sem_venda, 45)
        self.assertEqual(self.carteira.Intervalo, "31 a 60")
        self.assertEqual(self.carteira.qtd_dias_sem_venda, 45)
        self.assertEqual(self.carteira.intervalo, "31 a 60")


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
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_vendas(self.empresa)
            self.assertTrue(diretorio_importacao.exists())
            self.assertTrue(diretorio_subscritos.exists())
            self.assertEqual(diretorio_subscritos.parent, diretorio_importacao)
            self.assertEqual(diretorio_importacao.name, str(self.empresa.id))

    def test_preparar_diretorios_vendas_isola_por_empresa(self):
        empresa_b = Empresa.criar_empresa(nome="Empresa Teste Importacao B")
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao_a, _ = preparar_diretorios_vendas(self.empresa)
            diretorio_importacao_b, _ = preparar_diretorios_vendas(empresa_b)
            self.assertNotEqual(diretorio_importacao_a, diretorio_importacao_b)
            self.assertEqual(diretorio_importacao_a.name, str(self.empresa.id))
            self.assertEqual(diretorio_importacao_b.name, str(empresa_b.id))

    def test_importar_upload_vendas_mantem_apenas_novos_e_move_antigos(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_vendas(self.empresa)
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
            caminho_metadados = diretorio_subscritos / f"_ultimo_import_empresa_{self.empresa.id}.json"
            self.assertTrue(caminho_metadados.exists())
            payload = json.loads(caminho_metadados.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("empresa_id"), self.empresa.id)
            self.assertEqual(payload.get("modulo"), "vendas_por_categoria")

    def test_importar_upload_vendas_sem_xls_retorna_erro(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_vendas(self.empresa)
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
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_cargas(self.empresa)
            self.assertTrue(diretorio_importacao.exists())
            self.assertTrue(diretorio_subscritos.exists())
            self.assertEqual(diretorio_subscritos.parent, diretorio_importacao)

    def test_importar_upload_cargas_mantem_apenas_novo_e_move_antigo(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_cargas(self.empresa)
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
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_cargas(self.empresa)
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


class OrcamentoImportacaoServiceTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Teste Importacao Orcamento")
        self.base_dir = str((Path(settings.BASE_DIR) / f".tmp_test_orcamento_{uuid4().hex}"))
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(self.base_dir, ignore_errors=True))

    def test_preparar_diretorios_orcamento_cria_estrutura(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_orcamento(self.empresa)
            self.assertTrue(diretorio_importacao.exists())
            self.assertTrue(diretorio_subscritos.exists())
            self.assertEqual(diretorio_subscritos.parent, diretorio_importacao)

    def test_importar_upload_orcamento_mantem_apenas_novos_e_move_antigos(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_orcamento(self.empresa)
            antigo = diretorio_importacao / "orcamento_antigo.xls"
            antigo.write_bytes(b"arquivo-antigo")

            arquivo_a = SimpleUploadedFile("orcamento_1.xls", b"novo-a", content_type="application/vnd.ms-excel")
            arquivo_b = SimpleUploadedFile("orcamento_2.xls", b"novo-b", content_type="application/vnd.ms-excel")
            arquivo_invalido = SimpleUploadedFile("nao_importar.txt", b"xx", content_type="text/plain")

            with patch("app.services.importar_orcamento_do_diretorio") as importar_real_mock:
                importar_real_mock.return_value = {"arquivos": 2, "linhas": 2, "orcamentos": 2}
                ok, mensagem = importar_upload_orcamento(
                    empresa=self.empresa,
                    arquivos=[arquivo_a, arquivo_b, arquivo_invalido],
                    diretorio_importacao=diretorio_importacao,
                    diretorio_subscritos=diretorio_subscritos,
                )

            self.assertTrue(ok)
            self.assertIn("Importacao concluida", mensagem)
            self.assertTrue((diretorio_importacao / "orcamento_1.xls").exists())
            self.assertTrue((diretorio_importacao / "orcamento_2.xls").exists())
            self.assertFalse((diretorio_importacao / "nao_importar.txt").exists())
            self.assertTrue((diretorio_subscritos / "orcamento_antigo.xls").exists())
            importar_real_mock.assert_called_once()

    def test_importar_upload_orcamento_sem_xls_retorna_erro(self):
        with override_settings(BASE_DIR=self.base_dir):
            diretorio_importacao, diretorio_subscritos = preparar_diretorios_orcamento(self.empresa)
            arquivo_invalido = SimpleUploadedFile("arquivo.csv", b"1,2,3", content_type="text/csv")

            ok, mensagem = importar_upload_orcamento(
                empresa=self.empresa,
                arquivos=[arquivo_invalido],
                diretorio_importacao=diretorio_importacao,
                diretorio_subscritos=diretorio_subscritos,
            )

            self.assertFalse(ok)
            self.assertIn("arquivo .xls", mensagem)


class OrcamentoImportadorFkTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.criar_empresa(nome="Empresa Orcamento FK")
        self.base_dir = Path(settings.BASE_DIR) / f".tmp_importador_orcamento_{uuid4().hex}"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(self.base_dir, ignore_errors=True))

    def test_importacao_cria_fks_quando_nao_existem(self):
        caminho_arquivo = self.base_dir / "ORCAMENTO 03-02-2026.xls"
        caminho_arquivo.write_bytes(b"placeholder")

        linhas = [
            [
                "Dt. Vencimento",
                "Data Baixa",
                "Vlr Baixa",
                "Valor Liquido",
                "Vlr do Desdobramento",
                "Descricao (Tipo de Titulo)",
                "Natureza",
                "Descricao (Natureza)",
                "Descricao (Centro de Resultado)",
                "Parceiro",
                "Nome Parceiro (Parceiro)",
                "Tipo Operacao",
                "Receita/Despesa",
            ],
            [46055, 46055, 100.50, -100.50, 100.50, "DEBITO AUTOMATICO", "5010202", "Tarifas", "FINANCEIRO", "2414", "BANCO BRADESCO S.A.", "4100", "Despesa"],
        ]

        with patch("app.utils.financeiro_importacao._iterar_linhas_xls", return_value=linhas):
            resultado = importar_orcamento_do_diretorio(
                empresa=self.empresa,
                diretorio=str(self.base_dir),
                limpar_antes=True,
            )

        self.assertEqual(resultado["orcamentos"], 1)
        self.assertEqual(Titulo.objects.filter(empresa=self.empresa).count(), 1)
        self.assertEqual(Natureza.objects.filter(empresa=self.empresa).count(), 1)
        self.assertEqual(Operacao.objects.filter(empresa=self.empresa).count(), 1)
        self.assertEqual(Parceiro.objects.filter(empresa=self.empresa).count(), 1)
        self.assertEqual(CentroResultado.objects.filter(empresa=self.empresa).count(), 1)

        orcamento = Orcamento.objects.get(empresa=self.empresa)
        self.assertIsNotNone(orcamento.titulo)
        self.assertIsNotNone(orcamento.natureza)
        self.assertIsNotNone(orcamento.operacao)
        self.assertIsNotNone(orcamento.parceiro)
        self.assertIsNotNone(orcamento.centro_resultado)

    def test_importacao_garante_centro_resultado_quando_coluna_vem_vazia(self):
        caminho_arquivo = self.base_dir / "ORCAMENTO 03-02-2026.xls"
        caminho_arquivo.write_bytes(b"placeholder")

        linhas = [
            [
                "Dt. Vencimento",
                "Data Baixa",
                "Vlr Baixa",
                "Valor Liquido",
                "Vlr do Desdobramento",
                "Descricao (Tipo de Titulo)",
                "Natureza",
                "Descricao (Natureza)",
                "Descricao (Centro de Resultado)",
                "Parceiro",
                "Nome Parceiro (Parceiro)",
                "Tipo Operacao",
                "Receita/Despesa",
            ],
            [46055, 46055, 200, -200, 200, "DEBITO", "5010202", "Tarifas", "", "2414", "BANCO BRADESCO S.A.", "4100", "Despesa"],
        ]

        with patch("app.utils.financeiro_importacao._iterar_linhas_xls", return_value=linhas):
            resultado = importar_orcamento_do_diretorio(
                empresa=self.empresa,
                diretorio=str(self.base_dir),
                limpar_antes=True,
            )

        self.assertEqual(resultado["orcamentos"], 1)
        orcamento = Orcamento.objects.get(empresa=self.empresa)
        self.assertIsNotNone(orcamento.centro_resultado)
        self.assertEqual(orcamento.centro_resultado.descricao, "<SEM CENTRO DE RESULTADO>")

    def test_importacao_orcamento_planejado_sem_layout_mensal_gera_fallback(self):
        caminho_arquivo = self.base_dir / "ORCAMENTO 31.01.2026.xls"
        caminho_arquivo.write_bytes(b"placeholder")

        centro = CentroResultado.obter_ou_criar_por_descricao(self.empresa, "ADMINISTRAÇÃO")
        natureza = Natureza.obter_ou_criar_por_codigo_descricao(self.empresa, "DESC_FISCAL", "Fiscal")
        Orcamento.criar_orcamento(
            empresa=self.empresa,
            nome_empresa="1 - SAFIA DISTRIBUIDORA",
            data_vencimento=timezone.localdate(),
            data_baixa=timezone.datetime(2026, 1, 31).date(),
            valor_baixa=1000,
            valor_liquido=1000,
            valor_desdobramento=600,
            natureza=natureza,
            centro_resultado=centro,
        )
        Orcamento.criar_orcamento(
            empresa=self.empresa,
            nome_empresa="1 - SAFIA DISTRIBUIDORA",
            data_vencimento=timezone.localdate(),
            data_baixa=timezone.datetime(2026, 1, 15).date(),
            valor_baixa=500,
            valor_liquido=500,
            valor_desdobramento=400,
            natureza=natureza,
            centro_resultado=centro,
        )

        linhas = [
            [
                "Descrição (Tipo de Título)",
                "Dt. Vencimento",
                "Empresa",
                "Nome Fantasia (Empresa)",
                "Descrição (Natureza)",
                "Descrição (Centro de Resultado)",
                "Receita/Despesa",
                "Data Baixa",
                "Vlr Baixa",
            ],
            ["BOLETO", 46055, 1, "SAFIA DISTRIBUIDORA", "Fiscal", "ADMINISTRAÇÃO", "Despesa", 46051, 1518],
            ["BOLETO", 46055, 1, "SAFIA DISTRIBUIDORA", "Fiscal", "ADMINISTRAÇÃO", "Despesa", "15/02/2026", 2000],
        ]

        with patch("app.utils.financeiro_importacao._iterar_linhas_xls", return_value=linhas):
            resultado = importar_orcamento_planejado_do_diretorio(
                empresa=self.empresa,
                diretorio=str(self.base_dir),
                limpar_antes=True,
            )

        self.assertEqual(resultado["orcamentos_planejados"], 1)
        self.assertFalse(resultado["layout_mensal_detectado"])
        self.assertTrue(resultado["fallback_gerado"])
        item = OrcamentoPlanejado.objects.get(empresa=self.empresa)
        self.assertEqual(float(item.janeiro), 600.0)


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
