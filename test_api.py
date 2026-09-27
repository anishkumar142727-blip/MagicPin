import requests
import json
import time

BASE_URL = 'http://localhost:8080'

print("1. Pushing Category Context...")
r1 = requests.post(f"{BASE_URL}/v1/context", json={
  "scope": "category",
  "context_id": "salons",
  "version": 1,
  "payload": {
    "slug": "salons",
    "voice": { "tone": "warm and welcoming" },
    "offer_catalog": [{"title": "Haircut @ ₹199", "value": "199"}]
  },
  "delivered_at": "2026-09-27T10:00:00Z"
})
print(r1.json())

print("\n2. Pushing Merchant Context...")
r2 = requests.post(f"{BASE_URL}/v1/context", json={
  "scope": "merchant",
  "context_id": "m_001",
  "version": 1,
  "payload": {
    "identity": { "name": "The Great Salon", "locality": "South Delhi" },
    "category_slug": "salons",
    "performance": { "views": 2410, "ctr": 0.021 },
    "offers": [{"title": "Haircut @ ₹199", "status": "active"}]
  },
  "delivered_at": "2026-09-27T10:01:00Z"
})
print(r2.json())

print("\n3. Pushing Trigger Context...")
r3 = requests.post(f"{BASE_URL}/v1/context", json={
  "scope": "trigger",
  "context_id": "trg_001",
  "version": 1,
  "payload": {
    "merchant_id": "m_001",
    "kind": "research_digest",
    "details": "Searches for Haircuts in South Delhi have increased by 45% today."
  },
  "delivered_at": "2026-09-27T10:02:00Z"
})
print(r3.json())

print("\n4. Triggering Bot (Tick)...")
r4 = requests.post(f"{BASE_URL}/v1/tick", json={
  "now": "2026-09-27T10:30:00Z",
  "available_triggers": ["trg_001"]
})
print(json.dumps(r4.json(), indent=2))

print("\n5. Simulating Merchant Reply...")
r5 = requests.post(f"{BASE_URL}/v1/reply", json={
  "conversation_id": "conv_m_001_trg_001_12345",
  "merchant_id": "m_001",
  "customer_id": None,
  "from_role": "merchant",
  "message": "Yes, let us run that haircut campaign now. How do we start?",
  "received_at": "2026-09-27T10:45:00Z",
  "turn_number": 2
})
print(json.dumps(r5.json(), indent=2))
