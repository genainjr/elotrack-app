# Elo Track 🎵

Extrator de áudio em alta fidelidade a partir de URLs do YouTube, projetado primariamente para alimentar ferramentas de separação de stems (como **Moises** e modelos locais **Demucs**).

Construído em Python com arquitetura modular desacoplada, seguindo os princípios **SOLID** e padrões de engenharia de software para facilitar a migração entre CLI e interfaces gráficas (CustomTkinter/PySide6) e a extensão para pipelines automáticos de pós-processamento.

---

## 🏗️ Arquitetura do Sistema

A aplicação adota separação estrita de responsabilidades (**SoC**) e inversão de dependência (**DIP**):

```text
elotrack-app/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── interfaces.py       # Contratos: AudioDownloader, ProgressReporter, AudioProcessor
│   │   ├── downloader.py       # Motor concreto desacoplado baseado em yt-dlp
│   │   ├── validator.py        # Validação de URLs, checagem de FFmpeg e permissões de disco
│   │   └── config.py           # Configurações globais, formatos, codecs e bitrates
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── console_reporter.py # Adaptador de progresso para terminal interativo
│   └── main.py                 # Ponto de entrada CLI
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_downloader_contract.py
│   └── test_validator.py
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

### Princípios de Engenharia Aplicados:

1. **Single Responsibility (SRP):** Cada módulo possui um único papel bem definido. O downloader não imprime na tela nem desenha interface; a interface apenas consome eventos.
2. **Open/Closed Principle (OCP):** Novos estágios de processamento (como separação de stems ou normalização de volume) são implementados estendendo o contrato `AudioProcessor`, sem modificar o código do downloader.
3. **Liskov Substitution (LSP) & Interface Segregation (ISP):** Contratos definidos via `typing.Protocol` (`ProgressReporter`, `AudioDownloader`, `AudioProcessor`).
4. **Dependency Inversion (DIP):** O orquestrador depende de contratos abstratos, permitindo plugar adaptadores de CLI, GUI (CustomTkinter/PySide) ou logging silencioso.

---

## ⚙️ Pré-requisitos e Dependências

### 1. Python
- Python 3.10 ou superior (testado no Python 3.14).

### 2. FFmpeg (Obrigatório para extração e conversão de áudio)
O FFmpeg é necessário para extrair as faixas de áudio na melhor qualidade e converter para MP3/WAV/FLAC.

- **Windows:**
  ```powershell
  # Opção 1 (Recomendada via Winget):
  winget install Gyan.FFmpeg

  # Opção 2 (Via Chocolatey):
  choco install ffmpeg

  # Opção 3 (Via Scoop):
  scoop install ffmpeg
  ```
- **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt update && sudo apt install ffmpeg
  ```
- **macOS:**
  ```bash
  brew install ffmpeg
  ```

Para testar se o FFmpeg está pronto no seu sistema, execute:
```bash
python -m src.main --check-env
```

---

## 🚀 Instalação

1. Acesse o diretório do projeto:
   ```bash
   cd elotrack-app
   ```

2. Crie e ative um ambiente virtual (opcional, porém recomendado):
   ```bash
   python -m venv .venv
   # No Windows:
   .venv\Scripts\activate
   # No Linux/macOS:
   source .venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
   *(Para rodar testes de desenvolvimento, instale `pip install -r requirements-dev.txt`)*

---

## 💻 Guia de Uso (CLI)

### 1. Download Padrão em Alta Fidelidade (MP3 320 kbps)
```bash
python -m src.main "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### 2. Download Sem Perdas para Stems (WAV ou FLAC Nativo)
Ideal para ferramentas como **Moises** e **Demucs**, garantindo máxima resolução sem perdas de compressão secundária:
```bash
# WAV (PCM 16-bit nativo)
python -m src.main "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -f wav

# FLAC
python -m src.main "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -f flac
```

### 3. Extração com Corte de Trecho (Time Range)
Baixa e extrai apenas a parte necessária, economizando banda e processamento:
```bash
# Baixa do segundo 30 até o minuto 02:15
python -m src.main "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --start 00:30 --end 02:15
```

