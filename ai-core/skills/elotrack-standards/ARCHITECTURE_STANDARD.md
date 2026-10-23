# Padrão Arquitetural - Elo Track

## Regras Obrigatórias:

1. **Separação de Responsabilidades (SoC):**
   - O core (`src/core/`) nunca deve importar elementos de `src/gui/` ou usar `print()`.
   - Comunicação com camadas externas é estritamente via `ProgressReporter`.
2. **Inversão de Dependências (DIP):**
   - Dependa de abstrações (`typing.Protocol`), não de implementações concretas de relatórios ou pós-processadores.
3. **Open/Closed Principle (OCP):**
   - Estenda funcionalidades adicionando novos `AudioProcessor` em vez de inchar o método principal de download.
4. **Resiliência Multiplataforma:**
   - Use `Path` da biblioteca padrão `pathlib` para manipulação de caminhos de arquivos.
   - Trate codificação de caracteres com suporte seguro a terminais Windows legados (UTF-8 com fallback).
