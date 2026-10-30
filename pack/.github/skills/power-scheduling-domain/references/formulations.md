# Standard scheduling formulations in GAMS idiom

Sets: `g` units, `t` intervals (ordered), with `alias(t, tt)`.

Data: `pmax(g)`, `pmin(g)`, `mc(g)`, `noload(g)`, `startup(g)`, `rampUp(g)`/`rampDown(g)` per interval, `minUp(g)`/`minDown(g)` in intervals, `u0(g)` and `p0(g)` for the initial status and output, `demand(t)`, `dur(t)` for interval length in hours.

Variables: `u(g,t)` binary on/off, `v(g,t)` start-up, `w(g,t)` shut-down (continuous in [0,1] is enough when `u` is binary), `p(g,t)` output MW.

## Balance and reserves

```gams
balance(t)..  sum(g, p(g,t)) =e= demand(t);
reserve(t)..  sum(g, pmax(g)*u(g,t) - p(g,t)) =g= reserveReq(t);
```

## Output limits tied to commitment

```gams
maxOut(g,t).. p(g,t) =l= pmax(g)*u(g,t);
minOut(g,t).. p(g,t) =g= pmin(g)*u(g,t);
```

## Commitment logic with initial status

```gams
commit(g,t).. u(g,t) - u(g,t-1) - u0(g)$(ord(t) = 1) =e= v(g,t) - w(g,t);
```

`u(g,t-1)` is dropped at the first interval, so `u0(g)` must enter explicitly. Missing `u0` makes every unit "start" at `t1`.

## Minimum up / down time (window form)

```gams
minUpC(g,t)..   sum(tt$(ord(tt) >= ord(t) - minUp(g) + 1 and ord(tt) <= ord(t)), v(g,tt)) =l= u(g,t);
minDownC(g,t).. sum(tt$(ord(tt) >= ord(t) - minDown(g) + 1 and ord(tt) <= ord(t)), w(g,tt)) =l= 1 - u(g,t);
```

Units already on or off at the start may still owe up/down time from before the horizon. That needs data, e.g. hours already on, and either fixed `u` values for the first intervals or adjusted windows.

## Ramping (interval-length aware)

```gams
rampUpC(g,t)..   p(g,t) - p(g,t-1) - p0(g)$(ord(t) = 1) =l= rampUp(g)*dur(t) + pmax(g)*v(g,t);
rampDownC(g,t).. p(g,t-1) + p0(g)$(ord(t) = 1) - p(g,t) =l= rampDown(g)*dur(t) + pmax(g)*w(g,t);
```

If ramp rates are per minute or per hour, convert them consistently to the interval length. The start-up and shut-down terms (`pmax·v`, `pmax·w`) are a common simplification; tighter forms use start-up/shut-down ramp limits.

## Objective (energy in MWh)

```gams
objective.. cost =e= sum((g,t), mc(g)*p(g,t)*dur(t) + noload(g)*u(g,t)*dur(t) + startup(g)*v(g,t));
```

For sub-hourly intervals, forgetting `dur(t)` overstates energy cost by a factor of 1/dur.

## Piecewise-linear costs

With convex segments (increasing marginal cost), plain continuous segment variables are enough:

```gams
p(g,t) =e= pmin(g)*u(g,t) + sum(s, seg(g,t,s));
seg.up(g,t,s) = segWidth(g,s);
```

Non-convex curves need SOS2 or binaries; otherwise the solver fills cheap segments out of order.

## Contracts (energy over a window)

```gams
contractMin(k).. sum((g,t)$(contractUnit(k,g) and inWindow(k,t)), p(g,t)*dur(t)) =g= minEnergy(k);
```

Check that the window set `inWindow(k,t)` matches the contract's dates and interval resolution.
