# Repository AI Context Manifest - Elo Track

Este repositório contém a documentação técnica e o contexto de IA para o **Elo Track**, uma aplicação desktop modular e de alta fidelidade em Python para download, extração e pós-processamento de áudio do YouTube voltada para ferramentas de análise musical e separação de faixas (como **Moises** e modelos **Demucs**).

---

## 🎧 Domínios Principais

1. **Extração e Downloader Engine:** Interação com `yt-dlp` focada em streams de áudio `bestaudio/best`.
2. **Alta Fidelidade & Conversão:** Codificação sem perdas (PCM 16-bit WAV, FLAC) e lossy de alta taxa (MP3 320 kbps, AAC M4A) via binários locais do `ffmpeg`.
3. **Observabilidade & Eventos de Progresso:** Padrão Observer via `ProgressReporter` desacoplado do terminal ou da interface gráfica.
4. **Interface Gráfica Moderna (GUI):** Interface desktop construída com `CustomTkinter`, responsiva, com suporte a multithreading para garantir 60 fps durante downloads.
5. **Pós-processamento Extensível (AudioProcessor):** Pipeline aberto para cortes pontuais de trechos de áudio e separação local de stems (Demucs v4).
6. **Validação e Resiliência de Ambiente:** Autodetecção de FFmpeg no PATH, pastas WinGet e Registro do Windows.

---

## 🏛️ Arquitetura Primária

- **Linguagem:** Python 3.10+ (verificado e testado em Python 3.14).
- **Core Engine:** `yt-dlp` com integração nativa de hooks de progresso e conversão FFmpeg.
- **Transcoding / Media:** `ffmpeg` local (descoberta automática multiplataforma: Windows, Linux, macOS).
- **GUI:** `customtkinter` com tema Dark e execução assíncrona em background threads.
- **Arquitetura:** Clean Architecture / Ports and Adapters / SOLID.
- **Testes Automatizados:** `pytest` e `pytest-mock`.

---

## 📚 Contextos Importantes

- [Visão Geral da Arquitetura](architecture/overview.md)
- [Camadas e Separação de Responsabilidades](architecture/layers.md)
- [Decisões Arquiteturais (ADRs)](architecture/decisions.md)
- [Fluxo de Dados e Ciclo de Vida](architecture/data-flow.md)
- [Regras de Áudio e Formatos](business-rules/audio-quality-and-formats.md)
- [Regras de Validação e Ambiente](business-rules/validation-rules.md)
- [Ciclo de Vida Comercial, Versionamento e Invalidação](business-rules/commercial-lifecycle-and-versioning.md)
- [Backlog e Roadmap de Evolução](backlog/README.md)
- [Plano: Interface Gráfica Desktop](plans/gui-desktop-plan.md)
- [Plano: Pipeline Demucs para Stems](plans/stems-demucs-plan.md)
- [Plano: Empacotamento Executável (.exe)](plans/packaging-exe-plan.md)
- [Padrões de Testes Automatizados](testing/pytest.md)
- [Workflows de Desenvolvimento](workflows/feature-development.md)

---

## 🔒 Decisões Consolidadas

1. **Zero Cloud / Execução Local:** Não utilizar APIs ou clouds externas de download; a execução é 100% na máquina local do usuário, eliminando custos e riscos de bloqueio de datacenter.
2. **Desacoplamento Estrito:** A camada de serviço/core (`src/core`) nunca deve invocar `print()` ou referenciar widgets de tela (CLI ou GUI). Toda comunicação ocorre através do contrato `ProgressReporter`.
3. **Threading Mandatório na GUI:** Todo download invocado pela interface gráfica roda em daemon thread para nunca travar a janela (`root.after` utilizado para despachar eventos à main thread).
4. **Prioridade de Áudio Lossless para Stems:** Quando o objetivo for alimentar modelos de IA (Demucs/Moises), orientar o uso de WAV ou FLAC para evitar artefatos de dupla compressão perceptual.
5. **Resiliência a Encoding:** No Windows, assegurar que mensagens de console usem caracteres compatíveis ou fallback seguro para terminais legados (`cp1252`/OEM).
