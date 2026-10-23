# Plano de Implementação: Separação de Stems Local (Demucs v4)

## 📌 Contexto
Permitir que músicos, produtores e analistas de áudio dividam uma música baixada em quatro faixas individuais (vocais, bateria, baixo e outros instrumentos) diretamente no computador local, sem depender de créditos do Moises ou upload para nuvem.

---

## 🎯 Arquitetura Proposta

1. **Implementar `DemucsStemProcessor(AudioProcessor)`:**
   - Implementa a interface `AudioProcessor` definida em `src/core/interfaces.py`.
   - Localiza ou invoca o modelo `demucs` (via biblioteca Python `demucs` ou CLI subprocess).
2. **Modelo Padrão:**
   - `htdemucs` (Hybrid Transformer Demucs v4) - melhor balanço entre velocidade e qualidade acústica.
3. **Detecção de Hardware:**
   - Detectar presença de GPU NVIDIA CUDA (`torch.cuda.is_available()`).
   - Se GPU disponível: usar float16/CUDA para separação rápida (< 1 minuto por música).
   - Se CPU: usar multithreading com fallback gracioso.
4. **Organização das Faixas:**
   - Criação de pasta dedicada: `<output_dir>/<nome_da_faixa>_stems/` contendo:
     - `vocals.wav`
     - `drums.wav`
     - `bass.wav`
     - `other.wav`
5. **Integração na GUI e CLI:**
   - CLI: flag `--separate` ou `--stems`.
   - GUI: Checkbox "Separar Instrumentos (Vocais, Bateria, Baixo) com Demucs".
