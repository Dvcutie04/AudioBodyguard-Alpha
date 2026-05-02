import hashlib,time,json
S="OMEGA26"
def v(p,n):
 d=p["d"]
 k=hashlib.sha256((json.dumps(d,sort_keys=True)+S).encode()).hexdigest()
 ms=(n-d["t"])*1000
 if p["s"]!=k or ms>1500 or d["f"]-(ms/1000)*0.05<0.8: return 0
 return 1
