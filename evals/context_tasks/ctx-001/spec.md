# Unit Commitment Formulation (sandbox copy, version 7, last updated 2024-03-02)

## 3.4 Spinning reserve

The spinning reserve requirement is **15% of hourly demand**. Reserve is provided by the unused capacity of committed units:

$$ \sum_g \left(P^{max}_g u_{g,t} - p_{g,t}\right) \ge 0.15 \cdot D_t \quad \forall t $$
