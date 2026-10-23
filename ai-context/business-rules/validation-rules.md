# Regras de Validação e Ambiente - Elo Track

Critérios obrigatórios para garantir resiliência e integridade operacional antes de disparar qualquer download.

---

## 1. Validação de URLs do YouTube

A validação de URLs é realizada pela classe `URLValidator` através de expressão regular segura.

### URLs Aceitas:
- Padrão: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- Encurtada: `https://youtu.be/dQw4w9WgXcQ`
- Shorts: `https://youtube.com/shorts/dQw4w9WgXcQ`
- YouTube Music: `https://music.youtube.com/watch?v=dQw4w9WgXcQ`
- Embed: `https://youtube.com/embed/dQw4w9WgXcQ`
- Links com parâmetros adicionais (ex: timestamps `&t=30s` ou `feature=share`).

### Sanitização Automática de Mix/Playlists:
- Quando a URL contém um vídeo específico associado a um Mix do YouTube (ex: `&list=RD...` ou `&start_radio=1`), o `URLValidator.clean_video_url` e o `YtDlpAudioDownloader` sanitizam automaticamente o link para `https://www.youtube.com/watch?v=<ID>` e aplicam `noplaylist: True`, evitando que o motor entre em download sequencial de todas as músicas do Mix da rádio do YouTube.

### URLs Rejeitadas:
- Links que não sejam do ecossistema YouTube (SoundCloud, Vimeo, Spotify).
- URLs com ID de vídeo menor ou maior que 11 caracteres alfanuméricos.
- Strings nulas, vazias ou contendo apenas espaços em branco.

---

## 2. Validação de Dependência: FFmpeg

O `EnvironmentValidator` aplica 3 níveis de busca para garantir a presença do binário:

1. **PATH Ativo:** Consulta direta via `shutil.which("ffmpeg")`.
2. **Registro do Windows:** Leitura das chaves `HKCU\Environment` e `HKLM\...\Environment` para detectar instalações recentes que ainda não foram herdadas pelo shell atual.
3. **Pastas de Pacotes WinGet / Choco:** Varredura em `%LOCALAPPDATA%\Microsoft\WinGet\Packages\**\ffmpeg.exe`.

Se encontrado, o diretório pai do `ffmpeg.exe` é automaticamente adicionado ao `os.environ["PATH"]` do processo corrente para que tanto o `yt-dlp` quanto os subprocessos de pós-processamento o utilizem transparentemente.

---

## 3. Validação de Diretório de Destino

O `FileSystemValidator` garante que:
- O diretório seja criado recursivamente se não existir (`mkdir(parents=True)`).
- O caminho corresponda a uma pasta e não a um arquivo regular.
- Haja permissão real de escrita no disco (testada via criação e remoção atômica de um arquivo probe temporário `.write_probe.tmp`).
