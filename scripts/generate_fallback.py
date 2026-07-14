"""Script untuk menghasilkan fallback_phrases.json jika ingin dibuat secara terpisah.
Biasanya bot.py akan membuat file ini otomatis saat tidak ada.
"""

import json
import os
import random
from collections import defaultdict

FALLBACK_PATH = os.path.join('data', 'fallback_phrases.json')


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
                     ['','nih','?']),
        'support': (['Semangat','Kuat','Bisa','Ayo','Sikat'],
                    ['bro','teman','sobat','kalian','kita'],
                    ['','ya','!']),
        'surprise': (['Wah','Astaga','Waduh','Gila'],
                     ['beneran','serius','lho','ga nyangka'],
                     ['','!']),
        'opening': (['Woi','Halo','Gas','Yo','Siapa nih'],
                    ['ada yang','apa kabar','ada ide','ada cerita','lagi apa'],
                    ['','?','nih']),
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
        while len(combos) < per_cat and attempts < per_cat*10:
            p = random.choice(pref)
            c = random.choice(core)
            s = random.choice(suff)
            phrase = ' '.join([x for x in [p,c,s] if x]).strip()
            phrase = phrase.replace(' ?', '?').replace(' !','!')
            combos.add(phrase)
            attempts += 1
        out[cat] = sorted(combos)
    with open(FALLBACK_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Generated {sum(len(v) for v in out.values())} phrases into {FALLBACK_PATH}")


if __name__ == '__main__':
    generate(5000)
