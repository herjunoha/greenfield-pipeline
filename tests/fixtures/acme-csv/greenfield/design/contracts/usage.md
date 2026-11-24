# csvsum usage

```
csvsum summarize <input.csv> --out <summary.json>
csvsum --version
```

Exit codes: 0 success, 2 the input file does not exist or cannot be read.
Output: a JSON object `{"rows": <int>, "sums": {<column>: <number>}}`, keys sorted, written to `--out`.
