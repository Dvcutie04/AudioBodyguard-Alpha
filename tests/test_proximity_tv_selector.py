import pytest
from src.edge.proximity_tv_selector import ProximityEvidence, select_nearest_tv

@pytest.mark.parametrize("rows,current,expected", [
    ([("tv_a",2.0,99.0,True),("tv_b",4.0,99.0,True)],None,"tv_a"),
    ([("tv_a",5.0,99.0,True)],None,"tv_a"),
    ([("tv_a",5.1,99.0,True)],None,None),
    ([("tv_a",1.0,90.0,True)],None,None),
    ([("tv_a",1.0,101.0,True)],None,None),
    ([("tv_a",1.0,99.0,False),("tv_b",3.0,99.0,True)],None,"tv_b"),
    ([("tv_a",2.0,99.0,True),("tv_b",2.2,99.0,True)],None,None),
    ([("tv_a",2.2,99.0,True),("tv_b",2.0,99.0,True)],"tv_a","tv_a"),
    ([("tv_a",4.0,99.0,True),("tv_b",2.0,99.0,True)],"tv_a","tv_b"),
    ([("tv_a",1.0,90.0,True),("tv_b",3.0,99.0,True)],"tv_a","tv_b"),
    ([("tv_a",float("nan"),99.0,True)],None,None),
    ([],None,None),
])
def test_proximity_selection(rows,current,expected):
    evidence=[ProximityEvidence(*row) for row in rows]
    result=select_nearest_tv(evidence,now=100.0,radius_m=5.0,max_age_s=2.0,ambiguity_m=0.5,switch_margin_m=1.0,current_device_id=current)
    assert result==expected
