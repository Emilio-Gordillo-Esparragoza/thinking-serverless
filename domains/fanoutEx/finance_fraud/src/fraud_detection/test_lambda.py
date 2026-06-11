import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
from domains.fanoutEx.finance_fraud.src.fraud_detection.lambda_function import (
    _calculate_fraud_score,
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
        self.assertEqual(result[0]["transactionId"], "tx-1")


class TestCalculateFraudScore(unittest.TestCase):
    def test_small_transaction(self):
        score = _calculate_fraud_score({"amount": 500, "type": "deposit"})
        self.assertEqual(score, 0.0)

    def test_large_transfer(self):
        score = _calculate_fraud_score({"amount": 6_000_000, "type": "transfer"})
        self.assertGreaterEqual(score, 0.5)

    def test_large_deposit(self):
        score = _calculate_fraud_score({"amount": 15_000_000, "type": "deposit"})
        # amount > 10M => +0.4, capped at 1.0
        self.assertEqual(score, 0.4)

    def test_score_capped(self):
        score = _calculate_fraud_score({"amount": 50_000_000, "type": "transfer"})
        self.assertLessEqual(score, 1.0)


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
