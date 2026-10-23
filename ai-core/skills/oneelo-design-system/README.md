# OneElo Design System (ODS)

## Objetivo

Definir o padrao unico para futuras implementacoes de frontend no OneElo, com base apenas nos padroes encontrados na auditoria do sistema atual.

O ODS consolida os nucleos reutilizaveis ja existentes:

- `PageHeader`
- `DataTable`
- `EmptyState`
- `StatCard`
- `ComingSoon`
- `MembroModal`
- `UsuarioModal`
- `MembroSearchCombobox`
- `MemberProfileDrawer`
- `EscalaReadonlyGrid`
- `downloadCsv`

## Estrutura padrao

Novas telas administrativas devem seguir esta estrutura:

1. `PageHeader` no topo da pagina.
2. Area opcional de filtros.
3. Area principal de visualizacao:
   - `DataTable` para listagens CRUD tabulares.
   - Cards apenas quando o inventario ja mostrar que o modulo usa cards como experiencia primaria.
   - Grade/matriz apenas para escalas e visualizacoes equivalentes.
4. `EmptyState` para estado vazio.
5. Modal ou drawer para criacao, edicao ou detalhamento.
6. Acoes visiveis apenas quando o usuario puder executa-las.

## Componentes obrigatorios

- `PageHeader` em paginas internas com titulo, descricao e acao primaria quando aplicavel.
- `DataTable` para tabelas de entidades com colunas configuraveis.
- `EmptyState` para listas vazias.
- Modal para criar/editar entidades.
- Feedback inline para erro de carregamento e erro de formulario.
- Hook do modulo para operacoes de API sempre que houver CRUD.

## Componentes opcionais

- `StatCard` para metricas e resumos.
- `MembroSearchCombobox` para selecao de membros.
- `MemberProfileDrawer` para detalhe lateral read-only.
- `EscalaReadonlyGrid` para visualizacao read-only de escala.
- `ComingSoon` para modulos futuros.
- Banner de acao em massa apenas para fluxos com selecao multipla, como membros.

## Regras de UX

- Usar uma acao primaria por pagina no `PageHeader`.
- Usar modal para criar/editar entidades simples.
- Usar tabs em modal apenas quando a entidade tiver subareas reais, como ministerio com info, membros e funcoes.
- Usar `EmptyState` em vez de mensagens soltas quando uma lista estiver vazia.
- Usar skeleton/loading no corpo principal, nao substituir toda a pagina sem necessidade.
- Usar confirmacao custom para acoes destrutivas futuras; `confirm()` nativo e legado.
- Manter labels, cores e status centralizados em utilitarios existentes quando disponiveis.

## Regras de navegacao

- O backend permanece a fonte de verdade de autorizacao.
- O frontend deve esconder rotas e acoes que o usuario nao pode executar.
- Paginas internas devem ficar sob o `DashboardLayout`.
- Paginas de Super Admin devem ficar sob o `AdminLayout`.
- Telas de login tenant devem usar o padrao visual do `AuthLayout`.
- BASIC comum deve ser direcionado para `/minhas-escalas`.
- SUPER_ADMIN deve usar a area `/admin`.

## Exemplos de uso

### Pagina CRUD padrao

```tsx
<PageHeader
  title="Entidade"
  description="Gerencie os registros deste modulo."
  action={canManage ? <button>Nova entidade</button> : undefined}
/>

<DataTable
  columns={columns}
  data={items}
  loading={loading}
  emptyTitle="Nenhum registro encontrado"
  emptyDescription="Ajuste os filtros ou crie um novo registro."
/>
```

### Pagina read-only padrao

```tsx
<PageHeader
  title="Visualizacao"
  description="Consulte os dados sem abrir o modo de edicao."
/>

<EmptyState
  title="Nenhum resultado encontrado"
  description="Ajuste os filtros para localizar outros registros."
/>
```

## Anti-padroes identificados na auditoria

- Shell de modal duplicado em varias paginas.
- Quatro paginas de exportacao com estrutura quase identica.
- Filtros com layouts diferentes para problemas semelhantes.
- Tabelas manuais onde `DataTable` ja atenderia.
- Cards de metrica locais duplicando `StatCard`.
- Busca repetida de `/api/auth/me` em layout e paginas.
- `alert()` e `confirm()` nativos para feedback e confirmacao.
- Labels e cores de status repetidos fora de `utils`.

## Documentos do ODS

- `CRUD_STANDARD.md`: padrao para criar, listar, editar, excluir e acoes correlatas.
- `VIEW_STANDARD.md`: padrao para paginas read-only, detalhes e metricas.
- `EXPORT_STANDARD.md`: padrao para exportacao CSV.
- `TABLE_STANDARD.md`: padrao para tabelas e grades.
- `FORM_STANDARD.md`: padrao para formularios e modais.
- `PERMISSIONS_STANDARD.md`: padrao de permissoes, navegacao e visibilidade de acoes.

