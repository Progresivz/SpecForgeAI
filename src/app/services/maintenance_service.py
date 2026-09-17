from collections import Counter
from app.models.project import Project
from app.models.maintenance import MaintenanceItem

SEVERITY_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}
PRIORITY_WEIGHT = {"urgent": 4, "high": 3, "medium": 2, "low": 1}

def _summary(items):
    c = Counter(i.item_type for i in items); s = Counter(i.status for i in items); sev = Counter(i.severity for i in items)
    return {"total":len(items),"open":s["open"],"in_progress":s["in_progress"],"resolved":s["resolved"],"critical":sev["critical"],"high":sev["high"],"bugs":c["bug"],"feature_requests":c["feature_request"],"technical_debt":c["technical_debt"],"security_items":c["security"],"dependency_updates":c["dependency_update"],"refactoring_items":c["refactoring"]}

def prioritize(items, limit=10):
    active=[i for i in items if i.status in {"open","in_progress","deferred"}]
    return sorted(active, key=lambda i:(SEVERITY_WEIGHT.get(i.severity,2), PRIORITY_WEIGHT.get(i.priority,2), i.due_date is None, i.due_date or 0), reverse=True)[:limit]

def recommendations(items):
    out=[]
    security=[i for i in items if i.status in {"open","in_progress"} and i.item_type=="security"]
    deps=[i for i in items if i.status in {"open","in_progress"} and i.item_type=="dependency_update"]
    debt=[i for i in items if i.status in {"open","in_progress"} and i.item_type in {"technical_debt","refactoring"}]
    bugs=[i for i in items if i.status in {"open","in_progress"} and i.item_type=="bug"]
    if security: out.append("Address open security items before lower-risk maintenance work, especially critical and high severity findings.")
    if deps: out.append("Review dependency updates in a controlled branch and run the full test suite before release.")
    if bugs: out.append("Group recurring bugs by affected area to identify systemic defects instead of fixing symptoms independently.")
    if len(debt)>=3: out.append("Create a dedicated technical-debt/refactoring milestone and tackle the highest-impact areas incrementally.")
    if not out: out.append("Keep maintenance items current and review priorities at each release or milestone checkpoint.")
    return out

def report(project: Project, items, limit=10):
    return {"project_id":project.id,"project_name":project.name,"summary":_summary(items),"priorities":prioritize(items,limit),"recommendations":recommendations(items)}

def refactoring_recommendations(items):
    areas={}
    for i in items:
        if i.status in {"open","in_progress"} and i.affected_area:
            areas.setdefault(i.affected_area, []).append(i)
    result=[]
    for area, group in sorted(areas.items(), key=lambda x:len(x[1]), reverse=True):
        if len(group)>=2 or any(i.item_type in {"technical_debt","refactoring"} for i in group):
            result.append({"priority":"high" if any(i.severity in {"critical","high"} for i in group) else "medium","area":area,"reason":f"{len(group)} active maintenance items reference this area.","recommendation":f"Review {area} for shared causes, duplicated logic, coupling, or missing tests before adding more changes.","expected_benefit":"Reduce recurring defects and make future changes safer and easier to maintain."})
    return result[:20]
