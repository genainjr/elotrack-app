# Camadas e Responsabilidades - Elo Track

A base de código segue uma arquitetura em camadas concêntricas (inspirada em Clean Architecture e Hexagonal):

```text
src/
├── core/         # CAMADA DE DOMÍNIO E SERVIÇOS CENTRAIS (Isolada)
├── adapters/     # ADAPTADORES DE SAÍDA (Apresentação / Relatórios)
├── gui/          # INTERFACE GRÁFICA DO USUÁRIO (CustomTkinter)
└── main.py       # PONTO DE ENTRADA E COMPOSIÇÃO (CLI Dispatcher)
```

---

## 1. Camada Core (`src/core`)
Não possui dependências com GUI ou CLI. Contém a lógica de negócio pura e integrações com o sistema operacional.

- **`interfaces.py`:**
  - Define as entidades imutáveis (`ProgressEvent`, `DownloadRequest`, `DownloadResult`, `ProgressStatus`).
  - Define os contratos (`ProgressReporter`, `AudioDownloader`, `AudioProcessor`).
- **`downloader.py`:**
  - Implementação concreta `YtDlpAudioDownloader`.
  - Configura yt-dlp em modo silencioso, intercepta hooks internos e despacha para `ProgressReporter`.
  - Executa a cadeia de pós-processamento `AudioProcessor`.
- **`validator.py`:**
  - `EnvironmentValidator`: autolocaliza o binário FFmpeg pelo PATH, registro do Windows ou pastas WinGet.
  - `URLValidator`: valida expressões regulares de links do YouTube (padrão, shorts, music, embed).
  - `FileSystemValidator`: testa existência e permissão de escrita de pastas de destino.
- **`config.py`:**
  - Centraliza defaults de diretórios, bitrates, codecs suportados e configuração de `logging`.

---

## 2. Camada de Adaptadores (`src/adapters`)
Implementa os contratos definidos no Core para diferentes meios de saída.

- **`console_reporter.py`:**
  - Renderiza barra de progresso em tempo real no terminal com velocidade, tamanho e tempo restante.
  - Tratamento de encoding compatível com terminais legados Windows (CP1252/OEM) e UTF-8.
- **`gui_reporter.py`:**
  - Ponte entre os eventos de download do core e a interface gráfica `CustomTkinter`.

---

## 3. Camada de Interface Gráfica (`src/gui`)
- **`app.py`:**
  - Implementa a janela desktop moderna (`EloTrackApp`) em `CustomTkinter`.
  - Despacha tarefas de download para threads de background (`threading.Thread`) para preservar fluidez visual.
  - Utiliza `root.after()` para atualizar widgets Tk de forma thread-safe.

---

## 4. Ponto de Entrada (`src/main.py`)
- Ponto de entrada unificado:
  - Invocado sem parâmetros ou com `--gui` -> Inicia a interface gráfica desktop.
  - Invocado com URL e flags (`-f`, `-q`, `-o`, `--start`, `--end`) -> Executa em modo CLI silencioso ou interativo.
