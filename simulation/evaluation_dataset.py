"""Reproducible synthetic development/held-out controls with localisation annotations."""
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from simulation.security_fixtures import signed_control, tamper_signed, incremental_update, shadow_pair
from simulation.signed_samples import sign_pdf, get_test_cert
from simulation.sample_generator import build_unsigned, build_ela_target, _sig_image
import config


def visual_document(seed, kind):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(595, 842))
    annotations = []
    pages = 3 if kind == 'last_page' else 1
    for page in range(pages):
        c.setFont('Helvetica', 12)
        c.drawString(72, 770, f'Contract reference {seed}, page {page+1}')
        c.drawString(72, 740, 'Review all terms and signatures before acceptance.')
        if page == pages-1:
            if kind == 'scan':
                # Full-page raster text, a benign scan without signatures.
                from PIL import ImageDraw
                im = Image.new('RGB', (595, 842), 'white')
                draw = ImageDraw.Draw(im)
                for line in range(20):
                    draw.text((50, 50+line*25), f'Invoice {seed} ordinary printed text {line}', fill='black')
                c.drawImage(ImageReader(im), 0, 0, 595, 842)
            elif kind == 'image_edit':
                rng = np.random.default_rng(seed)
                im = Image.fromarray(rng.integers(0, 256, (120, 360, 3), dtype=np.uint8))
                # Actual pasted patch in a previously JPEG-compressed raster.
                jpeg = io.BytesIO(); im.save(jpeg, 'JPEG', quality=60)
                jpeg.seek(0); im = Image.open(jpeg).convert('RGB')
                im.paste(Image.fromarray(rng.integers(0, 256, (50, 90, 3), dtype=np.uint8)), (100, 30))
                c.drawImage(ImageReader(im), 72, 200, 240, 80)
            else:
                sig = _sig_image(240, 60, seed)
                locations = [(72, 180)]
                if kind in ('duplicate', 'repeated_logo'):
                    locations.append((330, 180))
                if kind == 'repeated_logo':
                    from PIL import ImageDraw
                    sig = Image.new('RGB', (240, 60), 'white')
                    d = ImageDraw.Draw(sig); d.rectangle((5,5,235,55), outline='blue', width=3)
                    d.text((30,20), f'COMPANY LOGO {seed}', fill='blue')
                for x,y in locations:
                    c.drawImage(ImageReader(sig), x,y, 180,45)
                    if kind != 'repeated_logo':
                        # Coordinates in 144-DPI top-left pixel space.
                        annotations.append({'page': page, 'bbox': [x*2, (842-y-45)*2, 360, 90]})
        c.showPage()
    c.save()
    return buffer.getvalue(), annotations


def generate_evaluation_dataset():
    root = Path(config.DATASETS_DIR) / 'security_v3'
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    kinds = ['genuine','tampered','content_change','annotation','additional_signature',
             'visual','last_page','duplicate','repeated_logo','scan','image_edit','ela','unsigned']
    for index, seed in enumerate((101, 2001, 2002, 2003)):
        split = 'development' if index == 0 else 'held_out'
        original = signed_control(f'Payment amount: ${seed:,}')
        for kind in kinds:
            boxes = []
            if kind == 'genuine': raw = original
            elif kind == 'tampered': raw = tamper_signed(original)
            elif kind == 'content_change': raw = incremental_update(original, f'Payment amount: ${seed+8000:,}')
            elif kind == 'annotation': raw = incremental_update(original, annotation=True)
            elif kind == 'additional_signature':
                raw, message = sign_pdf(original, *get_test_cert(), field_name='Signature2')
                if raw is None: raise RuntimeError(message)
            elif kind in ('visual','last_page','duplicate','repeated_logo','scan','image_edit'):
                raw, boxes = visual_document(seed, kind)
            elif kind == 'ela': raw = build_ela_target()
            else: raw = build_unsigned(f'Unsigned contract {seed}')
            filename = f'{split}_{kind}_{seed}.pdf'
            path = root / filename
            path.write_bytes(raw)
            positive = kind in ('tampered','content_change','duplicate','image_edit')
            label = 'TAMPERING_DETECTED' if kind == 'tampered' else ('REVIEW_REQUIRED' if positive else 'INCONCLUSIVE')
            expected_cls = ('Cryptographically Signed' if kind in ('genuine','tampered','content_change','annotation','additional_signature')
                            else 'Visual Signature Candidate' if kind in ('visual','last_page','duplicate','repeated_logo','image_edit') else 'Unsigned')
            entries.append({'file': str(path.relative_to(config.BASE_DIR)), 'category': kind,
                'label': label, 'positive': positive, 'split': split, 'seed': seed,
                'expected_class': expected_cls, 'signature_boxes': boxes,
                'notes': 'Benign annotations may still be rejected by pyHanko policy.' if kind=='annotation' else ''})
    manifest = {'version':3,'total':len(entries),'files':entries,
        'note':'Synthetic controls only. Held-out seeds were not used to tune thresholds; shared generator limits independence.'}
    (root/'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest
