# 🏢 Ciclo de Vida Comercial, Versionamento e Invalidação de Versões - Elo Track

Este documento estabelece as diretrizes estratégicas e técnicas de produto para a transição do **Elo Track** de utilitário interno para software comercial desktop com governança da **Lookup Labs**.

---

## 1. Visão de Produto e Comercialização

Embora o aplicativo esteja atualmente em estágio de pré-lançamento e homologação técnica, sua arquitetura foi concebida para **comercialização e monetização futura**.

### Pilares de Negócio:
1. **Controle de Acesso Centralizado:** O software não pode ser distribuído como um binário eterno e incontrolável. A empresa deve ter controle sobre quais versões estão ativas no mercado.
2. **Ciclo de Vida Enforcado (Enforced Version Sunset):** Quando uma versão do EloTrack for atualizada (seja por motivos de segurança, compatibilidade com o YouTube ou modelo de assinatura), **as versões antigas devem deixar de funcionar**, direcionando o usuário para o instalador oficial mais recente.
3. **Distribuição via Instalador Padrão do Windows:** Abandonar a distribuição exclusiva via executável portátil solto (`.zip`/pasta). O produto final é distribuído como um **Instalador Oficial do Windows (`.exe`)** que cria pastas de sistema, atalhos no Menu Iniciar, ícones na Área de Trabalho e registro de desinstalação no Painel de Controle do Windows.

---

## 2. Padrão de Versionamento Semântico (SemVer)

O Elo Track adota rigorosamente o padrão **SemVer 2.0.0** (`MAJOR.MINOR.PATCH`):

```
v1.0.0
 │ │ └─ PATCH: Correções de bugs, ajustes cosméticos ou compatibilidade de regex do YouTube.
 │ └─── MINOR: Novas funcionalidades (ex: separação de stems Demucs, download de playlists).
 └───── MAJOR: Mudanças de modelo de licenciamento, arquitetura ou quebras de compatibilidade.
```

- **Fonte da Verdade:** A versão oficial do aplicativo é definida exclusivamente no módulo [`src/core/version.py`](file:///c:/workspace/lookup/elotrack-app/src/core/version.py) através da constante `__version__ = "1.0.0"`.
- A versão é estampada nos metadados do executável compilado, na barra de título do aplicativo e no instalador gerado.

---

## 3. Política de Invalidação de Versão (Sunset & Deprecation Policy)

### 3.1 O Problema das Versões Antigas
Softwares que extraem conteúdo de plataformas externas como o YouTube sofrem quebras inevitáveis devido a alterações nos contratos da plataforma (cipher tokens, rotas de stream). Além disso, em um modelo comercial pago:
- Usuários que cancelaram ou estão em versões obsoletas não podem continuar utilizando infraestrutura da empresa.
- Bugs já corrigidos não devem poluir o canal de suporte.

### 3.2 Como Funciona o Mecanismo de Invalidação
O serviço `VersionService` localizado em [`src/core/version.py`](file:///c:/workspace/lookup/elotrack-app/src/core/version.py) opera no momento em que a interface desktop é iniciada:

1. **Checagem de Compatibilidade:**
   - O aplicativo valida a versão local contra a política de versão mínima exigida (`min_supported_version`) e status de sunset.
   - A verificação pode ser alimentada por um arquivo remoto de release (`update.json` hospedado no repositório oficial ou CDN) ou por endpoint central de licenciamento.
2. **Ação em Caso de Versão Descontinuada:**
   - **Bloqueio Operacional:** O botão de extração e os campos de download são desabilitados.
   - **Interface de Sunset:** É exibido um painel de alerta informativo no padrão Lookup Labs informando:
     > *"Esta versão do Elo Track (vX.Y.Z) foi descontinuada e não funciona mais. Para continuar baixando e extraindo áudios em alta fidelidade, por favor atualize para a versão mais recente."*
   - **Botão de Atualização:** Redireciona o usuário diretamente com 1 clique para o instalador oficial atualizado (`EloTrack-Setup.exe`).

---

## 4. Requisitos do Instalador Windows (Inno Setup)

Para atender ao padrão comercial de software para Windows, a distribuição é feita via **Inno Setup**:

1. **Diretório de Destino Padrão:**
   - Usuário Padrão (Sem privilégios de Admin): `{localappdata}\Programs\EloTrack`
   - Instalação Administrativa (Todos os usuários): `{autopf}\EloTrack` (`C:\Program Files\EloTrack`)
2. **Estrutura de Pastas Instalada:**
   ```
   C:\Program Files\EloTrack\
   ├── EloTrack.exe              # Executável principal (GUI Lookup Labs)
   ├── _internal\                # Dependências binárias e bibliotecas Python
   ├── bin\                      # Binários utilitários (ffmpeg.exe, ffprobe.exe)
   ├── assets\                   # Ícones oficiais de alta resolução (.ico, .png)
   ├── unins000.exe              # Desinstalador nativo do Windows
   └── LEIA-ME.txt               # Instruções e documentação
   ```
3. **Integração com o Sistema Operacional:**
   - Entrada no Menu Iniciar: `Elo Track` e atalho de desinstalação.
   - Atalho opcional na Área de Trabalho com o ícone oficial.
   - Registro em `Configurações do Windows > Aplicativos instalados` com ícone, editor ("Lookup Labs"), versão correta e suporte à desinstalação limpa.
