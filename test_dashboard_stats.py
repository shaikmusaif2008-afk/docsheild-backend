import urllib.request
import json

print("="*70)
print("  DOCSHIELD AI — DASHBOARD REAL-TIME STATISTICS TEST")
print("="*70)

# 1. Fetch initial dashboard stats
req = urllib.request.Request('http://localhost:8000/api/dashboard/stats')
res = urllib.request.urlopen(req)
stats_before = json.loads(res.read().decode('utf-8'))

print("\n[INITIAL DASHBOARD STATS]")
print(f"  Today's Screenings:   {stats_before['today']['total']} ({stats_before['today']['trend']})")
print(f"  Total Overall:        {stats_before['overall']['total']}")
print(f"  Likely Genuine:       {stats_before['overall']['genuine']} ({stats_before['riskDistribution']['genuine']}%)")
print(f"  Medium Risk:          {stats_before['overall']['medium']} ({stats_before['riskDistribution']['medium']}%)")
print(f"  High Risk:            {stats_before['overall']['high']} ({stats_before['riskDistribution']['high']}%)")
print(f"  Manual Review:        {stats_before['overall']['manualReview']} ({stats_before['riskDistribution']['manualReview']}%)")

# Verify overall sum consistency
total_b = stats_before['overall']['total']
sum_b = stats_before['overall']['genuine'] + stats_before['overall']['medium'] + stats_before['overall']['high'] + stats_before['overall']['manualReview']
assert total_b == sum_b, f"Total mismatch: {total_b} != {sum_b}"
print("[PASS] Mutually exclusive category consistency verified: Total = Genuine + Medium + High + Manual Review")

# 2. Add a new Genuine Screening Case
new_case_1 = {
    "case_id": f"TEST-CASE-GEN-{int(time.time() if 'time' in globals() else 1001)}",
    "domain": "01 — AIRLINES & GATE AGENTS",
    "doc_type": "Passport",
    "person_name": "Test Traveler Genuine",
    "doc_number": "P89241029",
    "overall_risk_score": 10,
    "risk_level": "LOW",
    "status": "LIKELY GENUINE"
}
import time
new_case_1["case_id"] = f"TEST-CASE-GEN-{int(time.time())}"

post_data = json.dumps(new_case_1).encode('utf-8')
post_req = urllib.request.Request('http://localhost:8000/api/screening/save-completed', data=post_data, headers={'Content-Type': 'application/json'})
urllib.request.urlopen(post_req)

# 3. Add a new High Risk Case
new_case_2 = {
    "case_id": f"TEST-CASE-HIGH-{int(time.time())}",
    "domain": "02 — IMMIGRATION & BORDER CONTROL",
    "doc_type": "Visa",
    "person_name": "Test Traveler Suspicious",
    "doc_number": "V9912847",
    "overall_risk_score": 85,
    "risk_level": "HIGH",
    "status": "LIKELY FAKE / SUSPICIOUS"
}
post_data_2 = json.dumps(new_case_2).encode('utf-8')
post_req_2 = urllib.request.Request('http://localhost:8000/api/screening/save-completed', data=post_data_2, headers={'Content-Type': 'application/json'})
urllib.request.urlopen(post_req_2)

# 4. Fetch updated dashboard stats
res_after = urllib.request.urlopen(req)
stats_after = json.loads(res_after.read().decode('utf-8'))

print("\n[UPDATED DASHBOARD STATS AFTER 2 NEW SCREENINGS]")
print(f"  Today's Screenings:   {stats_after['today']['total']} (Incremented by {stats_after['today']['total'] - stats_before['today']['total']})")
print(f"  Total Overall:        {stats_after['overall']['total']} (Incremented by {stats_after['overall']['total'] - stats_before['overall']['total']})")
print(f"  Likely Genuine:       {stats_after['overall']['genuine']} (Incremented by {stats_after['overall']['genuine'] - stats_before['overall']['genuine']})")
print(f"  High Risk:            {stats_after['overall']['high']} (Incremented by {stats_after['overall']['high'] - stats_before['overall']['high']})")

assert stats_after['overall']['total'] == stats_before['overall']['total'] + 2
assert stats_after['today']['total'] == stats_before['today']['total'] + 2
assert stats_after['overall']['genuine'] == stats_before['overall']['genuine'] + 1
assert stats_after['overall']['high'] == stats_before['overall']['high'] + 1

# 5. Fetch Recent Screenings
recent_req = urllib.request.Request('http://localhost:8000/api/dashboard/recent?limit=5')
recent_res = urllib.request.urlopen(recent_req)
recent_screenings = json.loads(recent_res.read().decode('utf-8'))

print(f"\n[RECENT SCREENINGS ({len(recent_screenings)} latest records)]")
for r in recent_screenings[:3]:
    print(f"  • Case: {r['case_id']} | Domain: {r['domain']} | {r['doc_type']} | Score: {r['overall_risk_score']}/100 | Status: {r['status']}")

assert recent_screenings[0]['case_id'] == new_case_2['case_id']

# 6. Fetch Domain Stats
domain_req = urllib.request.Request('http://localhost:8000/api/dashboard/domain-stats')
domain_res = urllib.request.urlopen(domain_req)
domain_stats = json.loads(domain_res.read().decode('utf-8'))
print(f"\n[SCREENINGS BY DOMAIN]")
for d in domain_stats:
    print(f"  • {d['domain']}: {d['count']} cases")

print("\n" + "="*70)
print("  DASHBOARD STATISTICS & REAL-TIME REFRESH VERIFIED 100%!")
print("="*70)
