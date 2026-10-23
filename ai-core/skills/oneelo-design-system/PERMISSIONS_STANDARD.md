# ODS - Permissions Standard

## Objetivo

Definir o padrao unico de permissoes visuais, navegacao e acoes no frontend do OneElo, com base nas regras atuais de navegacao e nos achados da auditoria.

Este documento trata apenas do frontend. O backend permanece a fonte de verdade de autorizacao.

## Estrutura padrao

1. Obter usuario atual via `/api/auth/me`.
2. Determinar visibilidade de rotas e acoes com base em:
   - `User.role`;
   - lideranca ministerial quando aplicavel;
   - escopo do ministerio selecionado quando existir.
3. Esconder rotas bloqueadas na sidebar.
4. Esconder acoes bloqueadas na pagina.
5. Manter protecao real no backend.

## Componentes obrigatorios

- `Sidebar` com itens filtrados por perfil.
- `DashboardLayout` para areas autenticadas.
- `AdminLayout` para area Super Admin.
- Checagens de permissao visual antes de renderizar acoes primarias.
- Checagens de permissao visual antes de renderizar acoes de linha/card/grade.

## Componentes opcionais

- Estado `canManage`.
- Estado `canCreate`.
- Estado `canManageSelected...`.
- Indicadores read-only quando usuario pode visualizar mas nao editar.
- Empty state ou mensagem de escopo vazio quando BASIC lider nao tiver entidades gerenciaveis.

## Regras de UX

- Nunca mostrar botao que o usuario nao pode executar.
- BASIC comum deve ter experiencia centrada em `/minhas-escalas`, `/agenda` e `/meu-perfil`.
- BASIC lider/co-lider pode ver acoes apenas no escopo dos ministerios onde lidera/co-lidera.
- ADMIN pode ver configuracoes.
- STAFF nao deve ver areas exclusivas de ADMIN.
- SUPER_ADMIN deve ficar na area `/admin`.
- A UI pode esconder acoes, mas nao deve assumir que isso autoriza a operacao.

## Regras de navegacao

### ADMIN

Pode acessar a experiencia administrativa do tenant:

- `/dashboard`
- `/membros`
- `/membros/visualizacao`
- `/membros/exportacao`
- `/ministerios`
- `/ministerios/exportacao`
- `/escalas`
- `/escalas/visualizacao`
- `/escalas/exportacao`
- `/agenda`
- `/agenda/exportacao`
- `/meu-perfil`
- `/configuracoes`

### STAFF

Pode acessar a operacao global do tenant, exceto areas exclusivas de ADMIN:

- `/dashboard`
- `/membros`
- `/membros/visualizacao`
- `/ministerios`
- `/escalas`
- `/escalas/visualizacao`
- `/agenda`
- `/meu-perfil`

### BASIC comum

Fluxo principal:

- login cai em `/minhas-escalas`;
- pode acessar `/minhas-escalas`;
- pode acessar `/agenda`;
- pode acessar `/meu-perfil`.

Nao deve acessar areas administrativas.

### BASIC lider/co-lider

Tem o menu BASIC com acesso adicional, escopado aos ministerios onde e lider ou co-lider:

- `/ministerios`
- `/escalas`
- `/escalas/visualizacao`

### SUPER_ADMIN

Usa somente a area de plataforma:

- `/admin/login`
- `/admin`

Nao deve ser direcionado para o dashboard operacional do tenant.

## Exemplos de uso

### Acao primaria condicionada

```tsx
<PageHeader
  title="Agenda"
  description="Gerencie eventos."
  action={canManage ? <button onClick={openCreate}>Novo evento</button> : undefined}
/>
```

### Acoes de item condicionadas

```tsx
{canManage && (
  <div>
    <button onClick={() => openEdit(item)}>Editar</button>
    <button onClick={() => requestDelete(item)}>Excluir</button>
  </div>
)}
```

### Escopo por entidade selecionada

```tsx
const canManageSelected = canManage || isLeaderOfSelectedMinistry;

{canManageSelected && <button>Salvar alteracoes</button>}
```

## Anti-padroes identificados na auditoria

- Busca repetida de `/api/auth/me` em layout e paginas.
- Regras de visibilidade espalhadas por paginas.
- Diferenca entre logout de `AdminLayout` e login de Super Admin.
- Acoes administrativas condicionadas localmente sem padrao comum de nomenclatura.
- Rotas futuras aparecem na sidebar como coming soon, mas ainda exigem criterio de visibilidade consistente.

