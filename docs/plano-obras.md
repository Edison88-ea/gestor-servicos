# Plano — Módulo de Obras / Mudanças de Layout no gestor-servicos

Traz o **gestor_obras** (hoje em `edison87.pythonanywhere.com`, repo
`github.com/Edison88-ea/gestor-obras`) para dentro do gestor-servicos como um
app novo. Não se aproveita o código de tela do legado (Django templates +
WeasyPrint) — só o **modelo de dados**, evoluído. Fonte de dados: o documento
**"Termo de Mudança de Layout"** (escopo de pontos a instalar por setor/linha).

---

## 1. Mapeamento do documento

| No "Termo de Mudança de Layout" | No sistema |
|---|---|
| O Termo (Volkswagen / Patagonia-Alternador / M-HEV Cabo de Bateria…) | `Projeto` |
| Escopo (texto) | `Projeto.descricao` |
| Responsável (Cristiano Almeida) | `Projeto.responsavel` (texto livre, não é usuário) |
| Tipo de mudança ("instalação de projeto") | `Projeto.tipo` |
| Data da mudança (04/08/26) / Término (30/09/26) | `Projeto.data_mudanca` / `data_termino_previsto` |
| Área afetada (checkboxes: VOLKS, ADM, Manutenção, Logística…) | `Projeto.areas_afetadas` (JSON) |
| Cada tipo de ponto do escopo (Rede, Ar, Energia, Telefone, LPRS, Rede Estabilizada, Elétrica 220V) | `Etapa` (uma por tipo/trecho) |
| Quantidade prevista ("PONTO DE REDE (2x)") | `Etapa.meta` |
| Quantidade instalada | `Etapa.realizado` → `Projeto.progresso` |
| Setor/linha na planta ("Patagonia - Alternador") | `Etapa.localizacao` |
| Foto do ponto instalado | `FotoEtapa` |
| Folhas da planta (nº 2, 3, 4…) | `PlantaProjeto` (PDF ou imagem) |
| Quem alterou a quantidade e quando | `HistoricoEtapa` |
| Assinaturas ("ciente da alteração", "supervisor de processos") | `AssinaturaProjeto` (fase 4, opcional) |

---

## 2. Backend — `apps/projects/`

App novo seguindo o padrão de `apps/service_orders/` (DRF ViewSets, sem template).

### 2.1 Models (`apps/projects/models.py`)

