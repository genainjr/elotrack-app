# Padrão de Processamento de Áudio - Elo Track

## Regras Obrigatórias para Mídia:

1. **Seleção de Stream:**
   - Sempre solicitar `bestaudio/best` do `yt-dlp`.
2. **Fidelidade de Stems:**
   - Para extrações destinadas a Moises ou Demucs, utilize WAV linear PCM (`pcm_s16le`) ou FLAC.
   - Não recompactar arquivos WAV com bitrates com perdas.
3. **Cortes de Trechos:**
   - Sempre que `time_range` for especificado, utilizar o recurso de download de trecho do `yt-dlp` (`download_range_func`) ou corte direto com FFmpeg sem reencodificações desnecessárias.
4. **Metadados:**
   - Preservar título, artista/canal e metadados ID3 sempre que possível.
