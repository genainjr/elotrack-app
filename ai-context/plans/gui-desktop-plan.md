# Plano de Implementação: Interface Gráfica Desktop (CustomTkinter)

## 📌 Contexto
O Elo Track precisava de uma interface visual simples, moderna e de alto desempenho para usuários que não querem operar via terminal, mantendo o consumo de recursos leve e o desacoplamento total do core.

---

## 🎯 Escopo Entregue

1. **Janela Principal Moderna (`EloTrackApp`):**
   - Tema Dark nativo com acentos em azul.
   - Badge dinâmico no cabeçalho indicando o status do FFmpeg (`● FFmpeg OK`).
2. **Entrada de Link:**
   - Campo estilizado com botão `📋 Colar` direto da área de transferência.
3. **Seleção de Formatos:**
   - `MP3 (320 kbps)`
   - `WAV (Lossless para Stems)`
   - `FLAC (Lossless)`
   - `M4A (AAC)`
4. **Corte de Trechos Opcional:**
   - Switch para exibir/ocultar campos de tempo inicial e final (MM:SS ou segundos).
5. **Seletor de Diretório:**
   - Mostra caminho atual, botão para alterar pasta e botão para abrir a pasta no Explorer do Windows.
6. **Execução em Background Thread:**
   - Todo download roda em `threading.Thread`, mantendo a UI responsiva a 60 fps.
7. **Barra de Progresso e Métricas:**
   - Atualização em tempo real de porcentagem, velocidade de transferência e tempo restante estimado (ETA).
8. **Player Interativo com Marcadores de Corte (Trimmer):**
   - Reprodução integrada de áudio via `pygame-ce` diretamente no app.
   - Linha do tempo com slider interativo para arrastar e ouvir qualquer ponto da música.
   - Botões `[ 📍 Marcar Início Aqui ]` e `[ 📍 Marcar Fim Aqui ]` que preenchem os tempos com 1 clique a partir da reprodução atual.
   - Botão `[ 🔁 Testar Trecho Marcado ]` para pré-escuta de validação antes da extração definitiva.
9. **Card de Conclusão:**
   - Exibição do arquivo gerado com tamanho em MB e botão de 1 clique para reproduzir no player padrão.
