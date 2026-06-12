"""
Generate a PNG architecture diagram for the EventBridge + SQS Financial Fan-Out pattern.
Requires: pip install diagrams  |  Graphviz installed on the system PATH.

Layout: left-to-right, clusters rendered horizontally.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import APIGateway
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import Eventbridge, SQS
from diagrams.onprem.client import User

OUTPUT_FILE = "fanout_architecture"

graph_attr = {
    "fontsize": "13",
    "bgcolor": "white",
    "pad": "0.8",
    "splines": "ortho",
    "nodesep": "0.6",
    "ranksep": "1.2",
}

with Diagram(
    "EventBridge + SQS Financial Fan-Out",
    filename=OUTPUT_FILE,
    outformat="png",
    show=False,
    direction="LR",          # ← left-to-right layout
    graph_attr=graph_attr,
):
    client = User("Client")

    # ── Entry point ──────────────────────────────────────────────────────────
    with Cluster("finance-orchestration"):
        apigw        = APIGateway("API Gateway")
        orchestrator = Lambda("process_transaction")
        apigw >> orchestrator   # horizontal inside cluster

    # ── Event bus ────────────────────────────────────────────────────────────
    with Cluster("Event Bus"):
        eb = Eventbridge("finance-events\n(EventBridge)")

    # ── Consumer domains ─────────────────────────────────────────────────────
    with Cluster("finance-compliance"):
        compliance_sqs = SQS("Compliance SQS")
        compliance_fn  = Lambda("compliance_check")
        compliance_dlq = SQS("DLQ")
        compliance_sqs >> compliance_fn >> Edge(label="on failure") >> compliance_dlq

    with Cluster("finance-fraud"):
        fraud_sqs = SQS("Fraud SQS")
        fraud_fn  = Lambda("fraud_detection")
        fraud_dlq = SQS("DLQ")
        fraud_sqs >> fraud_fn >> Edge(label="on failure") >> fraud_dlq

    with Cluster("finance-ledger"):
        ledger_sqs = SQS("Ledger SQS")
        ledger_fn  = Lambda("ledger_update")
        ledger_dlq = SQS("DLQ")
        ledger_sqs >> ledger_fn >> Edge(label="on failure") >> ledger_dlq

    # ── Flow ─────────────────────────────────────────────────────────────────
    client >> apigw                                    # client → API GW
    orchestrator >> Edge(label="put_event") >> eb      # orchestrator → EventBridge

    # fan-out: EventBridge → each SQS queue
    eb >> compliance_sqs
    eb >> fraud_sqs
    eb >> ledger_sqs

print(f"Diagram saved as {OUTPUT_FILE}.png")
