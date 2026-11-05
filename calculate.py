#!/usr/bin/env python3
"""Recompute public-evidence scores and verify 5,000 recorded sensitivity runs."""
import csv
import json
from collections import defaultdict
from pathlib import Path

BASE=Path(__file__).resolve().parent

def rows(name):
    with (BASE/name).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def recompute():
    data=rows("SCORE_MATRIX.csv")
    rubric=rows("SCORING_MODEL.csv")
    if len(data)!=180 or len(rubric)!=18:
        raise AssertionError("Expected 10 candidates × 18 metrics")
    metrics={r["metric_id"]:float(r["max_points"]) for r in rubric}
    assert sum(metrics.values())==100
    assert len({r["candidate_id"] for r in data})==10
    assert len({(r["candidate_id"],r["metric_id"]) for r in data})==180
    points=defaultdict(float)
    groups=defaultdict(lambda:defaultdict(float))
    for row in data:
        cid=row["candidate_id"]
        metric=row["metric_id"]
        maxp=float(row["max_points"])
        fraction=float(row["confirmed_level"])
        pts=float(row["confirmed_points"])
        if abs(pts-maxp*fraction)>1e-6 or abs(maxp-metrics[metric])>1e-6:
            raise AssertionError((cid,metric,pts,maxp,fraction))
        points[cid]+=pts
        groups[cid][row["group_id"]]+=pts
    result=json.loads((BASE/"RESULTS.json").read_text(encoding="utf8"))
    for r in result["results"]:
        if abs(points[r["candidate_id"]]-r["confirmedPoints"])>1e-6:
            raise AssertionError((r["name"],points[r["candidate_id"]],r["confirmedPoints"]))
    weights=defaultdict(float)
    for r in rubric:
        weights[r["group_id"]]+=float(r["max_points"])
    assert set(weights)==set("ABCDEF") and abs(sum(weights.values())-100)<1e-6
    tests=rows("SENSITIVITY_5000.csv")
    if len(tests)!=5000:
        raise AssertionError("Expected 5000 weight vectors")
    leads=[]
    for test in tests:
        score={}
        for cid,gvals in groups.items():
            score[cid]=sum(gvals[g]*float(test["weight_"+g])/weights[g] for g in weights)
        order=sorted(score,key=lambda cid:(-score[cid],cid))
        if order[0]!="C01":
            raise AssertionError(("unexpected winner",test["iteration"],order[:2]))
        gap=score[order[0]]-score[order[1]]
        leads.append(gap)
        if abs(gap-float(test["winner_lead"]))>0.00002:
            raise AssertionError(("gap mismatch",test["iteration"],gap,test["winner_lead"]))
    summary={"participants":len(points),"metrics":len(metrics),"matrixRows":len(data),"sensitivityRuns":len(tests),
             "winners":dict(sorted(points.items(),key=lambda z:-z[1])),
             "minimumWeightVariationLead":round(min(leads),6)}
    return summary

if __name__=="__main__":
    print(json.dumps(recompute(),ensure_ascii=False,indent=2))
