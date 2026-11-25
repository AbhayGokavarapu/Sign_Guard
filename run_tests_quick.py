"""Security outcome tests plus regenerated demo evidence. Exits nonzero on failure."""
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import config
from core.pipeline import run
from reporting.json_report import to_json
from reporting.pdf_report import build_pdf_report
from simulation.controlled_scenarios import ALL_SCENARIOS


def main():
    check = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_security_outcomes.py', '-q', '-p', 'no:cacheprovider'],
                           cwd=config.BASE_DIR, capture_output=True, text=True)
    print(check.stdout)
    if check.returncode:
        print(check.stderr)
        return check.returncode
    expected = {'A': ('INCONCLUSIVE', None), 'B': ('TAMPERING DETECTED', 'CRYPTO-001'),
                'C': ('REVIEW REQUIRED', 'SHADOW-001'), 'D': ('REVIEW REQUIRED', 'ORB-001'),
                'E': ('INCONCLUSIVE', None), 'F': ('INCONCLUSIVE', None)}
    checks=[]
    for scenario in ALL_SCENARIOS:
        _, raw, _ = scenario.factory()
        result = run(raw, f'scenario_{scenario.id}.pdf', record_audit=False)
        verdict, code = expected[scenario.id]
        passed = result.fusion.verdict.value == verdict and (code is None or code in {f.code for f in result.fusion.findings})
        checks.append({'scenario':scenario.id,'passed':passed,'verdict':result.fusion.verdict.value,
                       'findings':[f.code for f in result.fusion.findings]})
        base = Path(config.SCENARIO_RESULTS_DIR) / f'scenario_{scenario.id}'
        base.with_suffix('.json').write_text(to_json(result))
        base.with_suffix('.pdf').write_bytes(build_pdf_report(result))
        if result.parsed and result.parsed.page_images:
            result.parsed.page_images[0].save(str(base)+'_preview.png')
        print(checks[-1])
    count = int(re.search(r'(\d+) passed',check.stdout).group(1))
    summary={'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
             'passed':count+sum(c['passed'] for c in checks),
             'failed':sum(not c['passed'] for c in checks),'python':sys.version,'scenarios':checks}
    (Path(config.OUTPUTS_DIR)/'integration_test_summary.json').write_text(json.dumps(summary,indent=2))
    (Path(config.OUTPUTS_DIR)/'integration_test_summary.txt').write_text(check.stdout+'\n'+json.dumps(summary,indent=2))
    return 0 if all(c['passed'] for c in checks) else 1


if __name__=='__main__':raise SystemExit(main())
