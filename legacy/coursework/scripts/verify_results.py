"""Independent post-recovery checks, kept separate from the attack."""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server import original


def main():
    recovered=json.loads((ROOT/'output/recovered_keys.json').read_text())
    actual=json.loads((ROOT/'output/client_results.json').read_text())
    cases=json.loads((ROOT/'test_cases.json').read_text())
    decoded=list(csv.DictReader((ROOT/'output/decrypted.csv').open()))
    checks=[]
    for key,result,case in zip(recovered,actual,cases,strict=True):
        session=key['session'];b=2*case['mood'];a=original['next_coprime_above'](b)
        fields={r['field']:r['plaintext'] for r in decoded if int(r['session'])==session}
        check={'session':session,'key_matches_original_after_recovery':(key['a'],key['b'])==(a,b),
            'response_matches_client':key['plaintext']==result['plaintext'],
            'username_matches_input':fields['username_enc']==case['username'],
            'concern_matches_input':fields['message_enc']==case['concern'],
            'reencryption_matches':key['reencryption_matches']}
        assert all(v for k,v in check.items() if k!='session'),check
        checks.append(check)
    assert len(recovered)==5 and len(actual)==5
    assert sum(1 for _ in csv.DictReader((ROOT/'ciphertexts.csv').open()))==15
    pcap=ROOT/'evidence/capture.pcap'
    report={'all_passed':True,'session_checks':checks,'ciphertext_fields':15,
        'pcap_sha256':hashlib.sha256(pcap.read_bytes()).hexdigest(),
        'original_server_sha256':hashlib.sha256((ROOT/'original_server').read_bytes()).hexdigest(),
        'backend':json.loads((ROOT/'output/backend.json').read_text())}
    (ROOT/'output/verification.json').write_text(json.dumps(report,indent=2))
    print('PASS: all five recovered keys, request fields, replies and round trips match.')


if __name__=='__main__':main()
