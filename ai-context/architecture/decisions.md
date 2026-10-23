# Decisões de Arquitetura (ADRs) - Elo Track

Registro das principais decisões de engenharia adotadas no Elo Track.

---

## ADR 01: Uso de `yt-dlp` em vez de `pytube`
- **Contexto:** `pytube` frequentemente sofre quebras quando o YouTube atualiza suas tags internas e algoritmos de decifração de assinaturas (cipher n-token), além de não suportar streams em qualidade superior sem junção de vídeo.
- **Decisão:** Adotar `yt-dlp`, a biblioteca mais ativamente mantida, resiliente a mudanças do YouTube e com suporte nativo a hooks de progresso e formatos de áudio.
- **Consequência:** Dependência estável, com atualizações rápidas pela comunidade.

---

## ADR 02: Execução Local vs. Cloud API
- **Contexto:** Serviços online de download costumam enfrentar bloqueios severos de IP de datacenter pelo YouTube, geram custos de hospedagem e impõem limites de taxa.
- **Decisão:** Manter execução 100% local no dispositivo do usuário, simulando requisições residenciais.
- **Consequência:** Zero custo de infraestrutura, privacidade total dos arquivos e sem restrições de cota.

---

## ADR 03: Desacoplamento via Protocolos (`typing.Protocol`)
- **Contexto:** O sistema precisava nascer em CLI, mas com migração garantida para GUI Desktop (CustomTkinter/PySide) e modelos de IA.
- **Decisão:** Definir interfaces estruturais com `@runtime_checkable` `typing.Protocol` para `ProgressReporter`, `AudioDownloader` e `AudioProcessor`.
- **Consequência:** Permite que qualquer camada visual ou pós-processador se conecte ao core sem alterar as classes de serviço fundamentais.

---

## ADR 04: Autodescoberta de FFmpeg no Windows
- **Contexto:** Usuários do Windows frequentemente instalam o FFmpeg via WinGet ou Chocolatey, mas novas variáveis de ambiente não são herdadas por terminais que já estavam abertos.
- **Decisão:** O `EnvironmentValidator` verifica não apenas `shutil.which()`, mas também as chaves de Registro do Windows (`HKCU\Environment` e `HKLM\...\Environment`) e o diretório `%LOCALAPPDATA%\Microsoft\WinGet\Packages`, injetando o caminho no `os.environ["PATH"]` do processo.
- **Consequência:** A aplicação localiza e usa o FFmpeg imediatamente após a instalação, sem obrigar o usuário a reiniciar a máquina ou reabrir seu shell.

---

## ADR 05: Adoção do CustomTkinter para Desktop GUI
- **Contexto:** A interface desktop necessitava de visual moderno (Dark mode, cantos arredondados, fontes limpas), sem o peso de dependências massivas de compilação como Qt (PySide6) para uso pessoal ágil.
- **Decisão:** Adotar `CustomTkinter` sobre a base estável nativa do Tkinter.
- **Consequência:** Inicialização ultra-rápida (< 0.5s), baixo consumo de memória (< 30 MB) e aparência nativa moderna.

---

## ADR 06: Controle Centralizado de Versão e Invalidação Obrigatória (Sunset)
- **Contexto:** Em softwares comerciais distribuídos, versões legadas geram custos de suporte, utilizam contratos quebrados de APIs de terceiros e inviabilizam modelos de monetização futuros.
- **Decisão:** Implementar um serviço desacoplado `VersionService` que valida na inicialização a versão mínima suportada (`min_supported_version`). Versões obsoletas têm suas operações de download travadas e exibem um painel de direcionamento para o novo instalador.
- **Consequência:** Garante que 100% da base ativa migre compulsoriamente para as versões homologadas vigentes.

---

## ADR 07: Distribuição Oficial via Instalador Windows (Inno Setup)
- **Contexto:** Distribuir apenas executáveis portáteis soltos não oferece a experiência comercial esperada em ambiente Windows corporativo ou de consumo final (ausência de desinstalador, pastas desorganizadas, falta de atalhos no Menu Iniciar).
- **Decisão:** Adotar o Inno Setup como gerador oficial do instalador (`EloTrack-Setup-vX.Y.Z.exe`), instalando em pastas de sistema (`Program Files` ou `AppData/Programs`), criando atalhos e gerando o desinstalador nativo `unins000.exe`.
- **Consequência:** Experiência de instalação profissional, limpa e rastreável pelo Windows.
