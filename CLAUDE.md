# Claude Code project guide

Follow [AGENTS.md](AGENTS.md) and [docs/PROJECT_INSTRUCTIONS_KO.md](docs/PROJECT_INSTRUCTIONS_KO.md) as binding project instructions. Read the repo before modifying. Do not operate on user's Windows machine or claim actual GUI/API verification without evidence.

Development model: one feature per tested branch/PR, finish acceptance gates, then integrate. Never expose/commit API keys. Report Korean progress: overall %, finished, remaining, tests PASS/FAIL/SKIP, current SHA, next action. New source providers require API/license/terms review first.

First priority: long take >=180s semantics and the preview failure from the V1.0.2 screenshot. Treat stock poster and actual video playback as separate features. No silent fallback to short clips.
