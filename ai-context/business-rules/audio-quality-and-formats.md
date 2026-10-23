# Regras de Áudio e Formatos - Elo Track

Diretrizes de fidelidade sonora para garantir que as faixas extraídas sejam adequadas para stems (Moises, Demucs) ou para reprodução padrão de alta qualidade.

---

## 1. Origem das Streams no YouTube
- O YouTube entrega áudio tipicamente codificado em **Opus** (taxa média de 160 kbps, 48 kHz) ou **AAC** (128 kbps a 256 kbps).
- O seletor de streams configurado é rigorosamente `bestaudio/best`, garantindo que o algoritmo do `yt-dlp` selecione a stream com a maior fidelidade acústica disponível no servidor.

---

## 2. Formatos de Saída Suportados

### 🎯 WAV (PCM 16-bit) - **Recomendado para Stems (Moises / Demucs)**
- **Codec:** `pcm_s16le`.
- **Por que usar:** O WAV decodifica a stream original diretamente para amostras lineares não comprimidas. Ao alimentar redes neurais de separação de fontes (como Demucs ou Spleeter), o áudio não sofre com nova quantização ou artefatos de compressão secundária.

### 🎯 FLAC (Lossless)
- **Codec:** `flac`.
- **Por que usar:** Mesma integridade matemática do WAV, mas com compressão de tamanho de ~40% a 50%. Ideal para arquivamento e ferramentas que aceitam FLAC nativamente.

### 🎯 MP3 (CBR 320 kbps) - **Uso Pessoal & Escuta Geral**
- **Taxa de bits:** Taxa de bits constante de 320 kbps (máximo padrão do padrão MP3).
- **Por que usar:** Máxima compatibilidade com tocadores de áudio antigos, aparelhos de som e compartilhamento rápido.

### 🎯 M4A (AAC)
- **Codec:** AAC em contêiner MP4.
- **Por que usar:** Excelente eficiência perceptual mantendo metadados completos da Apple/M4A.

---

## 3. Metadados e Tags de Áudio
- Sempre que disponível, o extrator injeta metadados ID3 via `FFmpegMetadata`:
  - Título da faixa
  - Nome do artista / canal / uploader
  - Duração
  - Thumbnail embutida (opcional)
