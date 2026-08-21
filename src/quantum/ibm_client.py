import urllib.request
import urllib.parse
import json

API_KEY = "LZw0PaWBKFxSpE-4zZSE1M0JJJHwremUaEvydKdJYMYA"
IAM_URL = "https://iam.cloud.ibm.com/identity/token"

def get_access_token():
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = urllib.parse.urlencode({
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": API_KEY
    }).encode("utf-8")
    req = urllib.request.Request(IAM_URL, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode("utf-8"))
        return res.get("access_token")

if __name__ == "__main__":
    token = get_access_token()
    print(f"[SUCCESS] IBM Quantum REST Client initialized.")
    print(f"Token Snippet: {token[:20]}...")
