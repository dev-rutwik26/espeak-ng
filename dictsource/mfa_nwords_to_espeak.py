"""
mfa_nwords_to_espeak.py — MFA IPA → espeak-ng for normal English words
                          with authentic Indian English phonology (OED model)

Key IndE rules applied:
  • æ → a     (no trap-bath split in IndE)
  • ə stays @  (schwa stays schwa — NOT converted to open a)
  • θ → t[    (dental stop, NOT fricative: "think" → /t̪ɪŋk/)
  • ð → d[    (dental stop: "the" → /d̪ɪ/)
  • v,w,ʋ → v (merged labiodental /ʋ/)
  • ʒ → dZ    (leisure → /liːdʒər/ in IndE)
  • ŋ (final) → Ng  (IndE: "sing" always /sɪŋɡ/)
  • Stress: OED syllable-weight rules (light/heavy/extra-heavy)

Usage:
    python mfa_nwords_to_espeak.py input.txt              # stdout
    python mfa_nwords_to_espeak.py input.txt output.txt   # file
    python mfa_nwords_to_espeak.py input.txt out.txt --dedup  # one per word
"""

import sys

# ── IPA → espeak-ng phoneme map (Indian English common words) ─────────────────
IPA_TO_ESPEAK = {
    # SHORT VOWELS
    "ɪ":  "I",    # KIT    — kit, bit
    "ɛ":  "E",    # DRESS  — bed, press
    "e":  "E",    # DRESS variant
    "æ":  "a",    # TRAP   — IndE: open /a/, no trap-bath split (cat, trap)
    "ɒ":  "O",    # LOT    — lot, not
    "ʌ":  "@",    # STRUT  — cup, strut
    "ʊ":  "U",    # FOOT   — foot, put
    "ə":  "@",    # schwa  — STAYS SCHWA (biggest fix vs. proper noun script)
    "ɐ":  "@",    # near-open central → schwa
    "ɨ":  "I",    # close central unrounded
    "ɘ":  "@",    # close-mid central → schwa
    "ɜ":  "3:",   # NURSE short

    # LONG VOWELS
    "iː": "i:",   # FLEECE — see, fleece
    "i":  "i:",   # HAPPY  — IndE: happy is long (/iː/)
    "ɑ":  "A:",   # PALM short variant
    "ɑː": "A:",   # BATH/PALM — father, bath (IndE uses long open /aː/)
    "aː": "A:",   # long open variant
    "a":  "a",    # open front — comma, TRAP in IndE
    "ɔ":  "O",    # THOUGHT/LOT — IndE often merges these
    "ɔː": "O:",   # THOUGHT long — law, north
    "ɒː": "O:",   # CLOTH long variant
    "uː": "u:",   # GOOSE — food, goose
    "u":  "u:",   # GOOSE variant (IndE keeps full /uː/)
    "ʉ":  "u:",   # close central rounded
    "ʉː": "u:",
    "ɜː": "3:",   # NURSE — word, nurse (IndE rhotic variety)
    "eː": "eI",   # FACE  — IndE monophthong /eː/
    "oː": "oU",   # GOAT  — IndE monophthong /oː/
    "o":  "oU",   # GOAT variant
    "ɛː": "eI",   # SQUARE/FACE area

    # DIPHTHONGS (IndE: 2nd element not as weak as BrE)
    "aɪ": "aI",   "aj": "aI",   # PRICE
    "aʊ": "aU",   "aw": "aU",   # MOUTH
    "ɔɪ": "OI",   "ɔj": "OI",   # CHOICE
    "eɪ": "eI",                  # FACE (diphthong variant)
    "oʊ": "oU",                  # GOAT (diphthong variant)
    "ɪə": "I@",                  # NEAR
    "ɛə": "E@",                  # SQUARE (diphthong variant)

    # STOPS — retroflex via ph_rutwik, no map change needed
    "p":  "p",  "b":  "b",
    "t":  "t",  "ʈ":  "t",   # → retroflex ʈ via ph_rutwik
    "d":  "d",  "ɖ":  "d",   # → retroflex ɖ via ph_rutwik
    "t̪":  "t[", "d̪":  "d[",  # dental (from θ/ð MFA output)
    "k":  "k",  "ɡ":  "g",   "g": "g",
    "ʔ":  "",                 # glottal stop — drop

    # Aspirated (MFA may output these)
    "pʰ": "p", "tʰ": "t", "kʰ": "k",
    "bʱ": "b", "dʱ": "d", "gʱ": "g",

    # AFFRICATES
    "tʃ": "tS",  "dʒ": "dZ",
    "c":  "k",  "ɟ":  "g",  "ɟʷ": "dZ",

    # FRICATIVES — Note the critical IndE rules:
    "f":  "f",
    "θ":  "t[",  # THIN  → dental stop /t̪/ in IndE (NOT fricative)
    "ð":  "d[",  # THE   → dental stop /d̪/ in IndE (NOT fricative)
    "s":  "s",   "z": "z",
    "ʃ":  "S",
    "ʒ":  "dZ",  # MEASURE → /dʒ/ in IndE (per OED model)
    "h":  "h",
    "x":  "x",   "ç": "S",   "ɣ": "x",

    # NASALS
    "m":  "m",  "n":  "n",
    "ɲ":  "n",  "ɳ":  "n",
    "ɱ":  "m",  # labiodental nasal (before f/v: triumph, inflorescence) → m
    "ŋ":  "N",  # NOTE: word-final ŋ → Ng handled below

    # LATERALS — always CLEAR /l/ in IndE (never dark)
    "l":  "l",  "ɭ":  "l",  "ʎ":  "l",

    # RHOTICS — IndE rhotic: tap/trill (our ph_rutwik r)
    "r":  "r",  "ɾ":  "r",  "ɽ":  "r",  "ɹ":  "r",

    # APPROXIMANTS
    "j":  "j",
    "w":  "v",   # /w/ → labiodental /ʋ/ in IndE
    "v":  "v",   # /v/ → /ʋ/ in IndE (merged)
    "ʋ":  "v",   # labiodental approximant

    # PALATALIZED (MFA diacritics — strip palatalization)
    "bʲ":"b","pʲ":"p","mʲ":"m","nʲ":"n","fʲ":"f","vʲ":"v",
    "dʲ":"d","tʲ":"t","sʲ":"s","zʲ":"z","lʲ":"l","rʲ":"r",
    "ɡʲ":"g","kʲ":"k","ʈʲ":"t","ɖʲ":"d",

    # LABIALIZED
    "ɡʷ":"gw", "kʷ":"kw", "cʷ":"kw", "ʈʷ":"tw",
    "pʷ": "p",  # labialized p (French loanwords: poisson, pueblo) → p
}

