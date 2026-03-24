"""
mfa_to_espeak.py  —  Convert MFA IPA output to espeak-ng rutwik_list format

Input format (tab-separated):
    word<TAB>ɑː dʒ ʊ n

Output format (espeak-ng rutwik_list):
    word    'A:dZUn

Usage:
    python mfa_to_espeak.py input_mfa_ipa.txt >> rutwik_list
    python mfa_to_espeak.py input_mfa_ipa.txt output_rutwik_list.txt
"""

import sys

# IPA → espeak-ng phoneme mapping
# Prioritizes Indian English phonological accuracy
IPA_TO_ESPEAK = {

    # === VOWELS ===
    "ɑ":  "a:",   # long open back — "arjun"
    "ɑː": "a:",   # long open back
    "a":  "a",    # open front — TRAP vowel in IndE
    "aː": "a:",
    "ə":  "aa",    # schwa mid-word → STRUT /ɐ/ (overridden at word-end, see below)
    "ɐ":  "V",    # near-open central
    "ɛ":  "E",    # DRESS — short e
    "e":  "eI",   # FACE — maps to monophthong eː in ph_rutwik
    "eː": "eI",
    "ɪ":  "I",    # KIT — short i
    "i":  "i:",   # FLEECE — long i
    "iː": "i:",
    "ʊ":  "u",    # FOOT — short u
    "u":  "u:",   # GOOSE — long u
    "uː": "u:",
    "ʉ":  "u:",   # close central rounded (Australian/Indian variant)
    "ʉː": "u:",
    "ɔ":  "O",    # THOUGHT
    "ɔː": "O:",
    "o":  "oU",   # GOAT — maps to monophthong oː in ph_rutwik
    "oː": "oU",
    "ʌ":  "V",    # STRUT
    "æ":  "a",    # TRAP — IndE uses open a
    "ɜ":  "3:",   # NURSE
    "ɜː": "3:",
    "ɨ":  "I",    # close central unrounded (some IndE variants)
    "ɘ":  "V",
    "ɒ":  "O",    # LOT vowel
    "ɒː": "O:",   # long LOT/THOUGHT
    "ɛː": "eI",   # long open-mid front (SQUARE) → maps to e:


    # === DIPHTHONGS ===
    "aɪ": "aI",
    "aʊ": "aU",
    "ɔɪ": "OI",
    "eɪ": "eI",   # FACE
    "oʊ": "oU",   # GOAT
    "aj": "aI",   # Alternate MFA format for PRICE
    "aw": "aU",   # Alternate MFA format for MOUTH
    "ɔj": "OI",   # Alternate MFA format for CHOICE


    # === STOPS — Indian English specific ===
    "p":  "p",
    "b":  "b",
    "t":  "t",    # alveolar → retroflex ʈ via ph_rutwik
    "ʈ":  "t",    # retroflex → goes to our t which is already ʈ
    "d":  "d",    # alveolar → retroflex ɖ via ph_rutwik
    "ɖ":  "d",    # retroflex → goes to our d which is already ɖ
    "t̪":  "t[",   # dental t
    "d̪":  "d[",   # dental d
    "k":  "k",
    "ɡ":  "g",
    "g":  "g",
    "ʔ":  "",     # glottal stop — drop it

    # === ASPIRATED STOPS (breathy) ===
    "pʰ": "p",    # aspirated p — approximated as p for now
    "tʰ": "t",    # aspirated t
    "kʰ": "k",    # aspirated k
    "bʱ": "b",    # breathy b (bh) — approximated
    "dʱ": "d",    # breathy d (dh)
    "gʱ": "g",    # breathy g (gh)

    # === AFFRICATES ===
    "tʃ": "tS",   # 'ch' as in "chai"
    "dʒ": "dZ",   # 'j' as in "jaya"
    "c":  "tS",   # palatal stop — map to affricate (e.g. prachi)
    "ɟ":  "dZ",   # voiced palatal stop
    "ɟʷ": "dZ",   # labialized palatal stop


    # === FRICATIVES ===
    "f":  "f",
    "v":  "v",
    "s":  "s",
    "z":  "z",
    "ʃ":  "S",    # 'sh' — very common in Indian names
    "ʒ":  "Z",
    "h":  "h",
    "x":  "x",    # velar fricative (kh in some names)
    "θ":  "T",    # dental fricative — rarely in Indian names
    "ð":  "D",
    "ç":  "S",    # palatal fricative → map to sh


    # === NASALS ===
    "m":  "m",
    "n":  "n",
    "ɳ":  "n",    # retroflex nasal — approximated as n
    "ɲ":  "n",    # palatal nasal
    "ŋ":  "N",    # velar nasal (ŋ)

    # === LATERALS ===
    "l":  "l",
    "ɭ":  "l",    # retroflex lateral — approximated as l
    "ʎ":  "l",    # palatal lateral (e.g. diwali final) — approximated as l

    # === RHOTICS ===
    "r":  "r",    # tap/trill → our ph_rutwik r (tap ɾ)
    "ɾ":  "r",    # tap
    "ɽ":  "r",    # retroflex flap
    "ɹ":  "r",    # approximant → we map to our tap r

    # === APPROXIMANTS ===
    "j":  "j",    # palatal approximant 'y'
    "w":  "w",    # labiovelar → merged to ʋ via voice file replace rule
    "ʋ":  "v",    # labiodental approximant — key in Indian names (Vikram, Vivek)

    # === PALATALIZED CONSONANTS ===
    # MFA outputs ʲ (palatalization superscript) before front vowels.
    # espeak handles coarticulation via the following front vowel — just strip it.
    "bʲ": "b",   # abhishek: bʲ → b
    "pʲ": "p",
    "mʲ": "m",
    "nʲ": "n",
    "fʲ": "f",
    "vʲ": "v",
    "dʲ": "d",
    "tʲ": "t",
    "sʲ": "s",
    "zʲ": "z",
    "lʲ": "l",
    "rʲ": "r",
    "ɡʲ": "g",
    "kʲ": "k",
    "ʈʲ": "t",    # palatalized retroflex t → strip palatalization

    # === LABIALIZED CONSONANTS ===
    # MFA outputs ʷ (labialization) for 'qu' and 'tw' names.
    # We must explicitly output the 'w' (which our voice maps to 'v') so it's not lost.
    "ɡʷ": "gw",   # guadalupe, nagulini
    "kʷ": "kw",   # miquel, quadre
    "cʷ": "kw",   # quince, quintyn (cʷ acts as kw here)
    "ʈʷ": "tw",   # twyla, twinkal (labialized retroflex t)
}

