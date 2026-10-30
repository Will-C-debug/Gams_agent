# Sets, domains and conditions

## Sets and domains

- **Explicit domains.** `Set g 'units' / g1*g3 /;` and `Parameter cap(g) 'MW';` give domain checking at compile and load time. `Parameter cap(*)` disables it.
- **Subsets.** `Set active(g) 'units in service';` is a subset, so its elements must be in `g`. Dynamic subsets (assigned at execution time) are the usual way to drive `$` conditions.
- **Aliases.** Use an alias when the same set appears twice in one expression: `alias (t, tt); sum(tt$(ord(tt) <= ord(t)), x(tt))`. Without the alias, `t` would be controlled twice.
- **Singletons.** `Singleton Set` holds at most one element. GAMS 53 defaults to `strictSingleton=1`, so assigning several elements is an error.

## Conditions

| Form | Meaning |
|---|---|
| `e(i)$c(i)..` | Generates rows only where `c(i)` is non-zero. **This controls which constraints exist.** |
| `... =l= a(i)$c(i)` | The term is zero where `c(i)` is zero; the row still exists. |
| `x(i)$c(i) = ...;` | Assigns only where `c(i)` holds; other values are untouched. |
| `x(i) = ...$c(i);` | Assigns everywhere and sets zero where `c(i)` is false. **Different from the line above.** |
| `sum(i$c(i), ...)` | Sums over the filtered set. |

Prefer conditions on existing data (`$cap(g)`) over `ord` arithmetic. They keep models sparse and readable.

## Ordered sets, lag and lead

- **`ord` and `card`.** `ord(t)` works only on ordered sets (static sets whose elements appear in order). `card(t)` is the set size.
- **Linear lags.** `x(t-1)` refers to the previous element; at the first element the reference is outside the set and the term is dropped (zero).
- **Circular lags.** `x(t--1)` wraps to the last element; use it for cyclic horizons only.
- **Boundaries.** Initial conditions must be explicit: `u(g,t) - u(g,t-1) - u0(g)$(ord(t)=1) =e= v(g,t) - w(g,t);`. Check both ends of the horizon: first-period terms, and terminal or end-of-horizon constraints.
- **Window sums.** For "the last N periods" constraints (minimum up/down time), filter with `ord(tt) >= ord(t) - N + 1 and ord(tt) <= ord(t)`, and decide how the window treats periods before the horizon (initial status carried in).

## Element comparisons

- **`sameas`.** `sameas(i,'a')` compares labels; `sameas(i,j)` compares elements across sets.
- **Text with special characters.** Labels are case-insensitive, but labels in data files must match the set elements exactly once quotes and spaces are considered.
