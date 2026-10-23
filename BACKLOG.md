# 📋 Backlog do Projeto - Elo Track

Registro de evolução, arquitetura planejada e itens priorizados para as próximas versões.

---

## 📌 Status Geral das Demandas

| ID | Épico / Funcionalidade | Prioridade | Status |
| :---: | :--- | :---: | :---: |
| **ELO-01** | **Interface Gráfica Desktop (GUI CustomTkinter)** | 🟢 Alta (Imediata) | ✅ Concluído |
| **ELO-03** | **Empacotamento Executável Portátil (.exe com PyInstaller)** | 🟡 Média | ✅ Concluído |
| **ELO-05** | **Metadados e Capa Embutida (Thumbnail & Tags ID3)** | 🟢 Alta | ✅ Concluído |
| **ELO-06** | **Histórico Visual de Downloads Recentes com Playback** | 🟢 Alta | ✅ Concluído |
| **ELO-07** | **Instalador Oficial para Windows (.exe via Inno Setup com Pastas e Atalhos)** | 🟢 Alta | ✅ Concluído |
| **ELO-08** | **Controle Rígido de Versão e Invalidação de Versões Antigas (Sunset Policy)** | 🟢 Alta | ✅ Concluído |
| **ELO-02** | **Pipeline Local de Separação de Stems (Demucs v4 - IA)** | 🟡 Média | 📝 No Backlog |
| **ELO-04** | **Download de Playlists Completas e Busca Direta por Nome** | 🔵 Baixa | 📝 No Backlog |

---

## 🚀 Detalhamento dos Itens do Backlog

### [ELO-01] Interface Gráfica Desktop (GUI Moderna com CustomTkinter)
- **Objetivo:** Fornecer uma interface visual moderna, escura e responsiva para usuários que preferem não usar linha de comando.
- **Componentes Técnicos:**
  - Adaptador `GuiProgressReporter(ProgressReporter)` thread-safe para atualizar barras e labels via `root.after()`.
  - Execução de downloads em background thread (`threading.Thread`) para não congelar a janela durante o processamento.
  - Seletor de formatos com um clique: `MP3 (320 kbps)`, `WAV (Lossless)`, `FLAC`.
  - Seletor visual de diretório de saída com botão de abrir pasta no Explorer.
  - Suporte a corte de trechos (`--start` / `--end`) através de interface simples.
  - Botão de colagem rápida (Paste) da área de transferência.
- **Critérios de Aceite:**
  - Janela abre com `python -m src.main --gui` ou executando `src.main` sem argumentos em ambiente gráfico.
  - Barra de progresso reflete porcentagem real, velocidade e ETA sem travar a interface.

---

### [ELO-02] Pipeline Local de Separação de Stems com Demucs (IA)
- **Objetivo:** Integrar separação de faixas local (vocais, bateria, baixo e outros instrumentos) diretamente após o download do áudio.
- **Componentes Técnicos:**
  - Implementação de `DemucsStemProcessor(AudioProcessor)`.
  - Download opcional de modelos leves (`htdemucs` ou `htdemucs_ft`).
  - Suporte a aceleração via GPU (CUDA / PyTorch) com fallback automático para CPU.
  - Organização automática das faixas em pastas dedicadas (`stems/<track_name>/vocals.wav`).
- **Critérios de Aceite:**
  - Ativação via flag CLI `--separate` / `--stems` ou checkbox na GUI.
  - Geração dos 4 arquivos de stems preservando a qualidade master em WAV 44.1kHz.

---

### [ELO-03] Empacotamento em Executável Portátil (.exe com PyInstaller)
- **Objetivo:** Permitir a distribuição e execução do Elo Track em qualquer máquina Windows sem necessidade de ter o Python previamente instalado.
- **Componentes Técnicos:**
  - Script de build com `pyinstaller` empacotando dependências (`customtkinter`, `yt-dlp`).
  - Inclusão do binário estático do `ffmpeg` em pasta embutida ou verificação transparente.
  - Criação de atalho e ícone personalizado `.ico`.
- **Critérios de Aceite:**
  - Arquivo `EloTrack.exe` executável com duplo clique no Windows 10/11.
  - Inicialização limpa e autônoma sem console preta no modo GUI.

---

### [ELO-04] Download de Playlists Completas e Busca Direta
- **Objetivo:** Facilitar a extração de múltiplos links de uma vez ou baixar diretamente buscando pelo nome da faixa.
- **Componentes Técnicos:**
  - Suporte a detecção de URL de Playlist do YouTube com fila sequencial de download.
  - Suporte ao prefixo `ytsearch:` do `yt-dlp` para permitir buscas textuais diretas (ex: `elo-track "Nome da Música Artista"`).
- **Critérios de Aceite:**
  - Processamento em lote de playlists com relatório de sucesso para cada item da lista.
