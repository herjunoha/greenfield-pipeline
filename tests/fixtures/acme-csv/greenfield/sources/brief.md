# acme-csv brief

Acme wants a small command-line tool that turns a CSV file into a summary. Synthetic: a fictional company. No network.

## Summary
`csvsum summarize <input.csv> --out <summary.json>` reads the file and writes a JSON summary: how many data rows it
has and the sum of each numeric column. Text columns are left out of the sums.

## Missing
If the input file does not exist the tool says so on stderr, exits with code 2 and writes no output file.

## Empty
A file with only a header row has zero rows and every numeric column sums to zero.

## Speed
A 5000-row file is summarised in under two seconds.
