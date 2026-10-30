* Unit data for the small unit commitment test model
Set g 'generating units' / coal1, ccgt1, ct1 /;

Table unitData(g,*) 'unit characteristics'
          pmax   pmin   mc    noload  startup  ramp  minup  mindown  init_on  init_p
coal1     300    120    18    800     4000     80    4      4        1        200
ccgt1     200     70    28    400     1500     100   2      2        0        0
ct1       100     20    55    150      300     100   1      1        0        0
;
