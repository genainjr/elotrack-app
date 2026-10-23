# Workflow de Desenvolvimento - Elo Track

Ciclo padrão de desenvolvimento e evolução do código.

---

## 🔄 Ciclo de Entrega

1. **Definição de Contratos:**
   - Ao criar uma nova capacidade, comece especificando o contrato em `src/core/interfaces.py` (`Protocol` ou `dataclass`).
2. **Implementação de Testes de Contrato:**
   - Crie testes em `tests/` que exercitem os novos contratos antes ou durante a codificação.
3. **Implementação do Domínio:**
   - Adicione a lógica no Core sem dependência direta de UI ou CLI.
4. **Criação / Adaptação dos Adaptadores:**
   - Atualize `src/adapters/` e conecte à GUI (`src/gui/app.py`) e ao CLI (`src/main.py`).
5. **Verificação de Regressão:**
   - Rodar `pytest -v` e garantir 100% de testes passando.
6. **Atualização da Documentação de IA:**
   - Atualizar `ai-context/index.md` e os documentos relacionados caso haja novas decisões ou mudanças de arquitetura.
