# Padrão de Testes Automatizados - Elo Track

## Regras Obrigatórias para Testes:

1. **Determinismo:**
   - Testes unitários nunca devem depender de conexão de rede ou downloads reais do YouTube.
2. **Mocking Estruturado:**
   - Utilizar `unittest.mock.patch` e spies para testar `ProgressReporter`.
3. **Cobertura Essencial:**
   - Validadores de URLs e diretórios devem ter cobertura de cenários válidos, inválidos e extremos (strings nulas, pastas sem permissão).
   - Testes de regressão são obrigatórios para cada nova feature adicionada.
