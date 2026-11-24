# quote usage

```
quote --weight <kg> --zone <A|B|remote> [--dangerous]
```

Prints `{"price": <number>}` and exits 0. For dangerous goods it prints `{"refused": "ops"}` and exits 3.
