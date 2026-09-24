# erc20-snapshot

Rebuild ERC-20 holder balances by replaying `Transfer` logs in order.

Answers "who held this token, and how concentrated was it" from logs you already
have, without an archive node and without trusting a third-party explorer.

## Usage

```bash
python3 -m erc20_snapshot logs.json
```

```
holders: 1284
total:   1000000000000000000000000
top10:   62.41%
  0x1111111111111111111111111111111111111111  410000000000000000000000
  ...
```

Input is either a JSON array of log objects or `{"logs": [...]}`.

```json
[{"topics": ["0xddf252ad...", "0x000...aaa", "0x000...bbb"],
  "data": "0x0000000000000000000000000000000000000000000000000de0b6b3a7640000"}]
```

## Rules it enforces

- **A transfer that would take an account negative is an error.** A negative
  balance means the log set is incomplete or out of order — most likely you
  started mid-history. Clamping to zero would hide that and produce a wrong
  holder list that looks plausible.
- **Mints and burns are the zero address** and are never reported as holders;
  they adjust supply instead.
- **Only `topic0 == Transfer` is treated as a transfer.** Anything else is
  skipped rather than guessed at, so an approval log cannot corrupt balances.
- **`data` must be exactly one 32-byte word.** Non-standard tokens that pack the
  value elsewhere will raise rather than silently read zero.

## What it does not do

- **No RPC.** Feed it logs; it does not fetch them.
- **No decimals handling.** Raw base units only; formatting is a display concern.
- **No historical snapshots at a block.** It gives the final state of the log set
  you pass in. For "balance at block N", cut the log list at N.

## Development

```bash
python3 -m unittest discover -s test -t .
```

## License

MIT
