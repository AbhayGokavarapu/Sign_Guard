"""Static dictionary inventory only. Never execute actions, extract attachments or fetch links."""
from urllib.parse import urlsplit
import pymupdf as fitz
import config


def inspect(raw):
    entries=[]
    with fitz.open(stream=raw,filetype='pdf') as doc:
        count=doc.xref_length()-1
        for xref in range(1,min(doc.xref_length(),config.MAX_STATIC_OBJECTS+1)):
            try:keys=set(doc.xref_get_keys(xref))
            except Exception:continue
            def name(key):return doc.xref_get_key(xref,key)[1]
            action=name('S') if 'S' in keys else ''
            kind=name('Type') if 'Type' in keys else ''
            found=[]
            if action=='/JavaScript' or 'JS' in keys:found.append(('JavaScript','review','Script content/action present; not executed.'))
            if action=='/Launch':found.append(('Launch action','review','External launch action present; not executed.'))
            if 'OpenAction' in keys:found.append(('Open action','review','Document requests an automatic opening action; not executed.'))
            if 'AA' in keys:found.append(('Additional actions','review','Event-triggered actions are present; not executed.'))
            if kind=='/EmbeddedFile' or 'EF' in keys:found.append(('Embedded file','info','Embedded-file structure found; attachment not extracted.'))
            if 'XFA' in keys:found.append(('XFA form','review','Dynamic form structure may render differently across viewers.'))
            if action=='/URI' or 'URI' in keys:
                value=name('URI')
                try:host=urlsplit(value).hostname
                except ValueError:host=None
                found.append(('External link','info','URI action found; target not fetched. Host: '+(host or 'not established')))
            for category,severity,description in found:
                entries.append({'object':xref,'category':category,'severity':severity,'description':description})
    return {'entries':entries,'objects_inspected':min(count,config.MAX_STATIC_OBJECTS),
            'complete':count<=config.MAX_STATIC_OBJECTS,'review_required':any(e['severity']=='review' for e in entries),
            'note':'Presence is not proof of malware. Inventory includes parsed object dictionaries, including potentially unreferenced objects; no actions are executed.'}
