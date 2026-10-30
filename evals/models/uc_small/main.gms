$title Small unit commitment test model
$onText
Hourly unit commitment over a short horizon with power balance, spinning
reserve, minimum up/down times, ramp limits and start-up costs. System
lambda is reported from the power-balance marginals of the fixed-commitment
LP that GAMS/CPLEX solves after the MIP (solvefinal).
$offText

$if not set horizon $set horizon 8
$if not set reserve $set reserve 0.10

Set t 'hours' / h1*h%horizon% /;
$include data/units.inc

Parameter demand(t) 'system demand MW'
  / h1 300, h2 320, h3 380, h4 450, h5 500, h6 470, h7 400, h8 340 /;

Scalar reserveShare 'spinning reserve as share of demand' / %reserve% /;

Binary   Variable u(g,t)  'unit on';
Positive Variable p(g,t)  'output MW'
                  v(g,t)  'start-up indicator'
                  w(g,t)  'shut-down indicator';
Variable cost 'total cost $';

v.up(g,t) = 1;
w.up(g,t) = 1;

Equation
   balance(t)     'power balance'
   reserve(t)     'spinning reserve requirement'
   maxOut(g,t)    'maximum output when on'
   minOut(g,t)    'minimum output when on'
   commit(g,t)    'on/off/start-up/shut-down logic'
   rampUp(g,t)    'ramp-up limit'
   rampDown(g,t)  'ramp-down limit'
   minUp(g,t)     'minimum up time'
   minDown(g,t)   'minimum down time'
   objective      'total cost';

balance(t)..  sum(g, p(g,t)) =e= demand(t);

reserve(t)..  sum(g, unitData(g,'pmax')*u(g,t) - p(g,t)) =g= reserveShare*demand(t);

maxOut(g,t).. p(g,t) =l= unitData(g,'pmax')*u(g,t);

minOut(g,t).. p(g,t) =g= unitData(g,'pmin')*u(g,t);

commit(g,t).. u(g,t) - u(g,t-1) - unitData(g,'init_on')$(ord(t) = 1)
              =e= v(g,t) - w(g,t);

rampUp(g,t)..   p(g,t) - p(g,t-1) - unitData(g,'init_p')$(ord(t) = 1)
                =l= unitData(g,'ramp') + unitData(g,'pmax')*v(g,t);

rampDown(g,t).. p(g,t-1) + unitData(g,'init_p')$(ord(t) = 1) - p(g,t)
                =l= unitData(g,'ramp') + unitData(g,'pmax')*w(g,t);

alias (t, tt);
minUp(g,t)..   sum(tt$(ord(tt) >= ord(t) - unitData(g,'minup') + 1 and ord(tt) <= ord(t)), v(g,tt))
               =l= u(g,t);

minDown(g,t).. sum(tt$(ord(tt) >= ord(t) - unitData(g,'mindown') + 1 and ord(tt) <= ord(t)), w(g,tt))
               =l= 1 - u(g,t);

objective..   cost =e= sum((g,t), unitData(g,'mc')*p(g,t) + unitData(g,'noload')*u(g,t)
                                  + unitData(g,'startup')*v(g,t));

Model uc / all /;
option mip = cplex, optcr = 0, threads = 1;
uc.optFile = 1;
solve uc using mip minimizing cost;

abort$(uc.modelStat <> %modelStat.optimal% and uc.modelStat <> %modelStat.integerSolution%)
   'unit commitment did not return a usable solution', uc.modelStat;

Parameter lambda(t) 'system lambda $/MWh';
lambda(t) = balance.m(t);
display u.l, p.l, lambda;
