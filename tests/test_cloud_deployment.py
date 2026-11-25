"""Public deployment must not persist or expose a shared visitor audit log."""
import config
from core.pipeline import run
from simulation.sample_generator import build_unsigned


def test_public_demo_does_not_write_shared_audit(monkeypatch):
    import core.pipeline
    monkeypatch.setattr(config, 'PUBLIC_DEMO', True)
    def forbidden(*args):
        raise AssertionError('Public visitor audit must not be persisted')
    monkeypatch.setattr(core.pipeline, 'append_record', forbidden)
    result = run(build_unsigned('Public test document'))
    assert result.audit_error is None
    assert result.coverage['audit_persistence'].startswith('Disabled')


def test_public_reports_hide_shared_history(monkeypatch):
    import dashboard.reports
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(config, 'PUBLIC_DEMO', True)
    def forbidden():
        raise AssertionError('Shared history must not be read')
    monkeypatch.setattr(dashboard.reports, 'get_records', forbidden)
    app = AppTest.from_string('from dashboard.reports import render\nrender()').run()
    assert not app.exception
    assert any('Shared audit history is disabled' in x.value for x in app.info)


def test_public_benchmark_regeneration_disabled(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(config, 'PUBLIC_DEMO', True)
    app = AppTest.from_string('from dashboard.evaluation import render\nrender()').run()
    assert not app.exception
    assert app.button[0].disabled
