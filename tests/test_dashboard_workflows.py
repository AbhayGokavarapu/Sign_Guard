"""Exercise actual Streamlit renderers, controls and evidence states."""
import hashlib
import io
from pathlib import Path
import pytest
from PIL import Image, ImageChops
from streamlit.testing.v1 import AppTest
import config
from core.pipeline import run, _failure
from simulation.controlled_scenarios import ALL_SCENARIOS
from dashboard.revision_evidence import change_overlay

ROOT=Path(config.BASE_DIR)
PAGES=['Overview','Document analysis','Document comparison','Attack lab','Evidence viewer','Evaluation','Reports & audit','Case review','Presentation']

@pytest.fixture(autouse=True)
def public(monkeypatch):
    monkeypatch.setattr(config,'PUBLIC_DEMO',True)

@pytest.fixture(scope='module')
def scenarios():
    return {s.id:run(s.factory()[1],f'scenario_{s.id}.pdf',record_audit=False) for s in ALL_SCENARIOS}

def check(app):
    assert not app.exception, [(e.message,e.stack_trace) for e in app.exception]
    return app

def app_for(page=None):
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=60)
    if page:app.session_state['nav_page']=page
    return app

def click(app,label):
    return check(next(b for b in app.button if b.label==label).click().run())

@pytest.mark.parametrize('page',PAGES)
def test_empty_pages(page):
    check(app_for(page).run())

@pytest.mark.parametrize('scenario_id',['A','B','C','D','E','F'])
def test_all_pages_with_scenario_results(scenarios,scenario_id):
    app=app_for()
    result=scenarios[scenario_id]
    app.session_state['pipeline_result']=result
    app.session_state['evidence_result']=result
    app.session_state['pres_sc_result']=result
    for page in PAGES:
        app.session_state['nav_page']=page
        if page=='Presentation':app.session_state['pres_step']=3
        check(app.run())
    assert len(app.get('image'))>0
    if scenario_id in ('A','B'):
        assert any('No visible pixel difference' in i.value for i in app.info)
    elif scenario_id=='C':
        assert any('Changed area:' in c.value for c in app.caption)
        assert any('Raw pixel difference' in e.label for e in app.expander)
    else:
        assert any('No signed revision' in i.value for i in app.info)
    app.session_state['pres_step']=4
    check(app.run())
    assert len(app.get('download_button'))==2


def test_highlight_does_not_mutate_analysis(scenarios):
    rv=scenarios['C'].revision
    original=rv.current_image.copy()
    overlay=change_overlay(rv)
    assert overlay.size==rv.current_image.size
    assert ImageChops.difference(original,overlay).getbbox()
    assert ImageChops.difference(original,rv.current_image).getbbox() is None
    assert rv.diff_image.getbbox()


def test_presentation_controls_and_scenario_invalidation():
    app=check(app_for('Presentation').run())
    assert next(b for b in app.button if b.label=='← Previous').disabled
    click(app,'Load signed demo document')
    raw=app.session_state['pres_raw']
    assert app.session_state['pres_hash']==hashlib.sha256(raw).hexdigest()
    click(app,'Next →');click(app,'Verify baseline →');click(app,'Next →')
    click(app,'Generate and analyse scenario →')
    assert app.session_state['pres_sc_id']=='A'
    # Changing the selection must not leave the previous verdict under a new label.
    app.selectbox(key='pres_scenario').select_index(2).run();check(app)
    assert 'pres_sc_result' not in app.session_state
    click(app,'Generate and analyse scenario →')
    assert app.session_state['pres_sc_id']=='C'
    click(app,'Next →')
    assert any('Zoomed changed region' in str(i.proto) for i in app.get('image'))
    click(app,'Next →')
    assert next(b for b in app.button if b.label=='Next →').disabled
    click(app,'Restart walkthrough')
    assert app.session_state['pres_step']==0


def test_failed_and_partial_results_do_not_crash():
    app=app_for()
    failed=_failure('Test worker timeout')
    app.session_state['pipeline_result']=failed
    app.session_state['evidence_result']=failed
    app.session_state['pres_sc_result']=failed
    for page in PAGES:
        app.session_state['nav_page']=page
        app.session_state['pres_step']=3
        check(app.run())


def test_optional_evidence_empty_states(scenarios):
    from copy import copy
    result=copy(scenarios['C'])
    result.revision=None;result.localization=None;result.ela=None;result.ransac=None;result.orb=None
    app=app_for('Presentation')
    app.session_state['pres_step']=3;app.session_state['pres_result']=result
    check(app.run())
    assert len(app.info)>=4


