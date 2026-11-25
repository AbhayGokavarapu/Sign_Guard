"""Bounded Poppler comparisons. No PDF actions or certificate network fetching."""
import io
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import numpy as np
from PIL import Image, ImageFilter
import pymupdf as fitz
import config
from core.pdf_parser import render_bounded,validate_pdf,parse_pdf


def availability():
    return {'renderer':bool(shutil.which('pdftoppm')),'signature_validator':bool(shutil.which('pdfsig'))}


def compare_renderers(raw):
    binary=shutil.which('pdftoppm')
    if not binary:return {'complete':False,'error':'Poppler pdftoppm is not installed. Install poppler-utils.','pages':[]}
    pages=[]
    with tempfile.TemporaryDirectory(prefix='signguard-render-') as folder:
        pdf=Path(folder)/'document.pdf';pdf.write_bytes(raw)
        with fitz.open(stream=raw,filetype='pdf') as doc:
            for index in range(min(len(doc),config.MAX_RENDERER_PAGES)):
                pix=render_bounded(doc[index],config.THUMBNAIL_DPI,annots=False)
                a=Image.frombytes('RGB',(pix.width,pix.height),pix.samples).convert('L')
                prefix=Path(folder)/f'page-{index}'
                ret=subprocess.run([binary,'-f',str(index+1),'-l',str(index+1),'-singlefile','-hide-annotations',
                    '-r',str(config.THUMBNAIL_DPI),'-png',str(pdf),str(prefix)],capture_output=True,timeout=20)
                output=prefix.with_suffix('.png')
                if ret.returncode or not output.exists():return {'complete':False,'pages':pages,'error':'Poppler could not render the page.'}
                with Image.open(output) as image:
                    dimensions_match=image.size==a.size
                    b=image.convert('L').resize(a.size)
                aa=np.asarray(a.filter(ImageFilter.GaussianBlur(1)),dtype=np.int16)
                bb=np.asarray(b.filter(ImageFilter.GaussianBlur(1)),dtype=np.int16)
                pct=float((np.abs(aa-bb)>40).mean()*100)
                pages.append({'page':index,'changed_area_pct':round(pct,4),
                              'dimensions_match':dimensions_match,'disagreement':pct>config.RENDERER_DIFFERENCE_THRESHOLD or not dimensions_match})
            complete=len(doc)<=config.MAX_RENDERER_PAGES
    return {'engines':['MuPDF','Poppler'],'pages':pages,'complete':complete,
        'disagreement':any(p['disagreement'] for p in pages),'threshold_pct':config.RENDERER_DIFFERENCE_THRESHOLD,
        'method':'96 DPI grayscale, 1px blur, residual >40; same-position pages; annotations hidden.',
        'note':'Antialiasing can differ normally. Agreement does not establish authenticity or exclude all shadow attacks.'}


def validate_with_poppler(raw):
    validation=validate_pdf(raw,'document.pdf')
    if not validation.valid:return {'complete':False,'error':validation.reason}
    parsed=parse_pdf(raw)
    if parsed.error:return {'complete':False,'error':parsed.error}
    binary=shutil.which('pdfsig')
    if not binary:return {'complete':False,'error':'Poppler pdfsig is not installed.','signatures':[]}
    with tempfile.TemporaryDirectory(prefix='signguard-pdfsig-') as folder:
        path=Path(folder)/'document.pdf';path.write_bytes(raw)
        # -nocert and -no-ocsp prevent network validation; compare mathematics, not trust stores.
        ret=subprocess.run([binary,'-nocert','-no-ocsp',str(path)],capture_output=True,text=True,timeout=30,
                           env={**__import__('os').environ,'LC_ALL':'C'})
    outcomes=[]
    for line in ret.stdout.splitlines():
        if 'Signature Validation:' in line:
            text=line.split('Signature Validation:',1)[1].strip()
            outcomes.append({'valid':text=='Signature is Valid.','detail':text})
    return {'validator':'Poppler pdfsig','certificate_validation':'disabled for cross-validator mathematical comparison',
        'signatures':outcomes,'complete':ret.returncode==0,'exit_code':ret.returncode,
        'summary':ret.stdout[-12000:],'error':ret.stderr[-1000:] if ret.returncode else None}