LONG_VOWELS = {"ɑː","aː","iː","uː","eː","oː","ɜː","ʉː","ɔː","ɒː","ɛː"}
VOWEL_SET   = {
    "ɪ","ɛ","e","æ","ɒ","ʌ","ʊ","ə","ɐ","ɨ","ɘ","ɜ",
    "iː","i","ɑ","ɑː","aː","a","ɔ","ɔː","ɒː","uː","u","ʉ","ʉː",
    "ɜː","eː","oː","o","ɛː",
    "aɪ","aj","aʊ","aw","ɔɪ","ɔj","eɪ","oʊ","ɪə","ɛə",
}

# Tokens MFA may split that should be compound
MERGES = {("t","ʃ"): "tʃ", ("d","ʒ"): "dʒ", ("t","s"): "ts", ("d","z"): "dz"}

# Suffix sequence corrections — MFA often gets these wrong
SUFFIX_FIXES = [
    # -ture: MFA gives [ʈ,ʊ,ə] but should be [tʃ,ə]
    (["ʈ","ʊ","ə"], ["tʃ","ə"]),
    (["t","ʊ","ə"], ["tʃ","ə"]),
    # -tion: MFA sometimes gives [t,ɪ,ɒ,n] but should be [ʃ,ə,n]
    (["t","ɪ","ɒ","n"], ["ʃ","ə","n"]),
]

