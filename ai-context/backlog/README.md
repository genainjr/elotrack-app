# Backlog e Roadmap - Elo Track

Registro unificado de demandas, épicos de evolução e status do produto.

---

## 🎯 Matriz de Épicos

| ID | Épico | Prioridade | Status | Especificação |
| :---: | :--- | :---: | :---: | :--- |
| **ELO-01** | Interface Gráfica Desktop (CustomTkinter) | 🟢 Alta | ✅ **Concluído** | [Plano GUI](../plans/gui-desktop-plan.md) |
| **ELO-02** | Pipeline Local de Separação de Stems (Demucs v4) | 🟡 Média | 📝 **No Backlog** | [Plano Demucs](../plans/stems-demucs-plan.md) |
| **ELO-03** | Empacotamento em Executável Portátil (.exe com PyInstaller) | 🟡 Média | 📝 **No Backlog** | [Plano Executável](../plans/packaging-exe-plan.md) |
| **ELO-04** | Download de Playlists e Busca Direta por Nome | 🔵 Baixa | 📝 **No Backlog** | Em refinamento |

---

## 📋 Detalhamento das Próximas Entregas

### ELO-02: Separação de Stems Local (Demucs)
- Permite transformar o áudio baixado em 4 faixas isoladas (`vocals.wav`, `drums.wav`, `bass.wav`, `other.wav`).
- Implementado via protocolo `AudioProcessor` em `src/core/interfaces.py`.
- Suporte a GPU CUDA quando disponível com fallback para CPU.

### ELO-03: Distribuição Portátil (.exe)
- Gerar pacote autônomo com PyInstaller para Windows 10/11.
- Sem necessidade de ter Python ou dependências instaladas.
- Ícone personalizado `.ico` e abertura direta em modo GUI.
