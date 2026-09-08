import json
import pytest

from app.baseline.service import baseline_service
from app.ml.runtime import ml_runtime
from app.runtime import runtime_service
from app.verification.models import ReleaseStatus,VerificationCheck,VerificationStatus,overall_for
from app.verification.service import verification_service


def check(status,critical=True):return VerificationCheck(check_id='x',title='x',category='test',status=status,critical=critical,duration_ms=0,evidence={'observed':True},details='test')


def test_release_gate_status_rules():
 assert overall_for([check(VerificationStatus.PASS)]) is ReleaseStatus.READY
 assert overall_for([check(VerificationStatus.PASS),check(VerificationStatus.WARNING,False)]) is ReleaseStatus.READY_WITH_WARNINGS
 assert overall_for([check(VerificationStatus.FAIL,True)]) is ReleaseStatus.NOT_READY


def test_noncritical_failure_does_not_claim_ready():
 assert overall_for([check(VerificationStatus.FAIL,False)]) is ReleaseStatus.READY_WITH_WARNINGS


@pytest.fixture(scope='module')
def release_run():
 before=ml_runtime._interpreter;report=verification_service.run(write_reports=False);return report,before,ml_runtime._interpreter


def test_runner_records_evidence_and_all_critical_checks_pass(release_run):
 report,_,_=release_run;checks=[x for section in report.sections for x in section.checks]
 assert report.total_checks==len(checks)>80
 assert report.overall_status in (ReleaseStatus.READY,ReleaseStatus.READY_WITH_WARNINGS)
 assert not [x for x in checks if x.critical and x.status is VerificationStatus.FAIL]
 assert all(isinstance(x.evidence,dict) for x in checks)


def test_model_restored_and_runner_leaves_clean_state(release_run):
 _,before,after=release_run
 assert after is before
 assert baseline_service.snapshot().state.value=='UNINITIALIZED'
 assert runtime_service.snapshot() is None


def test_deterministic_reset_evidence_and_no_clinical_metrics(release_run):
 report,_,_=release_run;checks={x.check_id:x for section in report.sections for x in section.checks}
 assert checks['reset.reproducible'].status is VerificationStatus.PASS
 text=report.model_dump_json().lower()
 for claim in ('diagnostic accuracy','sensitivity:', 'specificity:', 'disease probability:'):
  assert claim not in text


def test_report_artifacts_and_latest_api_source(release_run,tmp_path,monkeypatch):
 report,_,_=release_run
 import app.verification.service as module
 monkeypatch.setattr(module,'OUTPUT_DIR',tmp_path);verification_service._write(report)
 parsed=json.loads((tmp_path/'latest-verification.json').read_text())
 assert parsed['overall_status']==report.overall_status.value
 assert (tmp_path/'latest-verification.md').read_text().startswith('# Aequor Release Verification')
 assert verification_service.latest() is report
