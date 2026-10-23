# Visão Geral da Arquitetura - Elo Track

O **Elo Track** é uma ferramenta desktop para download e extração de áudio em alta fidelidade a partir de links do YouTube, projetada para alimentar fluxos de trabalho de produção musical, transcrição e separação de instrumentos/vocais.

---

## 🎯 Objetivos de Design

1. **Desacoplamento Completo entre Apresentação e Domínio:**
   - O core de negócio pode ser executado via CLI, via GUI (CustomTkinter), via API local (FastAPI) ou como script de automação sem alterar uma única linha de código do motor.
2. **Alta Fidelidade Sonora:**
   - Evitar transcodificações degradantes acumuladas. A stream original Opus/AAC é convertida para PCM 16-bit linear (WAV) ou mantida em MP3 320 kbps com preservação de ID3 tags.
3. **Open/Closed Principle (OCP):**
   - Novas etapas (recortes, filtros acústicos, separadores de stems Demucs) são conectadas como processadores encadeados através do protocolo `AudioProcessor`.
4. **Independência de Nuvem e Baixa Frequência de Uso:**
   - Execução 100% cliente local, eliminando bloqueios de datacenter pelo YouTube.

---

## 🧩 Visão Estrutural

```text
               ┌───────────────────────────┐
               │    Entradas de Usuário    │
               │   (CLI ou Desktop GUI)    │
               └─────────────┬─────────────┘
                             │ Cria DownloadRequest
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │                   AudioDownloader                      │
 │              (YtDlpAudioDownloader)                    │
 ├────────────────────────────────────────────────────────┤
 │ 1. Valida URL (URLValidator)                           │
 │ 2. Valida Permissões de Pasta (FileSystemValidator)    │
 │ 3. Detecta e Injeta FFmpeg (EnvironmentValidator)      │
 │ 4. Configura e Executa yt-dlp                          │
 └─────────────┬───────────────────────────┬──────────────┘
               │ Emite ProgressEvent       │ Executa se houver
               ▼                           ▼
 ┌───────────────────────────┐   ┌───────────────────────────┐
 │     ProgressReporter      │   │      AudioProcessor       │
 │ - ConsoleProgressReporter │   │ - DemucsStemProcessor     │
 │ - GuiProgressReporter     │   │ - AudioTrimmer            │
 └───────────────────────────┘   └───────────────────────────┘
```

---

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Propósito |
| :--- | :--- | :--- |
| **Linguagem** | Python 3.10+ | Execução local multiplataforma |
| **Engine de Download** | `yt-dlp` | Extração de metadados e streams de melhor bitrate |
| **Motor de Mídia** | `FFmpeg` | Transcodificação, corte e injeção de metadados |
| **Interface Gráfica** | `CustomTkinter` | UI desktop moderna em Dark Mode |
| **Contratos** | `typing.Protocol` | Interfaces formais desacopladas |
| **Testes** | `pytest`, `pytest-mock` | Garantia de qualidade e regressão |
