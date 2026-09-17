from app.services.release_service import release_gate_report

def test_release_gate_report_empty_project():
    class P:
        id=1; requirements=[]; development_tasks=[]; maintenance_items=[]; documentation_set=None; database_design=None; prototype_design=None; git_repository=None
    class DB:
        def query(self,*a):
            class Q:
                def filter(self,*a): return self
                def all(self): return []
            return Q()
    r=release_gate_report(DB(),P())
    assert 'readiness_score' in r
    assert 'gates' in r
    assert r['requirements']==0
