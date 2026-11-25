"""Ordered text and image comparison; differences are evidence, not a forgery verdict."""
import difflib
import hashlib
import io
import pymupdf as fitz
from core.pdf_parser import parse_pdf, render_bounded
import config


def ordered_text_diff(before, after):
    a,b=before.splitlines(),after.splitlines()
    changes=[]
    for tag,i,j,k,l in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_opcodes():
        if tag!='equal':
            changes.append({'operation':tag,'before_lines':[i+1,j], 'after_lines':[k+1,l],
                            'removed':a[i:j], 'added':b[k:l]})
    return changes


def compare_raw(original, suspect, original_name='original.pdf', suspect_name='suspect.pdf', image_limit=3):
    from core.pdf_parser import validate_pdf
    for name,raw in [(original_name,original),(suspect_name,suspect)]:
        validation=validate_pdf(raw,name)
        if not validation.valid:return {'error':f'{name}: {validation.reason}','complete':False}
        parsed=parse_pdf(raw,name)
        if parsed.error:return {'error':f'{name}: {parsed.error}','complete':False}
        del parsed
    from core.revision_analyzer import _pixel_diff
    result={'comparison_type':'Known original versus suspect; differences do not establish forgery',
            'original':{'filename':original_name,'sha256':hashlib.sha256(original).hexdigest()},
            'suspect':{'filename':suspect_name,'sha256':hashlib.sha256(suspect).hexdigest()},
            'identical_bytes':original==suspect,'pages':[], 'images':[], 'complete':True,'limitations':[]}
    with fitz.open(stream=original,filetype='pdf') as a, fitz.open(stream=suspect,filetype='pdf') as b:
        result['original']['page_count']=len(a);result['suspect']['page_count']=len(b)
        result['metadata_changes']={key:{'before':a.metadata.get(key),'after':b.metadata.get(key)}
            for key in sorted(set(a.metadata)|set(b.metadata)) if a.metadata.get(key)!=b.metadata.get(key)}
        for page in range(max(len(a),len(b))):
            if page>=len(a):
                result['pages'].append({'page':page,'change':'added','text_changes':ordered_text_diff('',b[page].get_text())});continue
            if page>=len(b):
                result['pages'].append({'page':page,'change':'removed','text_changes':ordered_text_diff(a[page].get_text(),'')});continue
            ai,bi=render_bounded(a[page],config.THUMBNAIL_DPI),render_bounded(b[page],config.THUMBNAIL_DPI)
            from PIL import Image
            image_a=Image.frombytes('RGB',(ai.width,ai.height),ai.samples)
            image_b=Image.frombytes('RGB',(bi.width,bi.height),bi.samples)
            diff,mask,pct,boxes=_pixel_diff(image_a,image_b)
            text=ordered_text_diff(a[page].get_text(),b[page].get_text())
            dimensions_changed=a[page].rect!=b[page].rect
            changed=bool(text or pct>0 or dimensions_changed)
            result['pages'].append({'page':page,'change':'modified' if changed else 'unchanged',
                'changed_area_pct':round(pct,4),'dimensions_changed':dimensions_changed,
                'text_changes':text,'changed_boxes':boxes})
            if changed and len(result['images'])<image_limit:
                panels={}
                for name,image in [('original',image_a),('suspect',image_b),('difference',diff)]:
                    image.thumbnail((900,1000));buffer=io.BytesIO();image.save(buffer,'PNG');panels[name]=buffer.getvalue()
                result['images'].append({'page':page,**panels})
        result['changed_pages']=[row['page'] for row in result['pages'] if row['change']!='unchanged']
    result['limitations'].append('Pages are aligned by position. Insertions/reordering can shift later comparisons; text extraction may miss scanned content.')
    return result


def compare(original,suspect,original_name='original.pdf',suspect_name='suspect.pdf'):
    from core.worker import execute_task
    return execute_task('compare',dict(original=original,suspect=suspect,original_name=original_name,suspect_name=suspect_name))


def public_comparison(result):
    return {key:value for key,value in result.items() if key!='images'}
