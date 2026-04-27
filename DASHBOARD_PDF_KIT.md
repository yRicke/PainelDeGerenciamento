# Kit de Plug - Dashboard PDF

Abordagem simples com template HTML.

## Objetivo

Padronizar exportacao de dashboards para PDF usando:

1. Template HTML do dashboard (pagina visual)
2. Segunda pagina textual para auditoria (valores + filtros aplicados)
3. Renderer unico de HTML para PDF

## Arquitetura do Kit

### `app/utils/pdf_renderer.py`

- Funcao principal: `render_template_to_pdf_bytes(template_name, context, request=None)`
- Resolve navegador (Chrome/Edge) e gera PDF em modo headless
- Centraliza todo o "como gerar PDF" em um unico lugar

### `app/templates/dashboards_pdf/<area>/<modulo>.html`

- Template visual do PDF, normalmente com duas secoes e `page-break`
- Pagina 1: layout parecido com o dashboard da tela
- Pagina 2: detalhamento textual

### `app/templates/dashboards_pdf/<area>/<modulo>_texto.txt`

Opcional, mas recomendado.

- Template textual para montar auditoria de dados/filtros
- Pode ser embutido no HTML da pagina 2 via `{{ texto_relatorio }}`

## Exemplo Aplicado: Financeiro > Contas a Receber

Template PDF visual:

```text
app/templates/dashboards_pdf/financeiro/contas_a_receber.html
```

Template textual:

```text
app/templates/dashboards_pdf/financeiro/contas_a_receber_texto.txt
```

Endpoint:

```text
app/views/financeiro.py -> contas_a_receber_dashboard_pdf
```

Fluxo no endpoint:

1. Coleta filtros locais do dashboard (`periodo_inicio`, `periodo_fim`, `empresa`)
2. Coleta filtros da pagina (`filters`/`filter`) que impactam dashboards
3. Calcula contexto visual e textual
4. Renderiza `texto_relatorio` usando o template `.txt`
5. Renderiza PDF final via `render_template_to_pdf_bytes(...)`

## Como Plugar em Outro Modulo

1. Criar template HTML do PDF:

   ```text
   app/templates/dashboards_pdf/<area>/<modulo>.html
   ```

2. Opcionalmente, criar template textual:

   ```text
   app/templates/<area>/<modulo>_dashboard_pdf.txt
   ```

3. Criar endpoint de PDF na view:

   - Prepara contexto do dashboard
   - Coleta filtros relevantes (locais e de pagina)
   - Monta `texto_relatorio` se necessario
   - Chama `render_template_to_pdf_bytes(template_html, contexto_pdf)`
   - Retorna `HttpResponse(application/pdf)` com `attachment`

4. Registrar rota no `urls.py`

5. Adicionar botao/link "Baixar PDF do Dashboard" na pagina

   - No JS, atualizar querystring do link com filtros atuais

## Boas Praticas

- Evitar regra de negocio dentro do renderer.
- Regra de calculo fica na view, service ou util de negocio.
- Incluir sempre os filtros aplicados na pagina textual.
- Usar HTML/CSS focado em impressao:
  - `@page`
  - `page-break-after`
  - layout simples e previsivel para A4

## Dependencia de Ambiente

- O renderer usa navegador Chromium-based em headless (Chrome/Edge).
- Caminho pode ser configurado por variavel de ambiente:

  ```text
  DASHBOARD_PDF_BROWSER
  ```

- Sem browser disponivel, o endpoint retorna erro 500 com mensagem explicativa.

## Modo Generico

Escala rapida para outros modulos.

Para dashboards que nao exigem regra de negocio no servidor:

1. Rota generica:

   ```text
   /dashboard-pdf/<empresa_id>/<dashboard_slug>/
   app/views/dashboard_pdf.py -> dashboard_pdf_generico
   ```

2. Front compartilhado:

   ```text
   static/js/shared/dashboard-pdf-export.js
   ```

   - Captura KPIs no DOM
   - Captura graficos (svg/canvas) no `sec-dashboard`
   - Captura filtros externos e filtros da tabela
   - Envia `payload_json` por POST com CSRF

3. Config por template:

   ```html
   <div id="dashboard-pdf-config" data-endpoint="...slug..." data-title="..."></div>
   <script src="{% static 'js/shared/dashboard-pdf-export.js' %}"></script>
   ```

4. Template PDF generico:

   ```text
   app/templates/dashboards_pdf/shared/generic_dashboard.html
   app/templates/dashboards_pdf/shared/generic_dashboard_texto.txt
   ```

## Modo Dedicado por Modulo

Quando precisa ficar igual ao web.

Quando o dashboard exige layout muito proximo da tela web, use:

1. Templates dedicados no mesmo padrao de pasta:

   ```text
   app/templates/dashboards_pdf/<area>/<modulo>.html
   app/templates/dashboards_pdf/<area>/<modulo>_texto.txt
   ```

2. No mapeamento `DASHBOARD_EXPORT_CONFIG` (`app/views/dashboard_pdf.py`):

   - `template_html`
   - `template_text`

3. Opcionalmente, context builder dedicado por slug:

   - `CONTEXT_BUILDERS[slug] = funcao`
   - `payload_json` pode levar um bloco `module_payload` montado no front

4. Exemplos ja aplicados:

   - `administrativo_tofu_lista_de_atividades`
   - `comercial_controle_de_margem`