```python
class Projeto(models.Model):
    class Status(models.TextChoices):
        PLANEJADO = "PLANEJADO", "Planejado"
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        CONCLUIDO = "CONCLUIDO", "Concluído"
        CANCELADO = "CANCELADO", "Cancelado"

    class Tipo(models.TextChoices):
        INSTALACAO_PROJETO = "INSTALACAO_PROJETO", "Instalação de projeto"
        MUDANCA_LAYOUT = "MUDANCA_LAYOUT", "Mudança de layout"
        MANUTENCAO = "MANUTENCAO", "Manutenção"
        OUTRO = "OUTRO", "Outro"

    numero = models.CharField(max_length=20, unique=True, editable=False)   # PRJ000001
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)                # "Escopo" do Termo
    responsavel = models.CharField(max_length=150, blank=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.INSTALACAO_PROJETO)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PLANEJADO)
    areas_afetadas = models.JSONField(default=list, blank=True)   # ["VOLKS", "ADM", ...]

    data_mudanca = models.DateField(null=True, blank=True)
    data_termino_previsto = models.DateField(null=True, blank=True)
    data_conclusao = models.DateField(null=True, blank=True)

    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, related_name="projetos_criados")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def save(self, *a, **kw):        # gera numero PRJ%06d (igual OrdemServico)
        ...

    @property
    def progresso(self):             # soma(realizado) / soma(meta) * 100, teto 100
        ...                          # (porta do progresso_atual do legado)

    @property
    def total_meta / total_realizado: ...


class Etapa(models.Model):
    class TipoPonto(models.TextChoices):
        REDE = "REDE", "Ponto de rede"
        AR = "AR", "Ponto de ar"
        ENERGIA = "ENERGIA", "Ponto de energia"
        TELEFONE = "TELEFONE", "Ponto de telefone"
        LPRS = "LPRS", "Ponto de LPRS"
        REDE_ESTABILIZADA = "REDE_ESTABILIZADA", "Rede estabilizada elétrica"
        ELETRICA_220 = "ELETRICA_220", "Elétrica 220V"
        OUTRO = "OUTRO", "Outro"

    projeto = models.ForeignKey(Projeto, related_name="etapas", on_delete=models.CASCADE)
    nome = models.CharField(max_length=200)
    tipo_ponto = models.CharField(max_length=20, choices=TipoPonto.choices, blank=True)
    localizacao = models.CharField(max_length=200, blank=True)   # "Patagonia - Alternador"
    meta = models.PositiveIntegerField(default=1)
    realizado = models.PositiveIntegerField(default=0)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "id"]

    @property
    def concluida(self):   return bool(self.meta) and self.realizado >= self.meta
    @property
    def porcentagem(self): ...
    # NOTA: no legado 'concluida' era campo E property ao mesmo tempo (bug).
    # Aqui fica só property.


class FotoEtapa(models.Model):     # espelha FotoOrdemServico
    etapa = models.ForeignKey(Etapa, related_name="fotos", on_delete=models.CASCADE)
    imagem = models.ImageField(upload_to="obras/etapas/%Y/%m/")
    legenda = models.CharField(max_length=200, blank=True)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    enviado_em = models.DateTimeField(auto_now_add=True)


class PlantaProjeto(models.Model):
    projeto = models.ForeignKey(Projeto, related_name="plantas", on_delete=models.CASCADE)
    arquivo = models.FileField(upload_to="obras/plantas/%Y/%m/")   # PDF ou imagem
    pagina = models.PositiveIntegerField(null=True, blank=True)
    descricao = models.CharField(max_length=200, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)


class HistoricoEtapa(models.Model):    # porta do legado
    etapa = models.ForeignKey(Etapa, related_name="historico", on_delete=models.CASCADE)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    data = models.DateTimeField(auto_now_add=True)
    quantidade_anterior = models.PositiveIntegerField()
    quantidade_nova = models.PositiveIntegerField()
    observacao = models.CharField(max_length=300, blank=True)


class AssinaturaProjeto(models.Model):    # FASE 4 — opcional
    class Papel(models.TextChoices):
        CIENTE = "CIENTE", "Ciente da alteração"
        SUPERVISOR = "SUPERVISOR", "Supervisor de processos"
    projeto = models.ForeignKey(Projeto, related_name="assinaturas", on_delete=models.CASCADE)
    papel = models.CharField(max_length=15, choices=Papel.choices)
    nome = models.CharField(max_length=150)
    assinatura = models.ImageField(upload_to="obras/assinaturas/%Y/%m/")
    assinado_em = models.DateTimeField(auto_now_add=True)
```

### 2.2 Catálogo de áreas (código, não banco)

`apps/projects/catalogos.py` — lista fixa de áreas afetadas, exposta via endpoint
para o formulário:

```python
AREAS_AFETADAS = [
    ("DM", "DM"), ("CMI", "CMI"), ("VOLKS", "Volks"), ("ADM", "ADM"),
    ("MANUTENCAO", "Manutenção"), ("ONIX", "Onix"), ("VS30", "VS30"),
    ("PATIO", "Pátio"), ("LEAD_PREP", "Lead Prep"), ("FIAT", "Fiat"),
    ("GLM", "GLM"), ("BU", "BU"), ("LOGISTICA", "Logística"),
]
```

### 2.3 Serializers / Views / URLs

- `serializers.py`: `ProjetoSerializer` (etapas + plantas aninhados read-only,
  `progresso`, `total_meta`/`total_realizado`, `criado_por_nome`),
  `EtapaSerializer` (`fotos` + `historico` aninhados, `porcentagem`, `concluida`),
  `FotoEtapaSerializer`, `PlantaProjetoSerializer`, `HistoricoEtapaSerializer`.
