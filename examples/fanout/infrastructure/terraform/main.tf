# Fan-out composition root.
# Includes only the EventBridge + SQS fan-out domains.
# The monolith (domains/finance_monolith) is intentionally omitted —
# deploy it separately for the synchronous comparison.

module "finance_compliance" {
  source      = "../../../../domains/finance_compliance/infrastructure/terraform"
  environment = var.environment
}

module "finance_fraud" {
  source      = "../../../../domains/finance_fraud/infrastructure/terraform"
  environment = var.environment
}

module "finance_ledger" {
  source      = "../../../../domains/finance_ledger/infrastructure/terraform"
  environment = var.environment
}

module "finance_orchestration" {
  source               = "../../../../domains/finance_orchestration/infrastructure/terraform"
  environment          = var.environment
  compliance_queue_arn = module.finance_compliance.compliance_queue_arn
  fraud_queue_arn      = module.finance_fraud.fraud_queue_arn
  ledger_queue_arn     = module.finance_ledger.ledger_queue_arn
}
