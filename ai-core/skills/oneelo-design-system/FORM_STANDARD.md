# ODS - Form Standard

## Objetivo

Definir o padrao unico para formularios do OneElo, consolidando os formularios encontrados em login, CRUD modal, filtros, perfil, exportacao e tags.

O padrao escolhido para CRUD e formulario dentro de modal, usando a estrutura de `MembroModal` e `UsuarioModal` como referencia principal.

## Estrutura padrao

Para formulario CRUD modal:

1. Overlay.
2. Container central.
3. Header com titulo e botao fechar.
4. Formulario com conteudo rolavel quando necessario.
5. Erro inline dentro do formulario.
6. Footer com Cancelar e Salvar/Criar.
7. Loading no botao principal.

Para formulario inline:

1. Card ou bloco com borda.
2. Campos agrupados em grid quando houver mais de dois campos.
3. Botoes Aplicar/Limpar ou Salvar/Cancelar.
4. Erro inline proximo ao contexto.

## Componentes obrigatorios

- Labels visiveis.
- Inputs controlados.
- Validacao minima no submit.
- Estado `loading`.
- Estado `error`.
- Botao principal desabilitado durante loading.
- Botao secundario para cancelar/limpar quando aplicavel.

Para formularios com membro:

- `MembroSearchCombobox`.

Para senha:

- Campos com `type="password"` e `autoComplete` adequado.

## Componentes opcionais

- Campo de cor para tags.
- Select de status.
- Textarea para observacoes/descricao.
- Tabs quando o formulario tiver subareas reais.
- Info box explicativa, como em `UsuarioModal`.
- Botao de mostrar/ocultar senha, como em `UsuarioModal`.

## Regras de UX

- Campo obrigatorio deve ter indicacao visual no label.
- Erro de formulario deve aparecer dentro do modal/card.
- Nao usar `alert()` para erro de formulario em novos fluxos.
- Manter foco conceitual: formulario cria/edita uma entidade ou aplica filtro.
- Nao misturar edicao de entidade principal com sub-recursos sem separacao visual.
- Usar tabs apenas para contextos complexos ja observados, como ministerios.
- Formularios longos devem ter corpo rolavel e footer fixo no modal.
- Botoes devem manter ordem: Cancelar/Limpar antes, Salvar/Criar depois.

## Regras de navegacao

- Formularios CRUD devem abrir a partir da rota de gerenciamento.
- Formularios de filtro permanecem na pagina, nao em modal.
- Formularios de exportacao ficam em rotas `/exportacao`.
- Formulario de login tenant fica em `/login`.
- Formulario de login Super Admin fica em `/admin/login`.
- Formulario de perfil fica em `/meu-perfil`.

## Exemplos de uso

### Modal CRUD simples

```tsx
if (!isOpen) return null;

return (
  <div className="fixed inset-0 z-50 flex items-center justify-center">
    <div role="dialog" aria-modal="true">
      <header>
        <h2>{item ? 'Editar' : 'Novo'}</h2>
        <button onClick={onClose}>Fechar</button>
      </header>

      <form onSubmit={handleSubmit}>
        {error && <div>{error}</div>}
        <input value={nome} onChange={(event) => setNome(event.target.value)} />

        <footer>
          <button type="button" onClick={onClose}>Cancelar</button>
          <button type="submit" disabled={loading}>Salvar</button>
        </footer>
      </form>
    </div>
  </div>
);
```

### Filtro inline

```tsx
<form onSubmit={handleFilterSubmit}>
  <input value={searchName} onChange={(event) => setSearchName(event.target.value)} />
  <select value={status} onChange={(event) => setStatus(event.target.value)} />
  <button type="submit">Aplicar</button>
  <button type="button" onClick={clearFilters}>Limpar</button>
</form>
```

## Anti-padroes identificados na auditoria

- Shell de modal repetido em varias paginas.
- Forms de login duplicados entre tenant e admin.
- Formulario de usuario duplicado entre Super Admin e Configuracoes.
- `alert()` para erro/sucesso em membros, ministerios e agenda.
- Campos e classes repetidos sem componente de campo compartilhado.
- Filtros com estrutura visual inconsistente.

