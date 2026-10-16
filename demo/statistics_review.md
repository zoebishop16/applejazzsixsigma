# Statistical review evidence

Independent repository statistics review returned **OVERALL PASS** after a requested
correction: constant baselines now reject undefined control limits. This is an
agent review and automated verification, not a claim of external scientific audit.

The reviewed implementation is `app/qc.py`; the runnable evidence is
`python -m pytest tests -q`. At H-03 verification it printed:

```text
..............                                                           [100%]
14 passed in 2.34s
```

| Check | Known answer / expected behavior | Result |
|---|---|---|
| p-chart baseline 2/20 | center .1; UCL .301246117975; LCL 0 | PASS |
| Planted p-chart shift 19/20 | beyond frozen baseline UCL | PASS |
| I-MR [10,12,11,13,14] | I limits 8.0106382979, 15.9893617021; MR UCL 4.9005 | PASS |
| Recovery [5,10,15], target 10 | mean 10; sample SD 5; compliance 2/3; Ppu 0 | PASS |
| Hourly groups [0,2], [2,4] | center 2; pooled within SD sqrt(2); limits -1,5 | PASS |
| Constant p/I-MR/hourly baseline | clear zero-variation error | PASS |
| Empty/constant capability | undefined Ppu with explanatory message | PASS |
| Exponential rate .1/hour at 5 hours | .6065306597 | PASS |
| Independent components .9,.8 | series .72; parallel .98 | PASS |
| FMEA 8×9×3 | RPN 216 | PASS |
| Episode/gap fixtures | left/right censoring preserved; unknown exposure reported | PASS |
| Inventory reason switch | continuous unusability remains one episode | PASS |
| Forecast and maintenance replay | future readings and ticket details excluded | PASS |
| Invalid telemetry | missing, duplicate, impossible counts and unsupported states rejected | PASS |

No finite MTBF is asserted when no failures were observed. Overall sample SD is
used only for descriptive Ppu; it is not labeled within-process Cpk. Statistical
assumptions and the limitations of autocorrelated telemetry appear in the tool
and demo walkthrough. The scenario results are independently reproducible with
`python demo/verify.py` and do not replace these known-answer unit checks.
