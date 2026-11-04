"""Sway vector PDF extraction and HTTP upload regression checks."""
from io import BytesIO
import os
from pathlib import Path

from fastapi.testclient import TestClient
import pymupdf
import pytest

from app.pdf_import import MAX_PDF_BYTES, PDFImportError, import_sway_pdf
from app.server import app


def sway_pdf(*, ghost=False, offstage=False, wrong_count=False, missing_name=False,
             scale=1, second_roster=False):
    """Generate the observed export structure without storing a user's routine."""
    doc = pymupdf.open()
    for index in range(2):
        page = doc.new_page(width=800*scale, height=600*scale)
        page.insert_text((30*scale, 30*scale), 'Practice', fontsize=14*scale)
        page.insert_text((30*scale, 55*scale), f'F{index+1}', fontsize=11*scale)
        page.insert_text((30*scale, 80*scale), f"38' x 28' stage  |  {3 if wrong_count else 2} performers  |  2.5s hold", fontsize=9*scale)
        rect = pymupdf.Rect(200*scale, 170*scale, 580*scale, 450*scale)
        page.draw_rect(rect, color=(.4,.6,1))
        for name,x,y in [('Alpha', 280, 260), ('Changed' if second_roster and index else 'Beta', 680 if offstage and index else 470, 330)]:
            if ghost:
                page.draw_circle((x*scale,y*scale),5*scale,color=(.35,.5,.79),fill=(.14,.29,.57))
            page.draw_circle((x*scale,y*scale),7*scale,color=(1,1,1),fill=(0,.71,.85))
            if not (missing_name and name=='Beta'):
                fontsize=7*scale
                length=pymupdf.get_text_length(name,fontsize=fontsize)
                page.insert_text((x*scale-length/2,y*scale-12*scale),name,fontsize=fontsize)
    content=doc.tobytes();doc.close();return content


def test_extracts_dimensions_names_order_timing_and_positions():
    result=import_sway_pdf(sway_pdf(ghost=True))
    assert result['routine']['stage']=={'width':38.0,'height':28.0,'units':'ft'}
    assert [f['name'] for f in result['routine']['formations']]==['F1','F2']
    first=result['routine']['formations'][0]
    assert first['hold_seconds']==2.5 and first['source_page']==1
    assert first['dancers']==[{'id':'Alpha','x':8.0,'y':9.0},{'id':'Beta','x':27.0,'y':16.0}]
    assert all(page['importable'] for page in result['pages'])


def test_page_scale_does_not_change_coordinates():
    normal=import_sway_pdf(sway_pdf())
    scaled=import_sway_pdf(sway_pdf(scale=1.4))
    assert normal['routine']==scaled['routine']


def test_offstage_positions_are_preserved_and_reported_not_clipped():
    result=import_sway_pdf(sway_pdf(offstage=True))
    assert result['pages'][0]['importable']
    assert not result['pages'][1]['importable']
    assert any('outside stage' in e for e in result['pages'][1]['issues'])
    assert result['routine']['formations'][1]['dancers'][1]['x']==48


def test_roster_change_requires_review():
    result=import_sway_pdf(sway_pdf(second_roster=True))
    assert not result['pages'][1]['importable']
    assert any('roster' in e for e in result['pages'][1]['issues'])


@pytest.mark.parametrize('options',[{'wrong_count':True},{'missing_name':True}])
def test_unreliable_label_detection_is_rejected(options):
    with pytest.raises(PDFImportError,match='expected'):
        import_sway_pdf(sway_pdf(**options))


@pytest.mark.parametrize('content',[b'not a PDF',b'%PDF-broken'])
def test_invalid_or_corrupt_file_is_rejected(content):
    with pytest.raises(PDFImportError):import_sway_pdf(content)


def test_image_only_document_is_not_silently_imported():
    doc=pymupdf.open();doc.new_page();content=doc.tobytes();doc.close()
    with pytest.raises(PDFImportError,match='Scanned images'):
        import_sway_pdf(content)


def test_upload_endpoint_and_repair_integration():
    client=TestClient(app)
    response=client.post('/api/import/sway-pdf',files={'file':('sway.pdf',BytesIO(sway_pdf()),'application/pdf')})
    assert response.status_code==200
    routine=response.json()['routine']
    repair=client.post('/api/repair',json={'routine':routine,'missing':'Alpha','preference':'minimize_changes'})
    assert repair.status_code==200 and repair.json()['valid']
    assert all([p['id'] for p in f['dancers']]==['Beta'] for f in repair.json()['routine']['formations'])
    assert client.post('/api/import/sway-pdf',files={'file':('bad.pdf',b'bad','application/pdf')}).status_code==422
    assert client.post('/api/import/sway-pdf').status_code==422


def test_oversize_upload_is_rejected():
    response=TestClient(app).post('/api/import/sway-pdf',files={'file':('large.pdf',b'%PDF-'+b' ' * MAX_PDF_BYTES,'application/pdf')})
    assert response.status_code==413


@pytest.mark.skipif(not os.environ.get('SWAY_SAMPLE_PDF'), reason='Set SWAY_SAMPLE_PDF to run the supplied Kuthu PDF regression.')
def test_supplied_kuthu_pdf():
    result=import_sway_pdf(Path(os.environ['SWAY_SAMPLE_PDF']).read_bytes())
    assert len(result['pages'])==13
    assert [f['name'] for f in result['routine']['formations']]==['F1','F2','F3','F5','F6','F7','F8','F9','F10','F11','F12','F13','F14']
    assert all(len(f['dancers'])==14 for f in result['routine']['formations'])
    assert len({p['id'] for p in result['routine']['formations'][0]['dancers']})==14
    assert result['routine']['stage']=={'width':38,'height':28,'units':'ft'}
    assert sum(page['importable'] for page in result['pages'])==12
    assert not result['pages'][-1]['importable']
    # F2 includes previous-position ghosts; only current white-outlined dots count.
    steve=next(p for p in result['routine']['formations'][1]['dancers'] if p['id']=='Steve')
    assert steve=={'id':'Steve','x':3.5625,'y':12.25}
    routine={**result['routine'],'formations':result['routine']['formations'][:-1]}
    response=TestClient(app).post('/api/repair',json={'routine':routine,'missing':'Rhea'})
    assert response.status_code==200 and response.json()['valid']
