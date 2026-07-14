"""Script untuk menghasilkan fallback_phrases.json: memastikan frasa 2-3 kata saja."""

import json
import os
import random
from collections import defaultdict

FALLBACK_PATH = os.path.join('data', 'fallback_phrases.json')


def count_words(text):
    return len(text.split())


def generate(target_total=5000):
    os.makedirs('data', exist_ok=True)
    categories = {
        'agreement': (['Haha','Wkwk','Iya','Setuju','Bener','Yup','Betul','Sip','Mantap'],
                      ['iya','setuju','bener','betul','sama','sepakat','oke'],
                      ['','banget','bro','nih']),
        'humor': (['Wkwk','Haha','Njir','Ngakak','Hahaha','Gokil'],
                  ['kocak','gokil','gila','parah','konyol','absurd'],
                  ['','banget','bro']),
        'question': (['Eh','Woi','Asli','Halo'],
                     ['apa','gimana','kenapa','siapa','dimana','kapan','kok'],
                     ['','nih','ya']),
        'support': (['Semangat','Kuat','Bisa','Ayo','Sikat'],
                    ['bro','teman','sobat','kalian','kita'],
                    ['','ya']),
        'surprise': (['Wah','Astaga','Waduh','Gila'],
                     ['beneran','serius','lho','gak nyangka'],
                     ['','!']),
        'opening': (['Woi','Halo','Gas','Yo','Siapa'],
                    ['ada','apa','ide','cerita','lagi'],
                    ['','nih','?']),
        'smalltalk': (['Eh','Hmm','Hehe','Oh','Oke'],
                      ['lagi','makan','ngopi','kerja','libur','nongkrong'],
                      ['','ya','?'])
    }
    out = defaultdict(list)
    per_cat = max(300, target_total//len(categories))
    for cat, parts in categories.items():
        pref, core, suff = parts
        combos = set()
        attempts = 0
        while len(combos) < per_cat and attempts < per_cat*20:
            p = random.choice(pref).strip()
            c = random.choice(core).strip()
            s = random.choice(suff).strip()
            forms = []
            if p and c:
                forms.append(f"{p} {c}".strip())
            if c and s:
                forms.append(f"{c} {s}".strip())
            if p and c and s:
                forms.append(f"{p} {c} {s}".strip())
            if not forms:
                attempts += 1
                continue
            phrase = random.choice(forms)
            phrase = phrase.replace(' ?', '?').replace(' !','!')
            wc = count_words(phrase)
            if 2 <= wc <= 3:
                combos.add(phrase)
            attempts += 1
        out[cat] = sorted(combos)
    # Flatten and ensure total
    all_phrases = []
    for cat, lst in out.items():
        for p in lst:
            all_phrases.append({'category': cat, 'text': p})
    core_pool = [item['text'] for item in all_phrases]
    while len(all_phrases) < target_total:
        a = random.choice(core_pool) if core_pool else 'Iya bro'
        b = random.choice(core_pool) if core_pool else 'Siap ya'
        parts_a = a.split()
        parts_b = b.split()
        candidate_words = (parts_a + parts_b)[:3]
        candidate = ' '.join(candidate_words)
        if 2 <= count_words(candidate) <= 3 and candidate not in [x['text'] for x in all_phrases]:
            all_phrases.append({'category': 'mixed', 'text': candidate})
        else:
            alternative = (a.split()[0] + ' ' + (b.split()[0] if len(b.split())>0 else 'ya')).strip()
            if 2 <= count_words(alternative) <=3 and alternative not in [x['text'] for x in all_phrases]:
                all_phrases.append({'category': 'mixed', 'text': alternative})
    grouped = {}
    for item in all_phrases:
        grouped.setdefault(item['category'], []).append(item['text'])
    with open(FALLBACK_PATH, 'w', encoding='utf-8') as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)
    print(f"Generated {sum(len(v) for v in grouped.values())} phrases into {FALLBACK_PATH}")


if __name__ == '__main__':
    generate(5000)
