"""
Generate a PNG architecture diagram for the synchronous monolith pattern
(the "before" state — newOrder Lambda catch-all).
Requires: pip install diagrams  |  Graphviz on PATH.

Layout: left-to-right, clusters rendered horizontally.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import APIGateway
from diagrams.aws.compute import Lambda
from diagrams.aws.general import General
from diagrams.onprem.client import User

OUTPUT_FILE = "monolith_architecture"

graph_attr = {
    "fontsize": "13",
    "bgcolor": "white",
    "pad": "0.8",
    "splines": "ortho",
    "nodesep": "0.6",
    "ranksep": "1.2",
}

node_attr = {
    "fontsize": "12",
}

with Diagram(
    "Synchronous Monolith — newOrder Lambda (catch-all)",
    filename=OUTPUT_FILE,
    outformat="png",
    show=False,
    direction="LR",           # ← left-to-right layout
    graph_attr=graph_attr,
    node_attr=node_attr,
):
    client = User("Client")

    # ── Entry point ──────────────────────────────────────────────────────────
    with Cluster("finance-monolith"):
        apigw   = APIGateway("API Gateway")
        new_order = Lambda("newOrder\n(catch-all)")
        apigw >> new_order    # horizontal inside cluster

    # ── Sequential blocking steps ────────────────────────────────────────────
    with Cluster("1. Capture"):
        capture = Lambda("Capture\norder data")

    with Cluster("2. Compliance check  (amount > $10k)"):
        compliance  = Lambda("Compliance API\n(wait)")
        comp_reject = General("reject ✗")
        compliance >> Edge(label="if flagged") >> comp_reject

    with Cluster("3. Fraud check  (transfer)"):
        fraud      = Lambda("Fraud API\n(wait)")
        fraud_hold = General("hold ✗")
        fraud >> Edge(label="if suspicious") >> fraud_hold

    with Cluster("4. Ledger update"):
        ledger      = Lambda("Ledger API\n(wait)")
        ledger_fail = General("entire txn\nfails ✗")
        ledger >> Edge(label="if down") >> ledger_fail

    # ── Flow ─────────────────────────────────────────────────────────────────
    client >> apigw
    new_order >> capture

    # sequential, blocking chain (happy path)
    capture    >> Edge(label="sync call") >> compliance
    compliance >> Edge(label="ok")        >> fraud
    fraud      >> Edge(label="ok")        >> ledger

print(f"Diagram saved as {OUTPUT_FILE}.png")
