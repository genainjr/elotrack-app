# ODS - CRUD Standard

## Objetivo

Definir o padrao unico para futuras telas CRUD do OneElo, usando os padroes mais consistentes encontrados em `membros`, `configuracoes`, `agenda`, `ministerios`, `escalas` e `admin`.

O padrao escolhido e:

- `PageHeader` para titulo e acao primaria.
- Hook de dominio para carregar e mutar dados.
- `DataTable` para listagem tabular quando a entidade couber em tabela.
- Modal para criar/editar.
- Confirmacao custom para destruicao/desativacao futura.

## Estrutura padrao

1. Carregar dados pelo hook do modulo.
2. Carregar usuario atual quando permissao visual depender de perfil.
3. Renderizar `PageHeader`.
4. Renderizar filtros quando houver busca/listagem.
5. Renderizar erro inline com acao de retry.
6. Renderizar tabela, cards ou grade conforme tipo de entidade.
7. Renderizar modal de criacao/edicao.
8. Renderizar modal de confirmacao para acoes destrutivas.

## Componentes obrigatorios

- `PageHeader`
- Hook de dominio (`useMembros`, `useEventos`, `useEscalas`, `useMinisterios` ou equivalente)
- Estado de `loading`
- Estado de `error`
- `EmptyState` para lista vazia
- Modal para criar/editar
- Acao primaria condicionada por permissao

Para CRUD tabular:

- `DataTable`
- `Column<T>[]`
- Coluna de acoes quando o usuario puder gerenciar

## Componentes opcionais

- Filtros em card.
- Selecao em massa e banner fixo, apenas quando houver acoes em lote.
- `MembroSearchCombobox` para vinculo com membro.
- Tabs no modal quando a entidade tiver subareas reais.
- Cards quando a experiencia atual do modulo for card-based, como ministerios e agenda.
- Grade/matriz quando a entidade for escala.

## Regras de UX

- Usar uma unica acao primaria no `PageHeader`.
- Usar texto de acao claro: novo, salvar, cancelar, arquivar, desativar, excluir.
- Desabilitar botoes durante salvamento.
- Fechar modal somente apos sucesso.
- Exibir erro do formulario dentro do modal.
- Exibir erro de carregamento acima da visualizacao principal.
- Evitar `alert()` e `confirm()` em novos fluxos.
- Manter a entidade selecionada em estado explicito (`editingItem`, `selectedItem` ou equivalente).
- Distinguir destruir, arquivar e desativar pela linguagem da UI.
- Em cards de gerenciamento, nao usar clique no card inteiro para editar; manter acoes explicitas no contexto do item.
- Acoes de editar devem usar botao iconico compacto com borda neutra, fundo branco, hover neutro e icone indigo.
- Acoes destrutivas ou de desativacao devem usar botao iconico compacto com borda vermelha clara, icone/texto vermelho e hover vermelho claro.
- Em mobile, manter as mesmas acoes explicitas dos cards/tabelas desktop, alinhadas ao fim do card quando forem acoes administrativas.
- Cards de gerenciamento nao devem parecer navegaveis quando nao houver acao de detalhe.

## Regras de navegacao

- CRUD operacional deve estar dentro de `(dashboard)`.
- CRUD de plataforma deve estar dentro de `(admin)`.
- A rota principal deve ser a rota de gerenciamento:
  - `/membros`
  - `/ministerios`
  - `/escalas`
  - `/agenda`
  - `/configuracoes`
- Rotas read-only e exportacao devem ser separadas:
  - `/membros/visualizacao`
  - `/membros/exportacao`
  - `/escalas/visualizacao`
  - `/escalas/exportacao`
- A sidebar deve expor a rota apenas para perfis autorizados visualmente.

## Exemplos de uso

### CRUD tabular

```tsx
const { items, loading, error, createItem, updateItem, deleteItem } = useItems();
const [editingItem, setEditingItem] = useState<Item | null>(null);
const [modalOpen, setModalOpen] = useState(false);

<PageHeader
  title="Itens"
  description="Gerencie os itens do modulo."
  action={canManage ? <button onClick={openCreate}>Novo</button> : undefined}
/>

{error && <div>{error}<button onClick={refetch}>Recarregar</button></div>}

<DataTable
  columns={columns}
  data={items}
  loading={loading}
  emptyTitle="Nenhum item encontrado"
  emptyDescription="Crie um novo item ou ajuste os filtros."
/>

<ItemModal
  isOpen={modalOpen}
  item={editingItem}
  onClose={closeModal}
  onSave={handleSave}
/>
```

### CRUD com cards

```tsx
<PageHeader title="Ministerios" action={canManage ? <button>Novo</button> : undefined} />

{items.length === 0 ? (
  <EmptyState title="Nenhum ministerio" description="Crie o primeiro ministerio." />
) : (
  <div className="grid">
    {items.map((item) => <EntityCard key={item.id} item={item} />)}
  </div>
)}
```

## Anti-padroes identificados na auditoria

- Tabela manual no Super Admin em vez de `DataTable`.
- Modais CRUD inline com shells repetidos.
- `confirm()` nativo em membros, ministerios, agenda e escalas.
- `alert()` para sucesso/erro em fluxos CRUD.
- Mutacoes diretas na pagina quando ja existe hook de dominio.
- Mistura de labels e cores de status locais com utilitarios compartilhados.
- Busca repetida de usuario atual em varias paginas para calcular permissoes.

