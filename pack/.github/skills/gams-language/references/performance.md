# Performance: generation and execution

Most slow GAMS runs are slow *before* the solver starts. Check the log's "Generating ... model" step and the time between it and "Executing CPLEX".

## Patterns

- **Sparse equations.** Condition equation domains on existing data, e.g. `flow(i,j)$arc(i,j)..`. A dense cross-product with zero coefficients still costs generation time and memory.
- **Parallel assignments over loops.** `a(i,j)$c(i,j) = b(i)*d(j);` is far faster than `loop((i,j)$c(i,j), a(i,j) = ...);`.
- **Avoid repeated `sum` inside `loop`.** Precompute aggregates into parameters.
- **Order of indices.** Keep index order consistent with the symbol's declared domain order in assignments and sums; mismatched order slows execution on large data.
- **Many small solves.** `solveLink = 5` (in memory) avoids writing the model to disk each time. For scenario sweeps, use GUSS.

## Measuring

- **Statement-level timing.** `option profile = 1;` (or `profile=1` on the command line) reports time and memory per statement in the listing. `profileTol` hides fast statements.
- **Job steps.** `stepSum=1` reports resources per job step.
- **Model size.** The log line `--- N rows M columns K non-zeroes` and the range statistics are the first things to compare between two versions. `gams_run` returns both.
