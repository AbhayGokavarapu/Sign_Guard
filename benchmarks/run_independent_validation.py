"""External fixture checks and independent Poppler mathematics, with provenance and disagreements."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import config
from core.pipeline import run
from core.worker import execute_task


def main():
    root=Path(config.BASE_DIR)
    manifest=json.loads((root/'datasets/external-pyhanko/manifest.json').read_text())
    records=[]
    for item in manifest['files']:
        raw=(root/item['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        result=run(raw,Path(item['file']).name,record_audit=False,renderer_check=True)
        independent=execute_task('external_validate',{'raw':raw})
        sigs=result.crypto.results if result.crypto else []
        checks=[]
        for sig in sigs:
            expected=item['expected_checks']
            checks.append(sig.integrity_status==expected['integrity'] and sig.math_valid==expected['math_valid'] and
                ('coverage_level' not in expected or sig.coverage_level==expected['coverage_level']))
        record={**item,'verdict':result.fusion.verdict.value if result.fusion else None,
            'signatures':[{'integrity':s.integrity_status,'math_valid':s.math_valid,'coverage':s.coverage_level,'trust':s.trust_status} for s in sigs],
            'upstream_checks_match':bool(checks) and all(checks),'processing_error':result.processing_error,
            'poppler':independent,'renderer_comparison':result.renderer_comparison,
            'coverage':result.coverage,'engine_source_sha256':result.provenance.get('engine_source_sha256')}
        records.append(record)
        print(Path(item['file']).name,record['verdict'],'upstream checks:',record['upstream_checks_match'],flush=True)
    output={'scope':manifest['scope'],'total':len(records),'upstream_checks_matched':sum(r['upstream_checks_match'] for r in records),
            'independent_human_adjudication':'PENDING; upstream assertions are documented, not a substitute for an external examiner.',
            'records':records}
    (root/'benchmarks/independent_validation.json').write_text(json.dumps(output,indent=2))
    print('Saved benchmarks/independent_validation.json')


if __name__=='__main__':main()