### 4. Customização de Diretório de Destino
```bash
python -m src.main "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o "D:/Musicas/StemsInput"
```

### 5. Download em Lote (Batch File)
Crie um arquivo `links.txt` com uma URL por linha:
```bash
python -m src.main -b links.txt -f wav
```

### 6. Diagnóstico de Ambiente
```bash
python -m src.main --check-env
```

---

## 🧩 Evolutividade e Extensões

### Conectando a uma Interface Gráfica (PySide / CustomTkinter)

Graças ao desacoplamento através de `ProgressReporter`, plugar uma GUI não requer alteração de nenhuma linha do core:

```python
from src.core.downloader import YtDlpAudioDownloader
from src.core.interfaces import DownloadRequest, DownloadResult, ProgressEvent, ProgressReporter

class CustomTkinterReporter(ProgressReporter):
    def __init__(self, progress_bar_widget, status_label_widget):
        self.progress_bar = progress_bar_widget
        self.status_label = status_label_widget

    def on_progress(self, event: ProgressEvent) -> None:
        # Atualiza barra visual da GUI de 0.0 a 1.0
        self.progress_bar.set(event.percentage / 100.0)
        self.status_label.configure(
            text=f"{event.percentage:.1f}% - {event.downloaded_mb:.1f} MB"
        )

    def on_stage_changed(self, stage, message: str) -> None:
        self.status_label.configure(text=message)

    def on_complete(self, result: DownloadResult) -> None:
        self.status_label.configure(text=f"Pronto: {result.title}")

    def on_error(self, error, url: str) -> None:
        self.status_label.configure(text=f"Erro: {error}")
```

### Pipeline de Pós-Processamento: Separação de Stems com Demucs

Para acoplar separação local de instrumentos diretamente no fluxo de download:

```python
from pathlib import Path
from src.core.interfaces import AudioProcessor

class DemucsStemSeparator(AudioProcessor):
    @property
    def name(self) -> str:
        return "Demucs v4 (Local HTDemucs)"

    def process(self, audio_path: Path, **kwargs) -> Path:
        import subprocess
        # Executa demucs localmente na faixa extraída
        subprocess.run(["demucs", "-n", "htdemucs", str(audio_path)], check=True)
        # Retorna pasta ou stem desejado
        return audio_path.parent / "separated" / "htdemucs" / audio_path.stem

# Uso no request:
# req = DownloadRequest(url=..., output_dir=..., post_processors=[DemucsStemSeparator()])
```

---

## 🧪 Testes Automatizados

O projeto conta com suíte de testes unitários cobrindo validadores, conformidade de contratos e pipelines de extensão:

```bash
cd elotrack-app
pytest -v
```

---

## 📦 Distribuição e Instalador Comercial para Windows

O Elo Track é projetado como um produto comercial com governança da **Lookup Labs**.

### 1. Instalador Oficial (`.exe`) via Inno Setup
Para gerar o instalador profissional com suporte a pastas do sistema (`Program Files`), atalhos no Menu Iniciar/Área de Trabalho e Desinstalador nativo do Windows:

```powershell
python build_exe.py --installer
```
* O instalador é gerado em: `dist/installer/EloTrack-Setup-v1.0.0.exe` (comprimido via LZMA2 Solid Ultra).

### 2. Política de Controle de Versão e Invalidação (Sunset Policy)
* O aplicativo possui um módulo de ciclo de vida (`src/core/version.py`) que valida a versão mínima suportada (`min_supported_version`).
* **Invalidação Compulsória:** Quando uma nova versão for publicada, versões antigas são bloqueadas e impedidas de realizar novos downloads, direcionando o usuário para o instalador oficial atualizado.
* Para mais detalhes da governança comercial, consulte [`ai-context/business-rules/commercial-lifecycle-and-versioning.md`](ai-context/business-rules/commercial-lifecycle-and-versioning.md).