STRESS_MARK = "'"    # primary stress marker in espeak-ng


def find_stress_syllable(phones):
    """
    Since IPA format from MFA has no stress numbers,
    we apply a simple IndE heuristic:
    Stress the first long vowel, otherwise the first vowel.
    """
    long_vowel_markers = {"ɑː", "aː", "iː", "uː", "eː", "oː", "ɜː", "ʉː", "ɔː"}
    short_vowels = {"ɑ", "a", "ə", "ɐ", "ɛ", "e", "ɪ", "i", "ʊ", "u", "ʉ", "ɔ",
                    "o", "ʌ", "æ", "ɜ", "ɨ", "ɘ"}

    # First: try to find a long vowel
    for i, ph in enumerate(phones):
        if ph in long_vowel_markers:
            return i

    # Fallback: first short vowel
    for i, ph in enumerate(phones):
        if ph in short_vowels:
            return i

    return 0  # default to start


def convert_line(line):
    parts = line.strip().split('\t')
    if len(parts) != 2:
        return None

    word      = parts[0].strip()
    # split on spaces to get individual IPA tokens
    ipa_tokens = parts[1].strip().split(' ')

    # filter empties
    ipa_tokens = [t for t in ipa_tokens if t]

    stress_idx = find_stress_syllable(ipa_tokens)

    # Build espeak phoneme string
    espeak_out = []
    vocals_seen = 0
    vowel_set = {
        "ɑ","ɑː","a","aː","ə","ɐ","ɛ","e","eː","ɪ","i","iː",
        "ʊ","u","uː","ʉ","ʉː","ɔ","ɔː","o","oː","ʌ","æ","ɜ","ɜː",
        "ɨ","ɘ","aɪ","aʊ","ɔɪ","eɪ","oʊ","aj","aw","ɔj","ɒ","ɒː","ɛː"
    }

    for i, ipa in enumerate(ipa_tokens):
        is_vowel  = ipa in vowel_set
        is_final  = (i == len(ipa_tokens) - 1)

        if is_vowel:
            if i == stress_idx:
                espeak_out.append(STRESS_MARK)
            vocals_seen += 1

        espeak_ph = IPA_TO_ESPEAK.get(ipa)
        if espeak_ph is None:
            print(f"Warning: unmapped IPA '{ipa}' in word '{word}'", file=sys.stderr)
            continue

        # Rule: schwa in the last syllable of Indian names → open 'a', not 'V'
        # Covers absolute final (priya: -jə) AND pre-final consonant (kunal: -əl)
        is_in_last_syllable = (i >= len(ipa_tokens) - 2)
        if ipa == "ə" and is_in_last_syllable:
            espeak_ph = "a"

        espeak_out.append(espeak_ph)

    espeak_str = "".join(espeak_out)
    return f"{word}\t{espeak_str}"


def process(input_file, output_file=None):
    out = open(output_file, 'w', encoding='utf-8') if output_file else sys.stdout
    count = 0

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip() or line.startswith('#'):
                continue
            result = convert_line(line)
            if result:
                out.write(result + '\n')
                count += 1

    if output_file:
        out.close()
        print(f"Converted {count} entries → {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mfa_to_espeak.py <input_mfa_ipa.txt> [output_rutwik_list.txt]")
        sys.exit(1)

    in_file  = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else None
    process(in_file, out_file)
