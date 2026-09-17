from types import SimpleNamespace

# ---------------------------------------------------------
# Load all SQLAlchemy models before importing services that
# instantiate ORM models. This ensures every string-based
# relationship in Project is registered before mapper
# configuration occurs.
# ---------------------------------------------------------
from app.models.ai_artifact import AIArtifact
from app.models.copilot_conversation import CopilotConversation
from app.models.database_design import DatabaseDesign
from app.models.deadline import Deadline
from app.models.documentation import DocumentationSet
from app.models.git_repository import GitRepository
from app.models.knowledge import KnowledgeEntry
from app.models.maintenance import MaintenanceItem
from app.models.milestone import Milestone
from app.models.prototype import PrototypeDesign
from app.models.requirement import UseCase
from app.models.task import DevelopmentTask
from app.models.release import SDLCTtraceLink
from app.models.workflow import GeneratedTest, EngineeringFinding

from app.services.release_automation_service import (
    determine_release_decision,
    run_automation,
)
from app.services.release_service import release_gate_report


# ---------------------------------------------------------
# Fake query/session helpers
# ---------------------------------------------------------
class FakeQuery:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.rows)


class FakeDB:
    def __init__(self, trace_links=None, generated_tests=None):
        self.added = []
        self.committed = False
        self.trace_links = list(trace_links or [])
        self.generated_tests = list(generated_tests or [])

    def query(self, model):
        if model is SDLCTtraceLink:
            return FakeQuery(self.trace_links)

        if model is GeneratedTest:
            return FakeQuery(self.generated_tests)

        if model is EngineeringFinding:
            return FakeQuery([])

        return FakeQuery([])

    def add(self, obj):
        self.added.append(obj)

    def add_all(self, objects):
        self.added.extend(objects)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        return obj


