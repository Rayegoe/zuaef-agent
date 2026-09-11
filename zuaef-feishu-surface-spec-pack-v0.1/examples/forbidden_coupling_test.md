# Example Architecture Test: No Quant Logic in Feishu Surface

The actual test should use repository paths discovered on OPi5.

Concept:

```python
FORBIDDEN = [
    "BUY",
    "WATCH",
    "HOLD",
    "PIT",
    "T+1",
    "T+3",
    "T+5",
    "ticker",
    "position",
    "market_data",
]

def test_feishu_surface_has_no_quant_business_coupling():
    source = read_all_feishu_runtime_source_excluding_tests_and_docs()
    for token in FORBIDDEN:
        assert token not in source
```

Do not use this as a substitute for the behavioral Quant-removal test.
