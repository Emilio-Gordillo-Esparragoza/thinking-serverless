"""
Tests that IAM policies (shared JSON files and SAM templates) do not use
overbroad Resource: "*" for any statement.

Exceptions:
- logs:* actions: CloudWatch Logs requires a log-group ARN, not "*"
- events:PutEvents: must target the specific finance-events bus ARN, not "*"
- sqs:Receive/Delete actions: must target specific queue ARNs, not "*"
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RESOURCE_STAR = re.compile(r'"Resource"\s*:\s*"\*"')
# In YAML the bare value looks like:  Resource: "*"
YAML_RESOURCE_STAR = re.compile(r"Resource:\s+[\"']?\*[\"']?")


def _find_resource_star_in_json(path: Path) -> list[str]:
    """Return list of Sid/Action combos that still use Resource: '*'."""
    data = json.loads(path.read_text(encoding="utf-8"))
    violations = []
    for stmt in data.get("Statement", []):
        resource = stmt.get("Resource", "")
        if isinstance(resource, str) and resource == "*":
            sid = stmt.get("Sid", "<no Sid>")
            actions = stmt.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            violations.append(f"{path.name} – Sid={sid} Actions={actions}")
    return violations


def _find_resource_star_in_yaml(path: Path) -> list[str]:
    """
    Scan a SAM YAML template for raw 'Resource: "*"' lines.
    We rely on the text representation because PyYAML would need to be added
    as a dependency; a regex scan is sufficient for this purpose.
    """
    violations = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, start=1):
        if YAML_RESOURCE_STAR.search(line):
            # Allow queue/bus ARN references that use CloudFormation functions
            # e.g. Resource: !GetAtt ... or Resource: !Sub "arn:..."
            if "!GetAtt" in line or "!Sub" in line or "!Ref" in line:
                continue
            violations.append(f"{path} line {i}: {line.strip()}")
    return violations


# ---------------------------------------------------------------------------
# Test: shared JSON policy files
# ---------------------------------------------------------------------------

SHARED_POLICIES_DIR = ROOT / "shared" / "iam-policies"


def test_shared_iam_policies_no_wildcard_resource():
    """No shared IAM policy JSON file should grant Resource: '*'."""
    violations = []
    for policy_file in SHARED_POLICIES_DIR.glob("*.json"):
        violations.extend(_find_resource_star_in_json(policy_file))

    assert not violations, (
        "Found Resource: '*' in shared IAM policy files:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


# ---------------------------------------------------------------------------
# Test: SAM template inline policies
# ---------------------------------------------------------------------------

SAM_TEMPLATES = list(
    (ROOT / "domains").glob("**/infrastructure/sam/template.yaml")
)


def test_sam_templates_no_wildcard_resource():
    """No SAM template inline policy should grant Resource: '*'."""
    assert SAM_TEMPLATES, "No SAM templates found – check glob path"

    violations = []
    for template in SAM_TEMPLATES:
        violations.extend(_find_resource_star_in_yaml(template))

    assert not violations, (
        "Found Resource: '*' in SAM template inline policies:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


# ---------------------------------------------------------------------------
# Test: specific resource scoping — shared JSON policies
# ---------------------------------------------------------------------------

def test_lambda_execution_policy_scoped_to_lambda_log_groups():
    """lambda_execution_policy must target /aws/lambda/* log groups only."""
    policy = json.loads(
        (SHARED_POLICIES_DIR / "lambda_execution_policy.json").read_text(encoding="utf-8")
    )
    for stmt in policy["Statement"]:
        resource = stmt.get("Resource", "")
        assert resource != "*", "lambda_execution_policy must not use Resource: '*'"
        assert "/aws/lambda/" in resource, (
            f"lambda_execution_policy CloudWatch Logs resource should be scoped "
            f"to /aws/lambda/*, got: {resource}"
        )


def test_sqs_consumer_policy_scoped_to_domain_queues():
    """sqs_consumer_policy must target domain queue ARN patterns, not '*'."""
    policy = json.loads(
        (SHARED_POLICIES_DIR / "sqs_consumer_policy.json").read_text(encoding="utf-8")
    )
    for stmt in policy["Statement"]:
        resource = stmt.get("Resource", "")
        assert resource != "*", "sqs_consumer_policy must not use Resource: '*'"
        assert resource.startswith("arn:aws:sqs:"), (
            f"sqs_consumer_policy resource must be an SQS ARN pattern, got: {resource}"
        )


def test_eventbridge_put_policy_scoped_to_finance_bus():
    """eventbridge_put_policy must target the finance-events bus only."""
    policy = json.loads(
        (SHARED_POLICIES_DIR / "eventbridge_put_policy.json").read_text(encoding="utf-8")
    )
    for stmt in policy["Statement"]:
        resource = stmt.get("Resource", "")
        assert resource != "*", "eventbridge_put_policy must not use Resource: '*'"
        assert "finance-events" in resource, (
            f"eventbridge_put_policy resource must reference the finance-events bus, "
            f"got: {resource}"
        )
