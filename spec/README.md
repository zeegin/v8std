# Внутренние архитектурные документы

`spec/` — непубликуемый корпус требований, решений, контрактов и планов v8std.
Он не входит в сайт, навигацию и AI-артефакты из `docs/`.

## Каталоги

- `spec/designs/` — принятые design и требования;
- `spec/adr/` — атомарные архитектурные решения;
- `spec/invariants/` — проверяемые свойства продукта;
- `spec/contracts/` — версионированные наблюдаемые границы;
- `spec/plans/` — исполнимые планы реализации;
- `spec/process/` — версионированная схема архитектурного процесса.

Нормативная схема: `process:architecture-artifacts@1` в
`spec/process/architecture-artifacts-v1.md`.

Типизированные ссылки имеют вид `design:mcp-v3-resource-contract`,
`adr:PAGE_READING_VIA_RESOURCES`, `invariant:PAGE_IDENTITY_IS_STABLE`,
`contract:MCP_RESOURCE_READING@3.0` и `plan:mcp-v3-resource-contract`.

Перед локальным merge в `main` запустить:

```bash
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main --merge-ready
```
