# Fluxo de Dados e Ciclo de Vida - Elo Track

Descreve a sequência de eventos desde a entrada de um link até a entrega do arquivo de áudio finalizado no disco.

---

## Diagrama de Sequência de Download

```mermaid
sequenceDiagram
    autonumber
    actor Usuario
    participant Interface as CLI / Desktop GUI
    participant Downloader as YtDlpAudioDownloader
    participant Validator as Validators (URL, Pasta, FFmpeg)
    participant YtDlp as yt-dlp & FFmpeg
    participant Reporter as ProgressReporter

    Usuario->>Interface: Informa URL e clica em Baixar
    Interface->>Downloader: download(DownloadRequest, reporter)
    
    Downloader->>Validator: Valida URL (is_valid_youtube_url)
    Downloader->>Validator: Valida Pasta (validate_output_directory)
    Downloader->>Validator: Localiza FFmpeg (get_ffmpeg_path)
    
    Downloader->>Reporter: on_stage_changed(STARTING)
    Downloader->>YtDlp: Inicia extração (bestaudio/best)
    
    loop Durante o Download
        YtDlp->>Downloader: Hook de progresso
        Downloader->>Reporter: on_progress(ProgressEvent: % / Speed / ETA)
    end
    
    YtDlp->>Downloader: Conversão FFmpeg iniciada
    Downloader->>Reporter: on_stage_changed(CONVERTING)
    
    opt Se houver AudioProcessors (ex: Demucs)
        Downloader->>Reporter: on_stage_changed(PROCESSING)
        Downloader->>Downloader: Executa processor.process(output_path)
    end
    
    Downloader->>Reporter: on_complete(DownloadResult)
    Downloader-->>Interface: Retorna DownloadResult(success=True)
    Interface-->>Usuario: Exibe confirmação e botão para abrir áudio
```

---

## Estrutura do `ProgressEvent`

Cada evento emitido pelo motor de download contém:

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `status` | `ProgressStatus` | Enum: `STARTING`, `DOWNLOADING`, `CONVERTING`, `PROCESSING`, `FINISHED`, `ERROR` |
| `url` | `str` | URL original da solicitação |
| `filename` | `Optional[str]` | Nome temporário ou final do arquivo |
| `downloaded_bytes` | `int` | Bytes já recebidos |
| `total_bytes` | `Optional[int]` | Tamanho total estimado em bytes |
| `percentage` | `float` | Percentual concluído (0.0 a 100.0) |
| `speed_bytes_sec` | `Optional[float]` | Velocidade instantânea em bytes/segundo |
| `eta_seconds` | `Optional[int]` | Tempo restante estimado em segundos |
