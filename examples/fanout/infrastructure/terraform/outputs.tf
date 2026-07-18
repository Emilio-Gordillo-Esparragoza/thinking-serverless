output "event_bus_name" {
  value = module.finance_orchestration.event_bus_name
}

output "event_bus_arn" {
  value = module.finance_orchestration.event_bus_arn
}

output "compliance_queue_arn" {
  value = module.finance_compliance.compliance_queue_arn
}

output "fraud_queue_arn" {
  value = module.finance_fraud.fraud_queue_arn
}

output "ledger_queue_arn" {
  value = module.finance_ledger.ledger_queue_arn
}