def test_document_upload_settings_preview_and_malformed_input(scenarios):
    # AppTest has no file-upload action; inject only the uploaded-file boundary.
    source='''
import io
import streamlit as st
class Uploaded(io.BytesIO):
    name='ui-test.pdf'
def upload(*args, **kwargs):
    return Uploaded(st.session_state['test_raw'])
from unittest.mock import patch
from dashboard.document_analysis import render
with patch('streamlit.file_uploader',side_effect=upload):
    render()
'''
    app=AppTest.from_string(source,default_timeout=60)
    app.session_state['test_raw']=scenarios['C'].parsed.raw_bytes
    check(app.run())
    assert len(app.get('image'))>0
    click(app,'Run document analysis →')
    assert app.session_state['pipeline_result'].revision.diff_image.getbbox()
    assert len(app.get('download_button'))>=2
    app.slider(key='ela_quality').set_value(80).run();check(app)
    assert 'pipeline_result' not in app.session_state
    app.session_state['test_raw']=b'not a PDF'
    check(app.run())
    assert app.error
    click(app,'Retry reading this document')
    assert app.error


def test_attack_lab_generate_analyse_every_scenario():
    app=check(app_for('Attack lab').run())
    for index,scenario in enumerate(ALL_SCENARIOS):
        app.selectbox(key='lab_scenario').select_index(index).run();check(app)
        app.button(key='lab_generate').click().run();check(app)
        assert 'lab_'+scenario.id in app.session_state
        app.button(key='lab_analyse').click().run();check(app)
        result=app.session_state['lab_result_'+scenario.id]
        assert not result.processing_error
        assert result.fusion.verdict.value.replace(' ','_')==scenario.ground_truth
        assert len(app.get('download_button'))>=2
    app.button(key='lab_view_evidence').click().run();check(app)
    assert app.session_state['nav_page']=='Evidence viewer'


def test_comparison_and_review_exports(scenarios):
    from reporting.evidence_bundle import verify_bundle
    app=check(app_for('Document comparison').run())
    app.button(key='comparison_demo').click().run();check(app)
    assert app.session_state['comparison_result']['changed_pages']==[0]
    click(app,'Prepare comparison evidence package')
    bundle=app.session_state['comparison_bundle']
    assert verify_bundle(bundle[0],bundle[1])['valid']
    app.session_state['pipeline_result']=scenarios['B']
    app.session_state['nav_page']='Case review';check(app.run())
    click(app,'Save assessment')
    assert app.error  # Missing reason must be rejected rather than silently saved.
    next(s for s in app.selectbox if s.label=='Assessment').set_value('Benign')
    app.text_area[0].set_value('Known controlled demonstration; source bytes reviewed.')
    click(app,'Save assessment')
    assert app.session_state['human_reviews'][scenarios['B'].parsed.sha256]
    assert scenarios['B'].fusion.verdict.value=='TAMPERING DETECTED'
    app.session_state['nav_page']='Reports & audit';check(app.run())
    app.button(key='reports_package_prepare').click().run();check(app)
    bundle=app.session_state['reports_package_bundle']
    assert verify_bundle(bundle[0],bundle[1])['valid']
    app.checkbox(key='reports_package_source').check().run();check(app)
    assert not any(b.key=='reports_package_download' for b in app.get('download_button'))
    app.button(key='clear_workspace').click().run();check(app)
    for key in ('pipeline_result','human_reviews','comparison_result','pres_result'):
        assert key not in app.session_state
    assert app.session_state['nav_page']=='Overview'


def test_report_package_verification_control(scenarios):
    from reporting.evidence_bundle import build_bundle
    bundle,reference=build_bundle(result=scenarios['C'])
    source='''
import io
import streamlit as st
class Uploaded(io.BytesIO):
    name='evidence.zip'
from unittest.mock import patch
from dashboard.reports import render
with patch('streamlit.file_uploader',side_effect=lambda *a,**k: Uploaded(st.session_state['test_zip'])):
    render()
'''
    app=AppTest.from_string(source,default_timeout=60)
    app.session_state['test_zip']=bundle
    check(app.run())
    app.text_input[0].set_value(reference)
    click(app,'Verify package integrity')
    assert any('Package is consistent' in s.value for s in app.success)
    app.session_state['test_zip']=b'invalid zip'
    check(app.run());click(app,'Verify package integrity')
    assert app.error


def test_presentation_revision_example_keeps_scenario_label_consistent(scenarios):
    app=app_for('Presentation')
    app.session_state['pres_step']=3
    app.session_state['pres_result']=scenarios['A']
    check(app.run())
    app.button(key='pres_revision_example').click().run();check(app)
    assert app.session_state['pres_sc_id']=='C'
    assert app.session_state['pres_sc_result'].revision.changed_area_pct>0
    click(app,'← Previous')
    assert app.selectbox(key='pres_scenario').value.id=='C'
