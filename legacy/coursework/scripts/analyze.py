"""Ciphertext-only recovery per session; no server imports or supplied key mapping."""
import csv
import json
from collections import Counter
from math import gcd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
try:
    from common import ALPHA, ENGLISH_FREQ, affine_decrypt, chi_squared, egcd_steps
except ModuleNotFoundError:
    from .common import ALPHA, ENGLISH_FREQ, affine_decrypt, chi_squared, egcd_steps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'


def dearmor(text):
    text = text.replace(' ', '')
    assert len(text) % 2 == 0
    pairs = [(ord(text[i])-65, ord(text[i+1])-65) for i in range(0, len(text), 2)]
    assert all(0 <= hi < 16 and 0 <= lo < 16 for hi, lo in pairs)
    return bytes((hi << 4) | lo for hi, lo in pairs).decode('utf-8')


def main():
    rows = list(csv.DictReader((ROOT/'ciphertexts.csv').open(encoding='utf-8')))
    results, frequencies, decrypted, proof = [], [], [], []
    fig, axes = plt.subplots(5, 1, figsize=(11, 17), constrained_layout=True)
    for session in range(1, 6):
        group = [r for r in rows if int(r['session']) == session]
        cipher = next(r['ciphertext'] for r in group if r['field'] == 'ciphertext')
        ranked = sorted((chi_squared(affine_decrypt(cipher,a,b)), a,b)
                        for a in range(26) if gcd(a,26)==1 for b in range(26))
        score,a,b = ranked[0]
        _, inverse, euclid = egcd_steps(a,26)
        plain = affine_decrypt(cipher,a,b)
        counts = Counter(c for c in cipher if c in ALPHA); n=sum(counts.values())
        pc = Counter(c for c in plain if c in ALPHA)
        for c in ALPHA:
            frequencies.append({'session':session,'letter':c,'cipher_count':counts[c],
                'cipher_percent':round(100*counts[c]/n,4),
                'decrypted_percent':round(100*pc[c]/n,4),'english_percent':ENGLISH_FREQ[c]})
        top=counts.most_common(6)
        ce,ct=(4*a+b)%26,(19*a+b)%26
        lines=[f'SESSION {session}: {n} ciphertext letters; mood is not used for recovery.',
               'Most frequent ciphertext letters: '+str(top),
               'Test all 312 valid Affine candidates; rank decrypted English by chi-squared.',
               'Leading candidates (chi-squared, a, b): '+str(ranked[:5]),
               f'Winning mapping: E -> {ALPHA[ce]}, T -> {ALPHA[ct]}.',
               f'4a+b = {ce} (mod 26); 19a+b = {ct} (mod 26).',
               f'Subtraction gives 15a = {(ct-ce)%26} (mod 26).',
               '26 = 1*15+11; 15 = 1*11+4; 11 = 2*4+3; 4 = 1*3+1.',
               'Back substitution: 1 = 7*15 - 4*26; inverse(15) = 7.',
               f'a = 7*{(ct-ce)%26} mod 26 = {a}; b = {ce}-4*{a} mod 26 = {b}.',
               f'gcd({a},26)=1. Extended Euclid for decryption:']+euclid+[
               f'inverse(a)={inverse}; {a}*{inverse} = {(a*inverse)//26}*26 + 1.',
               f'D(y) = {inverse}*(y-{b}) mod 26.',
               'English E/T mappings are candidate hypotheses, not guaranteed rank-1/rank-2 identities.',
               'Independent checks: decoded UTF-8 request fields and re-encryption equality.']
        for r in group:
            text=affine_decrypt(r['ciphertext'],a,b)
            if r['field']!='ciphertext':text=dearmor(text)
            decrypted.append({'session':session,'direction':r['direction'],'field':r['field'],'plaintext':text})
        reencrypted=''.join(ALPHA[(a*(ord(c)-65)+b)%26] if c in ALPHA else c for c in plain)
        assert reencrypted==cipher
        results.append({'session':session,'a':a,'b':b,'a_inverse':inverse,'chi_squared':score,
                        'runner_up_chi_squared':ranked[1][0],'top5':ranked[:5],
                        'cipher_letters':n,'plaintext':plain,'reencryption_matches':True})
        proof.extend(lines+[''])
        ax=axes[session-1]; x=list(range(26))
        ax.bar([v-.2 for v in x],[100*counts[c]/n for c in ALPHA],width=.4,label='Ciphertext',color='#31688e')
        ax.bar([v+.2 for v in x],[ENGLISH_FREQ[c] for c in ALPHA],width=.4,label='English reference',color='#d99435')
        ax.set_xticks(x,ALPHA);ax.set_ylabel('Frequency (%)');ax.set_title(f'Session {session}: ciphertext vs English');ax.legend(fontsize=8)
        chart,cax=plt.subplots(figsize=(11,3.5))
        cax.bar([v-.2 for v in x],[100*counts[c]/n for c in ALPHA],width=.4,label='Ciphertext',color='#31688e')
        cax.bar([v+.2 for v in x],[ENGLISH_FREQ[c] for c in ALPHA],width=.4,label='English reference',color='#d99435')
        cax.set_xticks(x,ALPHA,fontsize=11);cax.set_ylabel('Frequency (%)',fontsize=12)
        cax.set_title(f'Session {session}: captured ciphertext vs English',fontsize=14)
        cax.legend(fontsize=11);chart.tight_layout()
        chart.savefig(OUT/f'session_{session}_frequency.png',dpi=180);plt.close(chart)
    fig.savefig(OUT/'frequency_by_session.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.5));x=list(range(26))
    total=Counter(c for result in results for c in result['plaintext'] if c in ALPHA);n=sum(total.values())
    ax.bar(x,[100*total[c]/n for c in ALPHA],label='Recovered English',color='#2b7b70')
    ax.plot(x,[ENGLISH_FREQ[c] for c in ALPHA],label='English reference',color='#b35b35',marker='o')
    ax.set_xticks(x,ALPHA);ax.set_ylabel('Frequency (%)');ax.set_title('Recovered replies: English frequency check');ax.legend();fig.tight_layout()
    fig.savefig(OUT/'decrypted_vs_english.png',dpi=180);plt.close(fig)
    for filename,data in [('frequency_table.csv',frequencies),('decrypted.csv',decrypted)]:
        with (OUT/filename).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    (OUT/'recovered_keys.json').write_text(json.dumps(results,indent=2))
    (OUT/'key_recovery_proof.txt').write_text('\n'.join(proof))
    (OUT/'decrypted_sessions.txt').write_text('\n\n'.join(f"Session {r['session']} / {r['field']}\n{r['plaintext']}" for r in decrypted))
    print('Recovered and decrypted all five sessions; 312 candidates tested per session.')


if __name__=='__main__':main()
