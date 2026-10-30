# Data loading and GDX

## Filtered vs. domain-checked loads (important in GAMS 53)

GAMS 53 ships with `Filtered=on`: `$load` / `execute_load` silently skip records whose labels are not in the symbol's domain. A misspelled unit name or a new unit missing from the set simply disappears from the model.

Two ways to make that visible:

- **Domain-checked loads.** Use `$loadDC` (compile time) or `execute_loadDC` (execution time). A domain violation becomes an error.
- **Filtered loads with justification.** Keep the filtered load only on purpose, and report the dropped records: compare `card()` before and after, or load into a `*`-domain parameter and check the labels.

Review rule: every external data load is domain-checked or comes with a written justification.

## Compile time vs. execution time

| | Compile time | Execution time |
|---|---|---|
| Read GDX | `$gdxIn file` + `$load` / `$loadDC` | `execute_load` / `execute_loadDC` / `execute_loadpoint` |
| Write GDX | `$gdxOut` + `$unload` | `execute_unload` |
| Use when | Data defines sets/domains the model needs at compile time | Data changes between solves or in loops |

## Special values

| Value | Meaning | In GDX / gdxdump |
|---|---|---|
| `0` | Not stored for parameters | absent |
| `eps` | Present but zero | `Eps` |
| `na` | Not available | `NA` |
| `inf` / `-inf` | Infinite bounds | `+Inf` / `-Inf` |
| `undf` | Undefined (result of a bad operation) | `UNDF` |

`gdx_diff` treats missing records as zero, which matches GAMS semantics, and reports `Eps` vs. missing as equal.

## GAMS Connect and embedded code

- **Connect.** GAMS Connect (`$onEmbeddedCode Connect:` ... `$offEmbeddedCode`) reads and writes CSV, Excel, SQL and GDX through agents such as CSVReader, ExcelReader and GDXWriter.
- **Embedded code.** It runs code: it is disabled under the agent's `execMode=2`. Data preparation that needs it should live in a separate step that people run, not in the model the agent compiles.
- **Reviewing data steps.** Check that data steps use explicit paths from defines (`%dataDir%`), not user-specific absolute paths.

## Output contracts

- **Schema changes.** Output GDX files and reports are interfaces. Renaming symbols, changing domains or changing units breaks downstream readers, so flag these changes in reviews.
- **Size.** Use `execute_unload 'out.gdx', sym1, sym2;` with an explicit symbol list rather than unloading everything.
