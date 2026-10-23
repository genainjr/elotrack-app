# Padrões de Testes Automatizados - Elo Track

Diretrizes para escrita e manutenção de testes unitários e de integração no Elo Track.

---

## 🧪 Estratégia de Testes

1. **Testes Rápidos e Determinísticos:**
   - Nenhum teste unitário deve fazer requisições HTTP reais ao YouTube ou baixar arquivos de gigabytes.
   - O `yt-dlp` e chamadas ao sistema operacional são mockados via `unittest.mock.patch`.
2. **Suíte Atual:**
   - `test_config.py`: validação de enums (`AudioFormat`, `AudioBitrate`), defaults de diretório e leitura de variáveis de ambiente (`ELO_TRACK_OUTPUT_DIR`).
   - `test_validator.py`: validação exaustiva de expressões regulares de URLs válidas/inválidas e checagem de permissões de pastas temporárias.
   - `test_downloader_contract.py`: validação de contrato de download, chamadas de callbacks do `ProgressReporter`, interceptação de erros do `yt_dlp.DownloadError` e extensibilidade do pipeline de `AudioProcessor`.
   - `test_gui_reporter.py`: garantia de disparo correto de eventos para a interface gráfica.

---

## 🏃 Como Rodar

```powershell
cd elotrack-app
pytest -v
```
