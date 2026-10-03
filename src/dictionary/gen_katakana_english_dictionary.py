"""Build reference-derived kana/English tokens with conservative noun costs."""
import argparse
from pathlib import Path


def hiragana(text):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


def generate(mappings, dictionaries, noun_id):
    existing = set()
    bases = {}
    keys = {key for key, _ in mappings}
    for lines in dictionaries:
        for line in lines:
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 5 or fields[0] not in keys:
                continue
            key, lid, rid, cost, value = fields[:5]
            existing.add((key, value))
            if hiragana(value) == key:
                token = (int(cost), int(lid), int(rid))
                if key not in bases or token < bases[key]:
                    bases[key] = token
    for key, value in sorted(set(mappings)):
        if (key, value) in existing:
            continue
        # Reuse the native loanword's POS; keep it above the new English spelling.
        cost, lid, rid = bases.get(key, (6500, noun_id, noun_id))
        yield f"{key}\t{lid}\t{rid}\t{min(cost + 2500, 32767)}\t{value}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True)
    parser.add_argument("--id_def", required=True)
    parser.add_argument("--dictionary_txts", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    mappings = []
    for input_path in args.input:
        mappings.extend(
            tuple(line.rstrip().split("\t")) for line in
            Path(input_path).read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#"))
    noun_id = next(int(line.split()[0]) for line in
                   Path(args.id_def).read_text(encoding="utf-8").splitlines()
                   if line.split()[1] == "名詞,一般,*,*,*,*,*")
    # Open one source at a time rather than keeping the full OSS corpus in memory.
    def dictionaries():
        for path in args.dictionary_txts:
            with open(path, encoding="utf-8") as source:
                yield source
    with open(args.output, "w", encoding="utf-8", newline="\n") as output:
        output.writelines(generate(mappings, dictionaries(), noun_id))


if __name__ == "__main__":
    main()
