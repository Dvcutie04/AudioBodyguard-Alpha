import math,statistics

def rmse(a,b):
    assert len(a)==len(b) and a
    return math.sqrt(statistics.fmean((x-y)**2 for x,y in zip(a,b)))

def mae(a,b):
    assert len(a)==len(b) and a
    return statistics.fmean(abs(x-y) for x,y in zip(a,b))
