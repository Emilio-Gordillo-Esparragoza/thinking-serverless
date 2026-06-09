import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
from domains.finance_ledger.src.ledger_update.lambda_function import (
    _build_ledger_entries,
    _parse_sqs_event,
    lambda_handler,
)


class TestParseSqsEvent(unittest.TestCase):
    def test_parses_valid_records(self):
        event = {
            "Records": [
                {
                    "body": json.dumps(
                        {"detail": json.dumps({"transactionId": "tx-1", "amount": 500})}
                    )
                }
            ]
        }
        result = _parse_sqs_event(event)
        self.assertEqual(len(result), 1)


class TestBuildLedgerEntries(unittest.TestCase):
    def test_debit_credit_structure(self):
        tx = {
            "transactionId": "tx-1",
            "accountId": "acc-1",
            "amount": 500,
            "type": "deposit",
        }
        debit, credit = _build_ledger_entries(tx)
        self.assertEqual(debit["direction"], "debit")
        self.assertEqual(credit["direction"], "credit")
        self.assertEqual(debit["amount"], 500)
        self.assertEqual(credit["amount"], 500)

    def test_entry_ids(self):
        tx = {"transactionId": "tx-1"}
        debit, credit = _build_ledger_entries(tx)
        self.assertTrue(debit["entryId"].endswith("-debit"))
        self.assertTrue(credit["entryId"].endswith("-credit"))


class TestLambdaHandler(unittest.TestCase):
    def test_handles_event(self):
        event = {
            "Records": [
                {
                    "body": json.dumps(
                        {"detail": json.dumps({"transactionId": "tx-1", "amount": 500})}
                    )
                }
            ]
        }
        lambda_handler(event, None)

    def test_empty_event(self):
        lambda_handler({}, None)


if __name__ == "__main__":
    unittest.main()
