"""Rebuild ERC-20 holder balances from a set of Transfer logs.

Given the decoded logs of a `Transfer(address indexed from, address indexed to,
uint256 value)` event, this replays them in order and prints the resulting
balances. Useful for checking what a token's holder distribution looked like at
a point in time without an archive node.

Any log whose topic0 is not the Transfer signature is ignored rather than
guessed at, and a transfer that would take an account negative is reported as an
error instead of being silently clamped, because a negative balance means the
input was wrong.
"""

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO_TOPIC = "0x" + "00" * 32


def topic_to_address(topic):
    """The low 20 bytes of a 32-byte topic, 0x-prefixed lowercase."""
    t = topic[2:] if topic[:2].lower() == "0x" else topic
    if len(t) != 64:
        raise ValueError("topic must be 32 bytes, got %d" % (len(t) // 2))
    return "0x" + t[24:].lower()


def log_to_transfer(log):
    """A log dict to (from, to, value), or None if it is not a Transfer."""
    topics = log.get("topics") or []
    if len(topics) < 3:
        return None
    if topics[0].lower() != TRANSFER_TOPIC:
        return None
    data = log.get("data") or "0x"
    h = data[2:] if data[:2].lower() == "0x" else data
    if len(h) == 0:
        value = 0
    elif len(h) == 64:
        value = int(h, 16)
    else:
        raise ValueError("Transfer data must be a single 32-byte word, got %d bytes" % (len(h) // 2))
    return (topic_to_address(topics[1]), topic_to_address(topics[2]), value)


def snapshot(logs):
    """Replay logs in order and return {address: balance}. Mints come from the
    zero address, burns go to it, and neither is a holder."""
    balances = {}
    for i, log in enumerate(logs):
        t = log_to_transfer(log)
        if t is None:
            continue
        src, dst, value = t
        if src != ZERO_TOPIC_ADDR:
            if balances.get(src, 0) < value:
                raise ValueError(
                    "log %d would take %s negative: has %d, sending %d"
                    % (i, src, balances.get(src, 0), value)
                )
            balances[src] = balances[src] - value
        if dst != ZERO_TOPIC_ADDR:
            balances[dst] = balances.get(dst, 0) + value
    return {k: v for k, v in balances.items() if v}


ZERO_TOPIC_ADDR = "0x" + "00" * 20


def summarise(balances):
    """(total_supply, holder_count, top10_share) for a balances dict."""
    total = sum(balances.values())
    top = sorted(balances.values(), reverse=True)[:10]
    share = (sum(top) / total) if total else 0.0
    return total, len(balances), share


def main(argv):
    import json
    import sys

    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    with open(argv[0]) as fh:
        payload = json.load(fh)
    logs = payload.get("logs", payload) if isinstance(payload, dict) else payload
    balances = snapshot(logs)
    total, holders, share = summarise(balances)
    print("holders: %d" % holders)
    print("total:   %d" % total)
    print("top10:   %.2f%%" % (share * 100))
    for addr, bal in sorted(balances.items(), key=lambda kv: -kv[1])[:20]:
        print("  %s  %d" % (addr, bal))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
