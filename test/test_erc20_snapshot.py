import unittest

from erc20_snapshot import (
    TRANSFER_TOPIC, log_to_transfer, snapshot, summarise, topic_to_address,
)


def w(addr_hex):
    """20-byte address hex to a 32-byte topic."""
    return "0x" + addr_hex.rjust(64, "0")


def log(src, dst, value, topic0=TRANSFER_TOPIC):
    return {
        "topics": [topic0, w(src), w(dst)],
        "data": "0x" + "%064x" % value,
    }


A = "11" * 20
B = "22" * 20
C = "33" * 20


class Topics(unittest.TestCase):
    def test_address_is_the_low_twenty_bytes(self):
        self.assertEqual(topic_to_address(w(A)), "0x" + A)

    def test_topic_length_is_checked(self):
        with self.assertRaises(ValueError):
            topic_to_address("0x1234")


class Transfers(unittest.TestCase):
    def test_mint_is_recognised(self):
        t = log_to_transfer(log("00" * 20, A, 100))
        self.assertEqual(t, ("0x" + "00" * 20, "0x" + A, 100))

    def test_non_transfer_log_is_ignored(self):
        self.assertIsNone(log_to_transfer(log(A, B, 1, topic0="0x" + "ab" * 32)))

    def test_missing_topics_is_ignored(self):
        self.assertIsNone(log_to_transfer({"topics": [TRANSFER_TOPIC]}))

    def test_wrong_data_width_is_an_error(self):
        bad = log(A, B, 1)
        bad["data"] = "0x" + "00" * 64
        with self.assertRaises(ValueError):
            log_to_transfer(bad)


class Snapshot(unittest.TestCase):
    def test_mint_then_transfer(self):
        balances = snapshot([log("00" * 20, A, 1000), log(A, B, 400)])
        self.assertEqual(balances["0x" + A], 600)
        self.assertEqual(balances["0x" + B], 400)
        self.assertNotIn("0x" + "00" * 20, balances)

    def test_burn_removes_from_supply(self):
        balances = snapshot([log("00" * 20, A, 100), log(A, "00" * 20, 30)])
        self.assertEqual(balances["0x" + A], 70)

    def test_zero_balance_holder_is_dropped(self):
        balances = snapshot([log("00" * 20, A, 100), log(A, B, 100)])
        self.assertNotIn("0x" + A, balances)

    def test_overspend_is_an_error_not_a_clamp(self):
        with self.assertRaises(ValueError) as cm:
            snapshot([log("00" * 20, A, 10), log(A, B, 11)])
        self.assertIn("negative", str(cm.exception))

    def test_order_matters(self):
        with self.assertRaises(ValueError):
            snapshot([log(A, B, 1), log("00" * 20, A, 5)])

    def test_non_transfer_logs_are_skipped_not_counted(self):
        balances = snapshot([
            {"topics": ["0x" + "ab" * 32], "data": "0x"},
            log("00" * 20, A, 5),
        ])
        self.assertEqual(balances, {"0x" + A: 5})

    def test_summary_shape(self):
        balances = snapshot([log("00" * 20, A, 100), log("00" * 20, B, 300)])
        total, holders, share = summarise(balances)
        self.assertEqual(total, 400)
        self.assertEqual(holders, 2)
        self.assertAlmostEqual(share, 1.0)


if __name__ == "__main__":
    unittest.main()
