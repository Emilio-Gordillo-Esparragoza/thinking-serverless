import importlib.util
import json
import os
import unittest

_src_path = os.path.join(os.path.dirname(__file__), "lambda_function.py")
_spec = importlib.util.spec_from_file_location("new_order_lambda", _src_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load module from {_src_path}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

lambda_handler = _mod.lambda_handler
_run_compliance = _mod._run_compliance
_run_fraud_check = _mod._run_fraud_check
_update_ledger = _mod._update_ledger
_validate = _mod._validate


class TestValidate(unittest.TestCase):
    def test_valid(self):
        _validate(
            {"accountId": "a1", "amount": 500, "currency": "USD", "type": "deposit"}
        )

    def test_missing_fields(self):
        with self.assertRaises(ValueError):
            _validate({"amount": 100})

    def test_negative_amount(self):
        with self.assertRaises(ValueError):
            _validate(
                {"accountId": "a1", "amount": -1, "currency": "USD", "type": "payment"}
            )

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            _validate(
                {"accountId": "a1", "amount": 100, "currency": "USD", "type": "unknown"}
            )


class TestRunCompliance(unittest.TestCase):
    def test_below_threshold(self):
        result = _run_compliance("tx-1", 500)
        self.assertFalse(result["flagged"])

    def test_above_threshold(self):
        result = _run_compliance("tx-1", 2_000_000)
        self.assertTrue(result["flagged"])


class TestRunFraudCheck(unittest.TestCase):
    def test_small_amount(self):
        result = _run_fraud_check("tx-1", 500, "deposit")
        self.assertFalse(result["suspicious"])
        self.assertEqual(result["score"], 0.0)

    def test_large_transfer(self):
        result = _run_fraud_check("tx-1", 6_000_000, "transfer")
        self.assertGreater(result["score"], 0.3)

    def test_score_capped(self):
        result = _run_fraud_check("tx-1", 50_000_000, "transfer")
        self.assertLessEqual(result["score"], 1.0)


class TestUpdateLedger(unittest.TestCase):
    def test_returns_debit_and_credit(self):
        result = _update_ledger("tx-1", "a1", 500, "deposit")
        self.assertIn("debit", result)
        self.assertIn("credit", result)
        self.assertIn("entryId", result["debit"])
        self.assertIn("entryId", result["credit"])
        self.assertEqual(result["debit"]["amount"], 500)
        self.assertEqual(result["credit"]["amount"], 500)

class TestLambdaHandler(unittest.TestCase):
    def test_successful_transaction(self):
        event = {
            "body": json.dumps(
                {"accountId": "a1", "amount": 500, "currency": "USD", "type": "deposit"}
            )
        }
        resp = lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertIn("transactionId", body)

    def test_compliance_blocks_large_amount(self):
        event = {
            "body": json.dumps(
                {
                    "accountId": "a1",
                    "amount": 2_000_000,
                    "currency": "USD",
                    "type": "deposit",
                }
            )
        }
        resp = lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 403)

    def test_validation_error(self):
        event = {"body": json.dumps({"amount": -5})}
        resp = lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 400)

    def test_missing_body(self):
        resp = lambda_handler({}, None)
        self.assertEqual(resp["statusCode"], 400)
        body = json.loads(resp["body"])
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()