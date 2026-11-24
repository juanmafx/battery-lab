# battery-lab documentation

This page covers the whole docs tree: seven pages, listed in the order they read best.

| Page | What's in it |
|---|---|
| [Why charge limits matter](why.md) | The story, the physics of high state of charge, what a cap costs, realistic expectations, and the landfill case. |
| [How it works](how-it-works.md) | The collect-to-show pipeline, the 60/75 firmware cycle, the three questions the log answers, and why the tool stays read-only. |
| [Install and use](install.md) | Installing, the `collect`, `json`, `show`, `trend` and `simulate` commands, cron, where files live, and the `collect.py` shim. |
| [Data format](data-format.md) | Every CSV column and its units, how machines are identified, and how header changes are migrated. |
| [Statistical methods](methods.md) | The trend estimators, their complexity, reproducibility, measured behavior and limitations. |
| [Known quirks](quirks.md) | Firmware and sensor oddities, and how battery-lab handles each one. |
| [Architecture](ARCHITECTURE.md) | Why each module exists, how to run the tests, and the repository layout. |

---

Next: [Why charge limits matter](why.md)

[Project README](../README.md)
