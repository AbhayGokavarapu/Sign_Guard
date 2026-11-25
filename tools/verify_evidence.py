"""Independent package integrity verifier. Does not extract or execute bundled files."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reporting.evidence_bundle import verify_bundle


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('package',type=Path)
    parser.add_argument('--expected-manifest-sha256')
    parser.add_argument('--trusted-public-key',type=Path)
    args=parser.parse_args()
    result=verify_bundle(args.package.read_bytes(),args.expected_manifest_sha256,
                         args.trusted_public_key.read_bytes() if args.trusted_public_key else None)
    print(json.dumps(result,indent=2))
    return 0 if result['valid'] else 1


if __name__=='__main__':raise SystemExit(main())