- Campos de arquivo: usar `RelativeImageField` (fotos/assinaturas) e um
  **`RelativeFileField` novo** em `config/drf_fields.py` (mesma lógica, para o
  PDF da planta).
- `views.py`:
  - `ProjetoViewSet(ModelViewSet)` — leitura para todos autenticados; criar /
    editar / apagar só `GESTOR` e `ADMIN`. `perform_create` grava `criado_por`.
    Actions:
    - `POST projetos/{id}/plantas` — upload de planta
    - `GET  projetos/opcoes` — devolve `AREAS_AFETADAS`, `Tipo`, `Status`,
      `TipoPonto` para os selects do front
  - `EtapaViewSet(ModelViewSet)` — filtra por `?projeto=`. Actions:
    - `POST etapas/{id}/progresso` — body `{realizado, observacao}`; cria
      `HistoricoEtapa`, faz clamp 0..meta, atualiza (porta de `atualizar_progresso`)
    - `POST etapas/{id}/fotos` — upload de foto
- `urls.py`: `DefaultRouter` → `projetos`, `etapas`.
- Fiação: `config/settings.py` INSTALLED_APPS += `"apps.projects"`;
  `config/urls.py` += `path("api/", include("apps.projects.urls"))`.
- `admin.py`: `Projeto` com inlines de `Etapa` e `PlantaProjeto`.
- **Sem WeasyPrint** — o PDF é client-side (`window.print`), igual ao
  Comprovante de OS.
