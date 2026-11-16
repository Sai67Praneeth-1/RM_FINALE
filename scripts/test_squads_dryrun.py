import sys, os
sys.path.insert(0, os.path.abspath("."))
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)

squads_to_test = [
    ('consumer_sentiment', 'What are the customers mostly complaining of?'),
    ('security_forensics', 'Check system access logs for unauthorized root escalation'),
    ('cross_squad', 'Investigate customer complaint TKT-1004 and correlate with system access logs for root breach'),
    ('adversarial_critic', 'Demonstrate adversarial critic debate between analyst and critic'),
    ('rapid_consensus', 'Run rapid 3-agent consensus check on records')
]

for sq_id, prompt in squads_to_test:
    print(f"\n=======================================================")
    print(f"=== TESTING SQUAD: {sq_id} ===")
    print(f"=======================================================")
    res = client.post('/api/chat', json={'message': prompt, 'squad_type': sq_id})
    if res.status_code != 200:
        print(f"FAILED {sq_id}: status {res.status_code}")
        continue
    data = res.json()
    wf_id = data.get('workflow_id')
    nodes = data.get('interaction_graph', {}).get('nodes', [])
    edges = data.get('interaction_graph', {}).get('edges', [])
    node_ids = [n.get('id') for n in nodes]
    print(f"Workflow ID: {wf_id}")
    print(f"Nodes ({len(nodes)}): {node_ids}")
    print(f"Edges ({len(edges)}):")
    for e in edges:
        lbl = str(e.get('label', ''))[:40]
        print(f"  {e.get('source')} -> {e.get('target')}: [{e.get('interaction_type')}] {lbl}")
    resp_preview = str(data.get('response', ''))[:100].replace('\n', ' ')
    print(f"Response preview: {resp_preview}...")

print("\n>>> ALL SQUAD DRY RUNS COMPLETED SUCCESSFULLY! <<<")
