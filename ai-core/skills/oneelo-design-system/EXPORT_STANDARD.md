# ODS - Export Standard

## Objetivo

Definir o padrao unico para paginas de exportacao do OneElo, consolidando as quatro paginas existentes:

- `/membros/exportacao`
- `/ministerios/exportacao`
- `/escalas/exportacao`
- `/agenda/exportacao`

O padrao escolhido e a estrutura comum ja existente: `PageHeader`, card central, formato, selecao de campos, resumo e botao de exportar CSV usando `downloadCsv`.

## Estrutura padrao

1. `PageHeader` com titulo "Exportacao de <Modulo>" e descricao.
2. Card central com largura contida.
3. Secao "Formato".
4. Secao "Campos".
5. Acoes "Selecionar todos" e "Limpar".
6. Resumo com quantidade de registros e campos selecionados.
7. Botao principal "Exportar CSV".
8. `downloadCsv(filename, headers, rows)` para gerar o arquivo.

## Componentes obrigatorios

- `PageHeader`
- `downloadCsv`
- `ALL_FIELDS`
- `selectedFields`
- `toggleField`
- `handleExport`
- Estado de `loading`
- Botao desabilitado quando:
  - loading ativo;
  - nenhum campo selecionado;
  - nenhum registro disponivel.

## Componentes opcionais

- Labels de status a partir de utilitarios compartilhados.
- Formatacao de data usando utilitario existente.
- Formato XLSX desabilitado com indicacao "em breve", como no padrao atual.
- Resumo com icone informativo.

## Regras de UX

- Exportacao deve ficar em rota separada do CRUD.
- CSV e o formato ativo padrao.
- XLSX so deve aparecer desabilitado enquanto nao existir suporte.
- Todos os campos devem iniciar selecionados.
- O usuario deve poder limpar e selecionar todos.
- O botao de exportacao deve ocupar largura total do card.
- O nome do arquivo deve incluir modulo e data ISO curta.
- Datas devem ser exportadas em formato legivel para o usuario.

## Regras de navegacao

- Rotas de exportacao devem seguir o padrao:
  - `/membros/exportacao`
  - `/ministerios/exportacao`
  - `/escalas/exportacao`
  - `/agenda/exportacao`
- A sidebar deve agrupar exportacao como filho do modulo.
- Exportacao deve respeitar as mesmas permissoes visuais do modulo administrativo.
- BASIC comum nao deve ver exportacao administrativa.

## Exemplos de uso

```tsx
const ALL_FIELDS = [
  { key: 'nome', label: 'Nome' },
  { key: 'createdAt', label: 'Criado em' },
];

const [selectedFields, setSelectedFields] = useState(
  ALL_FIELDS.map((field) => field.key),
);

function handleExport() {
  const active = ALL_FIELDS.filter((field) => selectedFields.includes(field.key));
  const headers = active.map((field) => field.label);
  const rows = items.map((item) => active.map((field) => item[field.key] ?? ''));

  downloadCsv(`modulo-${new Date().toISOString().slice(0, 10)}.csv`, headers, rows);
}
```

## Anti-padroes identificados na auditoria

- Quatro paginas com a mesma estrutura reimplementada.
- `STATUS_LABEL` duplicado nas paginas de exportacao.
- Formatacao de data local com `new Date(...).toLocaleDateString`.
- Logica repetida de resumo, selecao de campos e botao.
- `ALL_FIELDS` definido de forma isolada em cada pagina sem contrato comum.



---

## Compartilhamento e Exportação de Documentos (PDF e PNG Semanal)

Para telas de visualização que oferecem exportação e compartilhamento rápido de documentos visuais (como `/escalas/visualizacao` e `/agenda/visualizacao`), o ODS estabelece um padrão único:

### Componentes e Hooks Obrigatórios
- `<ExportShareDialog />` (`@/components/app/export-share-dialog`): Diálogo acessível em 2 etapas (Escolha do formato PDF vs Imagem e Seleção da semana civil / todas as semanas).
- `<ExportSharePreparedBanner />` e `<ExportShareErrorBanner />`: Feedback visual consistente para download/recompartilhamento e erros (503, falhas de rede).
- `useDocumentShare` (`@/hooks/use-document-share`): Hook unificado que gerencia estados de loading, cache de sessão em memória, chamadas aos endpoints de exportação (`/api/<modulo>/exportacao`), integração com a Web Share API (`navigator.share`) e fallback resiliente para download direto (`downloadFile`).
- Utilitários de calendário (`@/lib/export-calendar-weeks`): Agrupamento uniforme por semana civil.

### Padrão Visual dos Documentos Gerados
1. **PDF A4 Paisagem:**
   - Grid de cabeçalho padronizado (Logo do Tenant, Título, Período e Organização);
   - Rodapé One Elo / Lookup Labs com logo institucional;
   - Agrupamento obrigatório por dias da semana com faixas coloridas semânticas (`ROLE_COLORS`) e tabelas zebradas.
2. **PNG Semanal (1080px):**
   - Folha vertical `1080px` com cabeçalho de alta resolução;
   - Cartões estruturados (`.event-card`) com faixas coloridas semânticas, data grande (`44px`), dia da semana por extenso, pílula de categoria e linhas de detalhamento (`.assignment-row`).
