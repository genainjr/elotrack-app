# ODS - View Standard

## Objetivo

Definir o padrao unico para paginas de visualizacao, consulta e detalhes read-only no OneElo, usando os padroes encontrados em `membros/visualizacao`, `escalas/visualizacao`, `minhas-escalas`, `meu-perfil`, `dashboard` e `ComingSoon`.

## Estrutura padrao

1. `PageHeader` com titulo e descricao.
2. Resumo com metricas usando `StatCard` quando a visualizacao consultar uma colecao ou tiver dados agregaveis.
3. Filtros opcionais quando a visualizacao consultar colecoes.
4. Conteudo read-only:
   - tabela/lista para entidades simples;
   - grade para escalas;
   - cards para participacoes ou eventos;
   - drawer para detalhes laterais.
5. `EmptyState` para ausencia de dados.
6. Erro inline com retry.

## Componentes obrigatorios

- `PageHeader`
- `EmptyState`
- Estado de `loading`
- Estado de `error`
- Visualizacao sem controles de edicao quando a rota for read-only

Para detalhe lateral:

- `MemberProfileDrawer` como referencia de padrao de drawer.

Para grade read-only de escala:

- `EscalaReadonlyGrid`

## Componentes opcionais

- `StatCard` para metricas apenas quando a visualizacao nao tiver dados agregaveis ou for uma tela de detalhe individual.
- Filtros com aplicar, limpar e recarregar.
- Botao de imprimir em visualizacoes printaveis.
- Drawer de detalhes.
- Cards read-only quando a informacao for mais natural como participacao ou evento.
- `ComingSoon` para modulos futuros.

## Regras de UX

- Nao mostrar botoes de edicao em rotas de visualizacao.
- Usar linguagem de consulta: "consulte", "acompanhe", "visualizacao".
- Mostrar metricas antes dos filtros e da lista em visualizacoes de colecao, usando `StatCard`.
- Manter consistencia entre visualizacoes do sistema: se o modulo apresenta uma colecao administrativa, o cabecalho deve ter cards de resumo sempre que existirem contadores claros.
- Permitir abrir detalhes sem mudar para modo de edicao.
- Em mobile, trocar tabelas densas por cards quando a tabela nao couber bem.
- Cards read-only podem ser clicaveis quando abrirem detalhe/drawer de consulta; nesse caso devem usar cursor/hover coerente com navegacao.
- Se o card read-only nao abrir detalhe, ele nao deve parecer clicavel e nao deve conter acoes de edicao.
- Usar `EmptyState` quando nao houver resultados.
- Manter acao secundaria, como imprimir, no `PageHeader`.

## Tipografia de cards

- Titulo principal do card: `text-base font-bold text-gray-800`.
- Badge de status em cards: `text-xs font-bold`, com padding compacto e borda.
- Descricao do card: `text-sm text-gray-500`.
- Metadados de card, como data, hora, telefone, local e contadores secundarios: `text-xs text-gray-400 font-medium`.
- Icones em metadados de card: `w-3.5 h-3.5 text-gray-400`.
- Espacamento entre metadados: `gap-x-4 gap-y-1.5`, com `items-center`.
- Telas de visualizacao e gerenciamento do mesmo modulo devem manter a mesma escala tipografica para cards equivalentes.

## Acoes rapidas de status

- Em telas de gerenciamento, mudancas simples de status podem aparecer como acoes rapidas no contexto do item.
- As acoes devem seguir transicoes de negocio claras, como em escalas (`RASCUNHO` -> `PUBLICADA` -> `ENCERRADA`).
- A edicao completa permanece no modal; a acao rapida deve alterar apenas o status.
- Mostrar apenas transicoes validas para o status atual do item.
- Evitar acoes rapidas de retorno quando o item ja estiver em estado final, como realizado ou cancelado; nesse caso, usar o modal de edicao para reduzir ruido visual e evitar ambiguidade.
- Usar rotulos verbais orientados a acao quando o nome do status de destino puder ser ambiguo. Exemplo: `Cancelar evento` em vez de `Cancelado`.
- Usar botoes compactos: `px-3 py-1.5 text-xs font-semibold rounded-xl`.
- Acoes rapidas devem respeitar a mesma permissao visual das demais acoes de gerenciamento.

## Regras de navegacao

- Rotas read-only devem usar sufixo `/visualizacao` quando forem alternativa a rota de gerenciamento.
- A sidebar deve separar "Gerenciar", "Visualizacao" e "Exportacao" quando o modulo tiver essas variacoes.
- BASIC comum nao deve acessar visualizacoes administrativas.
- BASIC lider/co-lider pode acessar visualizacoes de ministerios/escalas apenas no escopo permitido.
- `/minhas-escalas` e uma visualizacao do membro, nao uma rota administrativa.

## Exemplos de uso

### Visualizacao read-only com metricas

```tsx
<PageHeader
  title="Visualizacao de membros"
  description="Consulte membros, contatos e participacao sem editar."
/>

<div className="grid">
  <StatCard title="Ativos" value={stats.ativos} icon={icon} />
  <StatCard title="Sem telefone" value={stats.semContato} icon={icon} />
</div>
```

### Visualizacao read-only com drawer

```tsx
<DataTable
  columns={columns}
  data={items}
  loading={loading}
  emptyTitle="Nenhum membro encontrado"
/>

<MemberProfileDrawer
  membro={selected}
  onClose={() => setSelected(null)}
/>
```

### Visualizacao de escala

```tsx
<PageHeader title="Visualizacao de escalas" action={<button>Imprimir</button>} />

{escalas.map((escala) => (
  <EscalaReadonlyGrid key={escala.id} escala={escala} />
))}
```

## Anti-padroes identificados na auditoria

- `StatBox` local duplicando `StatCard`.
- Tabela read-only manual quando `DataTable` poderia ser adaptado.
- Filtros read-only visualmente diferentes dos filtros CRUD.
- Cards de metricas locais em `/minhas-escalas` e `/escalas/visualizacao`.
- Mistura de rotas read-only e gerenciais sem padrao uniforme em alguns modulos.



---

## Compartilhamento de Documentos em Visualizações

Telas de visualização read-only com dados periódicos (`/escalas/visualizacao`, `/agenda/visualizacao`) devem padronizar o botão de compartilhamento no `PageHeader`:

```tsx
<PageHeader
  title="Visualização"
  description="Consulte e acompanhe as informações."
  action={(
    <button
      onClick={openExportDialog}
      disabled={loading || items.length === 0 || exporting !== null}
      aria-label="Compartilhar"
      title="Compartilhar"
      className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {exporting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Share2 className="h-4 w-4" />}
    </button>
  )}
/>
```

O controle deve ser sempre mediado por `<ExportShareDialog />` e pelo hook `useDocumentShare`.