- Compressão de imagem no upload (o legado fazia com Pillow no `Etapa.save`):
  criar util compartilhada e aplicar em `FotoEtapa` (ver decisão #4).
- `tests.py`: cobrir geração de `numero`, `progresso`, action `progresso`
  criando histórico e fazendo clamp, permissão de técnico.

---

## 3. Frontend — Vue 3 / Pinia

Espelha `ordensServico`. Views estáticas no `router` (o projeto não usa
code-splitting por rota — ver comentário em `router/index.js`).

| Arquivo | Papel | Porta de |
|---|---|---|
| `stores/obras.js` | CRUD + actions (progresso, fotos, plantas) | `stores/ordensServico.js` |
| `views/ObrasView.vue` | Lista de projetos: barra de progresso, contadores (total / em andamento / concluídos), gráfico | `lista_projetos` + `GraficoBarras.vue` |
| `views/NovaObraView.vue` | Form: nome, escopo, responsável, tipo, áreas afetadas (checkboxes), datas | `novo_projeto` |
| `views/ObraDetalheView.vue` | Cabeçalho + etapas com controle +/- de progresso, histórico, fotos, plantas | `detalhe_projeto` + `upload_foto` + `atualizar_progresso` |
| `views/EtapasObraView.vue` | Definir metas: adicionar / editar / remover etapas (tipo de ponto, localização, meta). Só GESTOR | `definir_metas` (formset) |
| `views/RelatorioObraView.vue` | Versão imprimível → "Imprimir / PDF" | `gerar_relatorio_pdf` + `ComprovanteOsView.vue` |

- Rotas em `router/index.js`: `/obras`, `/obras/nova`, `/obras/:id`,
  `/obras/:id/etapas`, `/obras/:id/relatorio`. `meta:{auth:true}`;
  `/nova` e `/etapas` com `meta:{gestor:true}`.
- `components/MenuLateral.vue`: novo botão **"Obras"** (ou "Mudanças de Layout").
- Reaproveita `AssinaturaCanvas.vue` (fase 4) e `GraficoBarras.vue`.
- Visualização de planta: PDF em `<iframe>`/link, imagem inline.

---

## 4. Migração de dados do PythonAnywhere

Volume real: **5 projetos, 51 etapas, 35 históricos, 14 fotos**. Comando dedicado
`apps/projects/management/commands/importar_obras_legado.py` (feito e testado com
o dump real):

- `Projeto`: `nome`, `descricao` iguais; `data_inicio` → `data_mudanca`;
  `tipo = MUDANCA_LAYOUT`; `status` calculado do progresso (0 → planejado,
  100 → concluído, resto → em andamento).
- `Etapa`: `nome`, `meta`, `realizado` iguais; `ordem` pela ordem do dump.
  `tipo_ponto` e `localizacao` ficam em branco (o legado não tinha) — ajustar
  depois pela tela de etapas.
- `foto` → cria `FotoEtapa` **se** `--media` apontar para a pasta com o arquivo;
  senão o comando lista as puladas.
- `HistoricoEtapa`: `data` original preservada (via `.update()`, driblando o
  `auto_now_add`); `usuario` = `--usuario <username>` ou nulo (o dump não traz
  os usuários do sistema antigo).

### Passo a passo (rodar contra o Neon de produção)

1. No PythonAnywhere: `cd ~/gestor_obras && python manage.py dumpdata core --indent 2 -o ~/obras_legado.json`
2. Baixar `~/obras_legado.json` e a pasta `~/gestor_obras/media/` (aba *Files*).
3. Subir os dois para a máquina que roda o deploy (ou rodar via shell do Render).
4. Com `DATABASE_URL` apontando para o Neon:
   `python manage.py importar_obras_legado obras_legado.json --media ./media`
   (o comando comprime as fotos e as grava no R2 pelo storage padrão).
5. Conferir no app (`/obras`), congelar o PythonAnywhere, desligar.

> `--limpar` apaga os `Projeto` existentes antes — usar só se precisar repetir a
> importação do zero.

---

## 5. Fases

| Fase | Entrega |
|---|---|
| **1 — Backend base** ✔ | app `apps.projects`, models, migração, admin, serializers, viewsets, urls, `RelativeFileField`, util de compressão, 8 tests |
| **2 — Frontend base** ✔ | `stores/obras.js`, `ObrasView` (lista + contadores + progresso), `NovaObraView`, `ObraDetalheView` (controle +/- de progresso + histórico), rotas, item "Obras" no menu |
| **3 — Etapas, plantas e fotos** ✔ | `ObraEtapasView` (CRUD etapas, GESTOR), anexo/visualização de plantas PDF, envio de fotos por etapa — entregue junto da Fase 2 |
| **4 — Relatório e assinaturas** ✔ | `RelatorioObraView` (print/PDF via `window.print`), action `projetos/{id}/assinaturas` + coleta com `AssinaturaCanvas` no detalhe |
| **5 — Migração** ✔ | comando `importar_obras_legado` (feito e testado com o dump real: 5 projetos / 51 etapas / 35 históricos). Falta só executar contra o Neon com a pasta `media/` e desligar o PythonAnywhere |

---

## 6. Decisões

**Confirmadas:**

1. **PDF**: client-side (`window.print`, igual ao Comprovante de OS). **Sem WeasyPrint.** ✔
2. **Compressão de imagem**: no servidor — util compartilhada com Pillow aplicada no upload de `FotoEtapa` (e reaproveitável para `FotoOrdemServico`). ✔
3. **Áreas afetadas**: catálogo fixo em código (`apps/projects/catalogos.py`), exposto via `GET projetos/opcoes`. ✔
4. **Nome**: app `apps.projects`, models `Projeto` / `Etapa`. ✔ (padrão, continuidade com o legado)
5. **Status do projeto**: manual, com sugestão automática pelo progresso. ✔
6. **`responsavel`**: texto livre (engenheiro externo, não usuário do sistema). ✔

7. **Permissões**: criar/editar obra e definir metas = `GESTOR` + `ADMIN`; técnico só atualiza progresso e sobe foto. ✔
8. **Menu**: rótulo **"Obras"** (curto, cabe no menu; é só uma string, fácil de trocar depois). ✔

Todas as decisões fechadas.
