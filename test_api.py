import requests

try:
    r = requests.get('http://localhost:8000/api/predictions', params={'date': '2026-01-13'}, timeout=120)
    print(f"Status Code: {r.status_code}")
    print(f"Response Text (first 2000 chars):")
    print(r.text[:2000])
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
