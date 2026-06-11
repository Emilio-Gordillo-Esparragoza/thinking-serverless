import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
from domains.fanoutEx.finance_compliance.src.compliance_check.lambda_function import (
    _parse_sqs_event,
    _run_aml_check,
    lambda_handler,
)


class TestParseSqsEvent(unittest.TestCase):
    def test_parses_valid_records(self):
        event = {
            "Records": [
                {
                    "body": json.dumps(
                        {
                            "detail": json.dumps(
                                {"transactionId": "tx-1", "amount": 50000}
                            )
                        }
                    )
                }
            ]
        }
        result = _parse_sqs_event(event)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["transactionId"], "tx-1")

    def test_skips_invalid_records(self):
        event = {"Records": [{"body": "not-json"}]}
        result = _parse_sqs_event(event)
        self.assertEqual(len(result), 0)

    def test_empty_event(self):
        self.assertEqual(_parse_sqs_event({}), [])


class TestRunAmlCheck(unittest.TestCase):
    def test_below_threshold(self):
        result = _run_aml_check({"transactionId": "tx-1", "amount": 50000})
        self.assertFalse(result["flagged"])
        self.assertEqual(result["reason"], "Passed AML check")

    def test_above_threshold(self):
        result = _run_aml_check({"transactionId": "tx-2", "amount": 2_000_000})
        self.assertTrue(result["flagged"])
        self.assertIn("AML threshold", result["reason"])


class TestLambdaHandler(unittest.TestCase):
    def test_handles_event_with_records(self):
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

    def test_handles_empty_event(self):
        lambda_handler({"Records": []}, None)
        lambda_handler({}, None)


if __name__ == "__main__":
    unittest.main()