def fix_suffix_sequences(tokens):
    for bad, good in SUFFIX_FIXES:
        n = len(bad)
        if tokens[-n:] == bad:
            tokens = tokens[:-n] + good
    return tokens

def merge_tokens(tokens):
    out, i = [], 0
    while i < len(tokens):
        if i+1 < len(tokens) and (tokens[i], tokens[i+1]) in MERGES:
            out.append(MERGES[(tokens[i], tokens[i+1])])
            i += 2
        else:
            out.append(tokens[i]); i += 1
    return out

def coda_count(tokens, v_idx):
    """Consonants between this vowel and next vowel (syllable coda)."""
    c = 0
    for j in range(v_idx+1, len(tokens)):
        if tokens[j] in VOWEL_SET: break
        c += 1
    return c

def syl_weight(tokens, v_idx):
    """OED IndE: light=(C)V, heavy=(C)V: or (C)VC, extra_heavy=(C)V:C or (C)VCC"""
    is_long = tokens[v_idx] in LONG_VOWELS
    coda    = coda_count(tokens, v_idx)
    if is_long and coda >= 1: return "extra_heavy"
    if is_long or  coda >= 1: return "heavy"
    return "light"

def find_stress(tokens):
    """
    OED IndE stress (syllable-weight based):
      1 syl  → stress it
      2 syls → 1st; unless 2nd is extra-heavy → stress 2nd
      3 syls → middle if heavy/extra-heavy; else 1st
      4+ syls → antepenultimate
    """
    vidxs = [i for i,t in enumerate(tokens) if t in VOWEL_SET]
    n = len(vidxs)
    if n == 0: return 0
    if n == 1: return vidxs[0]
    weights = [syl_weight(tokens, v) for v in vidxs]
    if n == 2:
        return vidxs[1] if weights[1] == "extra_heavy" else vidxs[0]
    if n == 3:
        return vidxs[1] if weights[1] in ("heavy","extra_heavy") else vidxs[0]
    return vidxs[-3]  # antepenultimate for 4+ syllables

def convert_line(line):
    parts = line.strip().split('\t')
    if len(parts) != 2: return None

    word   = parts[0].strip()
    tokens = [t for t in parts[1].strip().split(' ') if t]
    tokens = merge_tokens(tokens)
    tokens = fix_suffix_sequences(tokens)

    stress_idx = find_stress(tokens)
    out = []
    for i, ipa in enumerate(tokens):
        is_vowel = ipa in VOWEL_SET
        if is_vowel and i == stress_idx:
            out.append("'")

        ph = IPA_TO_ESPEAK.get(ipa)
        if ph is None:
            print(f"Warning: unmapped '{ipa}' in '{word}'", file=sys.stderr)
            continue

        # IndE: word-final /ŋ/ → /ŋɡ/ ("sing" = /sɪŋɡ/)
        if ipa == "ŋ" and i == len(tokens)-1:
            out.append("N"); out.append("g")
            continue

        out.append(ph)

    return f"{word}\t{''.join(out)}"

def process(in_file, out_file=None, dedup=True):
    out   = open(out_file, 'w', encoding='utf-8') if out_file else sys.stdout
    seen  = set()
    count = 0
    with open(in_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            result = convert_line(line)
            if not result: continue
            if dedup:
                word = result.split('\t')[0]
                if word in seen: continue
                seen.add(word)
            out.write(result + '\n')
            count += 1
    if out_file:
        out.close()
        print(f"Converted {count} entries → {out_file}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mfa_nwords_to_espeak.py <input.txt> [output.txt] [--dedup]")
        sys.exit(1)
    in_f  = sys.argv[1]
    out_f = next((a for a in sys.argv[2:] if not a.startswith('--')), None)
    dedup = '--dedup' in sys.argv
    process(in_f, out_f, dedup=dedup)
