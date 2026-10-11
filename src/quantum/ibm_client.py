import os
import urllib.request
import urllib.parse
import json

IAM_URL = "https://iam.cloud.ibm.com/identity/token"

def get_access_token():
    api_key = os.environ.get("IBM_CLOUD_API_KEY", "").strip()
    if not api_key:
        raise ValueError("IBM_CLOUD_API_KEY is required; no network request was made")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = urllib.parse.urlencode({
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key
    }).encode("utf-8")
    req = urllib.request.Request(IAM_URL, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=5.0) as response:
        res = json.loads(response.read().decode("utf-8"))
        return res.get("access_token")

if __name__ == "__main__":
    token = get_access_token()
    print(f"[SUCCESS] IBM Quantum REST Client initialized.")
