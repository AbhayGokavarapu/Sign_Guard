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


def test_public_dashboard_does_not_read_shared_history(monkeypatch):
    import core.audit_logger
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    from dashboard.navigation import PAGES
    monkeypatch.setattr(config, 'PUBLIC_DEMO', True)
    def forbidden(*args, **kwargs):
        raise AssertionError('Shared history must not be read')
    monkeypatch.setattr(core.audit_logger, 'get_records', forbidden)
    app=AppTest.from_file(str(Path(config.BASE_DIR)/'streamlit_app.py')).run()
    for page in PAGES:
        app.radio[0].set_value(page).run()
        assert not app.exception


def test_public_navigation_has_only_four_pages_and_no_benchmark_control(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    monkeypatch.setattr(config, 'PUBLIC_DEMO', True)
    app=AppTest.from_file(str(Path(config.BASE_DIR)/'streamlit_app.py')).run()
    assert not app.exception
    assert app.radio[0].options==['Document analysis','Document comparison','Attack lab','Evidence viewer']
    assert not any('Re-run evaluation' in b.label for b in app.button)