def test_phase34_release_automation_end_to_end(monkeypatch):
    """
    Phase 34 service-level E2E:

        project
          -> requirement
          -> development task
          -> traceability evidence
          -> generated test evidence
          -> architecture evidence
          -> documentation evidence
          -> Git evidence
          -> readiness
          -> release automation
          -> AI review
          -> GO/NO-GO
          -> evidence
          -> persistence
    """

    # ---------------------------------------------------------
    # Acceptance criterion
    # ---------------------------------------------------------
    acceptance = SimpleNamespace(
        id=1,
        criterion="User can sign in successfully with valid credentials",
        is_met=True,
    )

    # ---------------------------------------------------------
    # Requirement
    # ---------------------------------------------------------
    requirement = SimpleNamespace(
        id=1,
        requirement_id="REQ-001",
        title="User Login",
        description=(
            "Users must be able to sign in securely using valid "
            "application credentials."
        ),
        rationale=(
            "Authentication is required to protect application "
            "resources."
        ),
        source="Product requirements specification",
        requirement_type="functional",
        acceptance_criteria=[acceptance],
        trace_links=[],
    )

    # ---------------------------------------------------------
    # Development task
    # ---------------------------------------------------------
    task = SimpleNamespace(
        id=1,
        task_key="TASK-001",
        title="Implement user login",
        description="Implement authentication and login flow.",
        status="completed",
        completed=True,
        priority="high",
        requirement_id=1,
        depends_on_task_id=None,
    )

    # ---------------------------------------------------------
    # Generated test evidence
    #
    # This represents an existing GeneratedTest row that is
    # already associated with the project and requirement.
    # ---------------------------------------------------------
    generated_test = SimpleNamespace(
        id=1,
        project_id=1,
        title="Verify User Login",
        description=(
            "Verify users can sign in successfully with valid "
            "credentials."
        ),
    )

    # ---------------------------------------------------------
    # Persisted traceability evidence
    #
    # release_gate_report() explicitly checks these database
    # trace links:
    #
    # requirement -> development_task
    # requirement -> generated_test
    # ---------------------------------------------------------
    trace_requirement_task = SimpleNamespace(
        project_id=1,
        source_type="requirement",
        source_id=1,
        target_type="development_task",
        target_id=1,
        relation="implements",
    )

    trace_requirement_test = SimpleNamespace(
        project_id=1,
        source_type="requirement",
        source_id=1,
        target_type="generated_test",
        target_id=1,
        relation="verifies",
    )

    # ---------------------------------------------------------
    # Database architecture evidence
    # ---------------------------------------------------------
    column = SimpleNamespace(
        name="id",
        primary_key=True,
    )

    table = SimpleNamespace(
        name="users",
        columns=[column],
    )

    database_design = SimpleNamespace(
        tables=[table],
        relationships=[],
    )

    # ---------------------------------------------------------
    # Prototype architecture evidence
    # ---------------------------------------------------------
    screen = SimpleNamespace(
        name="Login",
    )

    prototype_design = SimpleNamespace(
        screens=[screen],
        flows=[],
    )

    # ---------------------------------------------------------
    # Documentation evidence
    # ---------------------------------------------------------
    documentation_set = SimpleNamespace(
        documents=[
            SimpleNamespace(id=1),
        ]
    )

    # ---------------------------------------------------------
    # Project
    # ---------------------------------------------------------
    project = SimpleNamespace(
        id=1,
        name="Phase 34 Demo",
	    description="End-to-end release automation demonstration project.",
	    status="active",
        target_date=None,
        requirements=[requirement],
        development_tasks=[task],
	    knowledge_entries=[],
        maintenance_items=[],
        documentation_set=documentation_set,
        database_design=database_design,
        prototype_design=prototype_design,
        git_repository=SimpleNamespace(
            url="https://example.com/specforge-demo.git",
            enabled=True,
            repo_path="D:\\SpecForgeAI_Phase27",
        ),
        user_stories=[],
    )

    # ---------------------------------------------------------
    # Release
    # ---------------------------------------------------------
    release = SimpleNamespace(
        id=1,
        project_id=1,
        version="v1.0.0",
        name="Phase 34 Release",
        description="Release automation integration test.",
        readiness_score=100,
        gate_status="ready",
    )

    # ---------------------------------------------------------
    # Fake database session
    # ---------------------------------------------------------
    db = FakeDB(
        trace_links=[
            trace_requirement_task,
            trace_requirement_test,
        ],
        generated_tests=[
            generated_test,
        ],
    )

    # ---------------------------------------------------------
    # Git evidence
    #
    # release_automation_service uses _safe_git().
    # release_service uses git_status().
    # ---------------------------------------------------------
    git_result = {
        "available": True,
        "status": {
            "clean": True,
            "branch": "main",
            "changes": [],
        },
        "commits": [
            {
                "short_hash": "abc123",
                "subject": "Implement user login",
            }
        ],
        "risk": {
            "level": "low",
        },
    }

    monkeypatch.setattr(
        "app.services.release_automation_service._safe_git",
        lambda *args, **kwargs: git_result,
    )

    monkeypatch.setattr(
        "app.services.release_service.git_status",
        lambda *args, **kwargs: {
            "available": True,
            "clean": True,
            "status": "clean",
        },
    )

    monkeypatch.setattr(
        "app.services.release_service.git_risk",
        lambda *args, **kwargs: {
            "level": "low",
        },
    )

    # ---------------------------------------------------------
    # AI release review
    # ---------------------------------------------------------
    ai_review = {
        "decision": "GO",
        "score": 95,
        "summary": "Release evidence is complete.",
        "blockers": [],
        "risks": [],
        "required_actions": [],
        "evidence_gaps": [],
    }

    from app.services.release_service import release_gate_report
    from app.services import release_automation_service as ras

    run_automation.__globals__["release_gate_report"] = release_gate_report

    monkeypatch.setitem(
        release_gate_report.__globals__,
        "git_status",
        lambda *args, **kwargs: {
            "available": True,
            "clean": True,
            "branch": "main",
            "changes": [],
        },
    )

    monkeypatch.setitem(
        release_gate_report.__globals__,
        "git_risk",
        lambda *args, **kwargs: {
            "level": "low",
        },
    )

    monkeypatch.setattr(
        ras,
        "ai_release_review",
        lambda *args, **kwargs: ai_review,
    )

    run_automation.__globals__["ai_release_review"] = ras.ai_release_review

    result = run_automation(
        db,
        project,
        release,
        include_ai=True,
    )

    # ---------------------------------------------------------
    # Core result
    #
    # Production code calculates:
    #
    # (readiness score 100 + AI score 95) / 2 = 97.5
    # round(97.5) = 98
    # ---------------------------------------------------------
    assert result is not None
    assert result.decision == "GO"
    assert result.score == 98

    # ---------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------
    assert result.project_id == project.id
    assert result.release_id == release.id
    assert result.release_notes
    assert result.test_suite
    assert result.ai_review
    assert result.evidence
    assert db.added
    assert db.committed is True

    # ---------------------------------------------------------
    # Deserialize generated automation artifacts
    #
    # ReleaseAutomationRun stores these fields as JSON strings.
    # ---------------------------------------------------------
    import json

    ai_review_result = json.loads(result.ai_review)
    suite = json.loads(result.test_suite)
    evidence = json.loads(result.evidence)
    notes = result.release_notes

    # ---------------------------------------------------------
    # AI review
    # ---------------------------------------------------------
    assert ai_review_result["decision"] == "GO"
    assert ai_review_result["score"] == 95

    # ---------------------------------------------------------
    # Generated release test suite
    # ---------------------------------------------------------
    assert suite
    assert suite[0]["requirement_id"] == 1
    assert suite[0]["requirement_key"] == "REQ-001"

    # ---------------------------------------------------------
    # Release notes
    # ---------------------------------------------------------
    assert "# v1.0.0" in notes
    assert "Phase 34 Release" in notes

    # ---------------------------------------------------------
    # Evidence
    #
    # These keys match the REAL evidence() implementation.
    # ---------------------------------------------------------
    assert evidence["readiness"]["readiness_score"] == 100
    assert evidence["readiness"]["ready"] is True
    assert evidence["test_count"] >= 1
    assert evidence["release_notes_characters"] > 0
    assert evidence["requirements"] == 1
    assert evidence["tasks"] == 1
    assert evidence["documentation_documents"] == 1

    # ---------------------------------------------------------
    # Persistence
    #
    # run_automation() should create an automation run and
    # persist it through the supplied DB session.
    # ---------------------------------------------------------
    assert db.added
    assert db.committed is True