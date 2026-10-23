# Plano de Implementação: Empacotamento em Executável Portátil (.exe)

## 📌 Contexto
Facilitar a distribuição e o uso do Elo Track em computadores Windows 10 e 11 que não possuam ambiente de desenvolvimento Python instalado.

---

## 🎯 Arquitetura de Empacotamento

1. **Ferramenta de Build:** `PyInstaller` ou `Nuitka`.
2. **Configuração de Build (`elotrack.spec`):**
   - Inclusão dos assets visuais do `customtkinter` (temas JSON e imagens SVG/PNG).
   - Flag `--noconsole` para evitar que uma janela de prompt preta fique aberta atrás da interface gráfica.
   - Ícone personalizado `.ico`.
3. **Distribuição do FFmpeg:**
   - Opção A: O executável instrui o usuário a instalar via winget caso ausente.
   - Opção B: O build empacota o binário estático `ffmpeg.exe` dentro do bundle do executável ou extrai para `%LOCALAPPDATA%\EloTrack\bin`.
4. **Passo a Passo de Build:**
   ```powershell
   pip install pyinstaller
   pyinstaller --noconsole --name "EloTrack" --icon "assets/icon.ico" --add-data "src/gui;src/gui" src/main.py
   ```
