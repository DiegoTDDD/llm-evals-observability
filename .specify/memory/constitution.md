# Constitution: llm-evals-observability

1. **Numbers come from runs.** Every figure in the README or the dashboard is produced by a
   committed run's files; nothing is typed by hand.
2. **The gate replays real behaviour.** Offline checks use calls the model really made, never
   invented inputs.
3. **The projects stay untouched.** Tracing and evaluation wrap the projects' own scripts.
4. **Free to run.** Local model, GitHub Actions and GitHub Pages; no paid key.
5. **Every change is tested** (pytest, ruff) before it is pushed.
