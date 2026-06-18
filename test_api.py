import urllib.request
import json
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

req = urllib.request.Request('https://drootle-byk-production.up.railway.app/api/auth/login', method='POST')
req.add_header('Content-Type', 'application/json')
data = json.dumps({"username": "drootle admin", "password": "admin_secret_456"}).encode('utf-8')
resp = urllib.request.urlopen(req, data=data)
token = json.loads(resp.read())['access_token']

req2 = urllib.request.Request('https://drootle-byk-production.up.railway.app/api/dashboard/profile')
req2.add_header('Authorization', 'Bearer ' + token)
try:
    print(urllib.request.urlopen(req2).read())
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(e.read())
