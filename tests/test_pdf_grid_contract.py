"""RED acceptance contract: preserve PDF grid divisions for frontend rendering.

No repair logic changes are requested here. Numeric grid metadata is additive:
`stage.grid.x/y` contain major divisions in stage units, including the borders.
The synthetic pages have the same 38x28-foot stage but different depth divisions,
matching the distinction between the supplied Kuthu and Bhangra exports.
"""
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.server import app


def gridded_sway_pdf(rows):
    doc=pymupdf.open()
    page=doc.new_page(width=800,height=600)
    page.insert_text((30,30),'Practice')
    page.insert_text((30,55),'F7')
    page.insert_text((30,80),"38' x 28' stage | 2 performers | 2.5s hold",fontsize=9)
    page.draw_rect(pymupdf.Rect(200,170,580,450),color=(.4,.6,1))
    for i in range(9):
        x=200+380*i/8
        page.draw_line((x,170),(x,450),color=(.4,.6,1))
        text=str(i-4);size=7
        page.insert_text((x-pymupdf.get_text_length(text,fontsize=size)/2,465),text,fontsize=size)
    for i in range(rows+1):
        y=170+280*i/rows
        page.draw_line((200,y),(580,y),color=(.4,.6,1))
        page.insert_text((588,y+3),str(rows-i),fontsize=7)
    for name,x,y in [('Alpha',280,260),('Beta',470,330)]:
        page.draw_circle((x,y),7,color=(1,1,1),fill=(0,.71,.85))
        page.insert_text((x-pymupdf.get_text_length(name,fontsize=7)/2,y-12),name,fontsize=7)
    content=doc.tobytes();doc.close();return content


@pytest.mark.parametrize('rows',[4,3],ids=['kuthu-four-depth-divisions','bhangra-three-depth-divisions'])
def test_pdf_import_returns_major_grid_divisions_in_stage_coordinates(rows):
    response=TestClient(app).post('/api/import/sway-pdf',files={
        'file':('gridded.pdf',gridded_sway_pdf(rows),'application/pdf')
    })
    assert response.status_code==200,response.text
    body=response.json()
    assert body['routine']['stage']['width']==38
    assert body['routine']['stage']['height']==28
    grid=body['routine']['stage'].get('grid')
    assert grid is not None,'Return additive stage.grid metadata so UI can use the PDF grid rather than guess its depth divisions'
    assert grid['x']==pytest.approx([i*38/8 for i in range(9)])
    assert grid['y']==pytest.approx([i*28/rows for i in range(rows+1)])
    assert body['routine']['formations'][0]['dancers']==[
        {'id':'Alpha','x':8.0,'y':9.0},{'id':'Beta','x':27.0,'y':16.0}
    ],'Grid extraction must not alter stage coordinates or names'
    repaired=TestClient(app).post('/api/repair',json={
        'routine':body['routine'],'missing':'Alpha','preference':'minimize_changes'
    })
    assert repaired.status_code==200 and repaired.json()['valid']
    assert repaired.json()['routine']['stage']['grid']==grid
