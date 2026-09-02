import urllib.request, json

def req(url, method='GET', body=None):
    data = json.dumps(body).encode() if body else None
    headers = {'Content-Type': 'application/json'} if data else {}
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=4) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, {}

base = 'http://localhost:5000'

code, data = req(base + '/api/workers')
print("GET /api/workers ->", code, "| count:", data.get('count'))

try:
    r = urllib.request.urlopen(base + '/login', timeout=4)
    print("GET /login ->", r.status, "OK")
except Exception as e:
    print("GET /login ->", e)

try:
    r2 = urllib.request.urlopen(base + '/', timeout=4)
    print("GET / ->", r2.status, r2.url)
except Exception as e:
    print("GET / -> redirected or error:", str(e)[:80])

code, data = req(base + '/api/register', 'POST', {'name':'Judge Client','phone':'8800000001','role':'client'})
print("POST /api/register ->", code, "|", data.get('message'))

code, data = req(base + '/api/login', 'POST', {'phone': '8800000001'})
print("POST /api/login    ->", code, "|", data.get('message'))

print()
print("=== SMOKE TEST COMPLETE ===")
