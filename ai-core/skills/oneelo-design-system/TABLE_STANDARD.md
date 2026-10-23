# ODS - Table Standard

## Objetivo

Definir o padrao unico para tabelas, listagens tabulares e grades do OneElo, escolhendo `DataTable<T>` como padrao principal para entidades tabulares.

Grades de escala sao uma excecao de dominio ja existente e devem seguir os padroes `EscalaGrid` e `EscalaReadonlyGrid`.

## Estrutura padrao

Para tabelas de entidades:

1. Definir `Column<T>[]`.
2. Usar `DataTable`.
3. Passar `data`, `loading`, `emptyTitle` e `emptyDescription`.
4. Usar `selectedIds` e `onSelectChange` apenas quando houver acao em massa.
5. Usar `currentPage`, `totalItems`, `itemsPerPage` e `onPageChange` quando houver paginacao local.
6. Coluna de acoes deve ficar no final.

Para grades de escalas:

1. Primeira coluna fixa para data/dia.
2. Colunas seguintes para funcoes.
3. Celulas com membros escalados.
4. Variacao interativa apenas em rota de gerenciamento.
5. Variacao read-only em rota de visualizacao.

## Componentes obrigatorios

Para tabelas:

- `DataTable`
- `Column<T>[]`
- `EmptyState` via `DataTable`
- Loading skeleton
- `rowKey` quando `id` nao for suficiente

Para grades:

- Estrutura dias x funcoes.
- Estado vazio quando nao houver dias ou funcoes.
- Status de confirmacao com label/cor compartilhados.

## Componentes opcionais

- Selecao de linhas.
- Paginacao.
- Coluna de avatar/iniciais.
- Badges de status.
- Acoes inline.
- Renderizacao mobile em cards quando a tabela read-only for densa.

## Regras de UX

- Usar tabela para comparacao e operacao recorrente.
- Usar cards quando o item exigir leitura de bloco, como agenda ou ministerios.
- Usar grade apenas quando a informacao for matricial, como escala.
- A coluna de acoes deve ser visualmente discreta.
- Acoes destrutivas devem usar cor vermelha/rose.
- Estado vazio deve ocupar a tabela inteira.
- Loading deve preservar a estrutura da tabela.
- Badges devem usar labels e cores consistentes.

## Regras de navegacao

- Tabelas CRUD ficam em rotas de gerenciamento.
- Tabelas read-only ficam em rotas `/visualizacao`.
- Grade interativa de escala fica em `/escalas`.
- Grade read-only de escala fica em `/escalas/visualizacao`.
- Exportacao nao deve ser feita por botao dentro da tabela principal quando ja existir rota de exportacao.

## Exemplos de uso

### Tabela de entidade

```tsx
const columns: Column<User>[] = [
  { key: 'nome', header: 'Nome', className: 'font-semibold' },
  { key: 'email', header: 'E-mail' },
  {
    key: 'actions',
    header: '',
    render: (user) => <Actions user={user} />,
  },
];

<DataTable
  columns={columns}
  data={users}
  loading={loading}
  itemsPerPage={15}
  emptyTitle="Nenhum usuario encontrado"
  emptyDescription="Crie um novo usuario para comecar."
/>
```

### Tabela com selecao em massa

```tsx
<DataTable
  columns={columns}
  data={paginatedData}
  selectedIds={selectedIds}
  onSelectChange={setSelectedIds}
  currentPage={currentPage}
  totalItems={items.length}
  itemsPerPage={itemsPerPage}
  onPageChange={setCurrentPage}
/>
```

## Anti-padroes identificados na auditoria

- Tabela HTML manual no Super Admin.
- Tabela read-only manual em `membros/visualizacao`.
- `DataTable` nao usado em todos os casos tabulares simples.
- Badges e cores definidos dentro da tabela em vez de utilitarios compartilhados.
- Grade interativa e read-only de escalas com logicas parcialmente duplicadas.

