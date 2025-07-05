import json
import csv
import re
import unidecode
import smartypants
import spacy
from spacy.util import compile_infix_regex, compile_prefix_regex, compile_suffix_regex, filter_spans
from spacy.tokens import Doc, Span
from spacy.matcher import PhraseMatcher

from bs4 import BeautifulSoup


def latin2shaw(text):
    with open("static/readlex_converter.json", 'r', encoding="utf-8") as file:
        json_data = file.read()

    readlex_dict: dict[str, list[dict[str, str]]] = json.loads(json_data)

    # Categories of letters that determine how a following 's is pronounced
    s_follows: set[str] = {"𐑐", "𐑑", "𐑒", "𐑓", "𐑔"}
    uhz_follows: set[str] = {"𐑕", "𐑖", "𐑗", "𐑟", "𐑠", "𐑡"}
    z_follows: set[str] = {"𐑚", "𐑛", "𐑜", "𐑝", "𐑞", "𐑙", "𐑤", "𐑥", "𐑯", "𐑸", "𐑹", "𐑺", "𐑻", "𐑼", "𐑽"}
    consonants = set.union(s_follows, uhz_follows, z_follows)
    # vowels = {"𐑦", "𐑰", "𐑧", "𐑱", "𐑨", "𐑲", "𐑩", "𐑳", "𐑪", "𐑴", "𐑫", "𐑵", "𐑬", "𐑶", "𐑭", "𐑷", "𐑾", "𐑿"}
    # The following are never final other than in initialisms: "𐑣", "𐑢", "𐑘", "𐑮".

    # Contractions that need special treatment since the separate words are not as they appear in the dictionary
    contraction_start: dict[str, str] = {"ai": "𐑱", "ca": "𐑒𐑭", "do": "𐑛𐑴", "does": "𐑛𐑳𐑟", "did": "𐑛𐑦𐑛", "sha": "𐑖𐑭",
                                         "wo": "𐑢𐑴",
                                         "y'": "𐑘"}
    contraction_end: dict[str, str] = {"n't": "𐑯𐑑", "all": "𐑷𐑤", "'ve": "𐑝", "'ll": "𐑤", "'m": "𐑥", "'d": "𐑛",
                                       "'re": "𐑼"}

    # Common prefixes and suffixes used in new coinings
    prefixes: dict[str, str] = {"anti": "𐑨𐑯𐑑𐑦",
                                "counter": "𐑒𐑬𐑯𐑑𐑼",
                                "de": "𐑛𐑰",
                                "dis": "𐑛𐑦𐑕",
                                "esque": "𐑧𐑕𐑒",
                                "hyper": "𐑣𐑲𐑐𐑼",
                                "hypo": "𐑣𐑲𐑐𐑴",
                                "mega": "𐑥𐑧𐑜𐑩",
                                "meta": "𐑥𐑧𐑑𐑩",
                                "micro": "𐑥𐑲𐑒𐑮𐑴",
                                "multi": "𐑥𐑳𐑤𐑑𐑦",
                                "mis": "𐑥𐑦𐑕",
                                "neuro": "𐑯𐑘𐑫𐑼𐑴",
                                "non": "𐑯𐑪𐑯",
                                "o'er": "𐑴𐑼",
                                "out": "𐑬𐑑",
                                "over": "𐑴𐑝𐑼",
                                "poly": "𐑐𐑪𐑤𐑦",
                                "post": "𐑐𐑴𐑕𐑑",
                                "pre": "𐑐𐑮𐑰",
                                "pro": "𐑐𐑮𐑴",
                                "pseudo": "𐑕𐑿𐑛𐑴",
                                "re": "𐑮𐑰",
                                "sub": "𐑕𐑳𐑚",
                                "super": "𐑕𐑵𐑐𐑼",
                                "ultra": "𐑳𐑤𐑑𐑮𐑩",
                                "un": "𐑳𐑯",
                                "under": "𐑳𐑯𐑛𐑼"
                                }
    suffixes: dict[str, str] = {"able": "𐑩𐑚𐑩𐑤",
                "bound": "𐑚𐑬𐑯𐑛",
                "ful": "𐑓𐑩𐑤",
                "hood": "𐑣𐑫𐑛",
                "ish": "𐑦𐑖",
                "ism": "𐑦𐑟𐑩𐑥",
                "less": "𐑤𐑩𐑕",
                "like": "𐑤𐑲𐑒",
                "ness": "𐑯𐑩𐑕"
                }
    affixes: dict[str, str] = prefixes | suffixes

    # Words that sometimes change spelling before 'to'
    have_to: dict[str, str] = {"have": "𐑣𐑨𐑓", "has": "𐑣𐑨𐑕"}
    vbd_to: dict[str, str] = {"used": "𐑿𐑕𐑑", "unused": "𐑳𐑯𐑿𐑕𐑑", "supposed": "𐑕𐑩𐑐𐑴𐑕𐑑"}
    before_to: dict[str, str] = have_to | vbd_to

    # Suffixes that follow numerals in ordinal numbers
    ordinal_suffixes: dict[str, str] = {"st": "𐑕𐑑", "nd": "𐑯𐑛", "rd": "𐑮𐑛", "th": "𐑔", "s": "𐑟"}

    # Load spaCy, excluding pipeline components that are not required
    nlp = spacy.load("en_core_web_sm", exclude=["parser", "lemmatizer", "textcat"])

    # Customise the spaCy tokeniser to ensure that initial and final dashes and dashes between words aren't stuck to one
    # of the surrounding words
    # Prefixes
    spacy_prefixes: list[str] = nlp.Defaults.prefixes + [r'''^[-–—]+''',]
    prefix_regex = compile_prefix_regex(spacy_prefixes)
    nlp.tokenizer.prefix_search = prefix_regex.search
    # Infixes
    spacy_infixes: list[str] = nlp.Defaults.infixes + [r'''[.,?!:;\-–—"~\(\)\[\]]+''',]
    infix_regex = compile_infix_regex(spacy_infixes)
    nlp.tokenizer.infix_finditer = infix_regex.finditer
    # Suffixes
    spacy_suffixes: list[str] = nlp.Defaults.suffixes + [r'''[-–—]+$''',]
    suffix_regex = compile_suffix_regex(spacy_suffixes)
    nlp.tokenizer.suffix_search = suffix_regex.search

    def add_span(matcher, doc, i, matches):
        match_id, start, end = matches[i]

    # Define the phrase to match
    with open("static/readlex_converter_phrases.json", "r", newline="") as f:
        reader = csv.reader(f)
        phrases = [row[0] for row in reader if row]
    phrase_patterns: list[Doc] = [nlp.make_doc(phrase) for phrase in phrases]
    phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    phrase_matcher.add("phrases", phrase_patterns, on_match=add_span)

    namer_dot_ents: set[str] = {"PERSON", "FAC", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "WORK_OF_ART", "LAW"}

    def tokenise(text: str) -> spacy.tokens.Doc:
        # Tokenise and tag the text using spaCy as doc

        doc = nlp(text)
        phrase_matches = phrase_matcher(doc)
        phrase_spans: list[Span] = []
        for match_id, start, end in phrase_matches:
            span = Span(doc, start, end, label=match_id)
            phrase_spans.append(span)

        filtered_spans = filter_spans(phrase_spans)

        with doc.retokenize() as retokenizer:
            for span in filtered_spans:
                retokenizer.merge(span)

        # Expand person entities to include titles and take initial 'the' out of entity names
        titles: set[str] = {
            "archbishop",
            "archdeacon",
            "baron",
            "baroness",
            "bishop",
            "captain",
            "count",
            "countess",
            "cpt",
            "dame",
            "deacon",
            "doctor",
            "dr.",
            "dr",
            "duchess",
            "duke",
            "earl",
            "emperor",
            "empress",
            "gov.",
            "gov",
            "governor",
            "justice",
            "king",
            "lady",
            "lord",
            "marchioness",
            "marquess",
            "marquis",
            "miss",
            "missus",
            "mister",
            "mistress",
            "mr.",
            "mr",
            "mrs.",
            "mrs",
            "ms.",
            "ms",
            "mx.",
            "mx",
            "pope",
            "pres.",
            "pres",
            "president",
            "prince",
            "princess",
            "prof.",
            "prof",
            "professor",
            "queen",
            "rev.",
            "rev",
            "reverend",
            "saint",
            "sen.",
            "sen",
            "senator",
            "sir",
            "st.",
            "st",
            "viscount",
            "viscountess"
        }
        new_ents: list[Span] = []
        for ent in doc.ents:
            # Only check for title if it's a person and not the first token
            if ent.label_ == "PERSON" and ent.start != 0:
                prev_token = doc[ent.start - 1]
                if prev_token.lower_ in titles:
                    new_ent = Span(doc, ent.start - 1, ent.end, label=ent.label)
                    new_ents.append(new_ent)
                else:
                    new_ents.append(ent)
            elif ent.label_ in namer_dot_ents:
                if doc[ent.start].lower_ == "the":
                    new_ent = Span(doc, ent.start + 1, ent.end, label=ent.label)
                    new_ents.append(new_ent)
                else:
                    new_ents.append(ent)
            else:
                new_ents.append(ent)

        filtered_ents = filter_spans(new_ents)
        doc.ents = tuple(filtered_ents)

        return doc

    def convert(doc: spacy.tokens.Doc) -> str:
        # Apply a series of tests to each token to determine how to Shavianise it.
        text_split_shaw: str = ""

        for token in doc:

            # Leave HTML tags unchanged
            if token.tag_ == "HTML":
                text_split_shaw += token.text

            # Convert contractions
            if token.lower_ in contraction_start and token.i < len(doc) - 1 and doc[
                token.i + 1].lower_ in contraction_end:
                text_split_shaw += contraction_start[token.lower_]
            elif token.lower_ in contraction_end:
                prefix: str = "𐑩" if token.lower_ != "𐑼" and text_split_shaw and text_split_shaw[
                    -1] in consonants else ""
                text_split_shaw += prefix + contraction_end[token.lower_] + token.whitespace_

            # Convert possessive 's
            elif token.lower_ == "'s":
                suffix: str = "𐑕" if text_split_shaw[-1] in s_follows else "𐑩𐑟" if text_split_shaw[
                                                                                       -1] in uhz_follows else "𐑟"
                text_split_shaw += suffix + token.whitespace_

            # Convert possessive '
            elif token.lower_ == "'" and token.tag_ == "POS":
                text_split_shaw += token.whitespace_

            # Convert verbs that change pronunciation before 'to', e.g. 'have to', 'used to', 'supposed to'
            elif token.lower_ in before_to and token.i < len(doc) - 1 and doc[token.i + 1].lower_ == "to":
                # 'have' only changes pronunciation where 'have to' means 'must'
                if token.lower_ in have_to and doc[token.i + 2].tag_ in ["VB", "VBP"]:
                    text_split_shaw += have_to[token.lower_] + token.whitespace_
                # 'used', 'supposed' etc. only change pronunciation in the past tense, not past participle
                elif token.lower_ in vbd_to and token.tag_ in ["VBD", "VBN", "."]:
                    text_split_shaw += vbd_to[token.lower_] + token.whitespace_

            # Match ordinal numbers represented by a numeral and a suffix
            elif re.fullmatch(r"([0-9]+(?:[, .]?[0-9]+)*)(st|nd|rd|th|s)", token.lower_):
                number, number_suffix = re.match(r"([0-9]+(?:[, .]?[0-9]+)*)(st|nd|rd|th|s)", token.lower_).groups()
                text_split_shaw += number + ordinal_suffixes[number_suffix] + token.whitespace_

            # Loop through the words in the ReadLex and look for matches, and only apply the namer dot to the first word
            # in a name (or not at all for initialisms marked with ⸰)
            elif token.lower_ in readlex_dict:
                for i in readlex_dict.get(token.lower_, []):
                    # Match the part of speech for heteronyms
                    if i["tag"] == token.tag_:
                        prefix: str = "·" if token.ent_iob_ == "B" and token.ent_type_ in namer_dot_ents and not i[
                            "Shaw"].startswith("⸰") else ""
                        text_split_shaw += prefix + i["Shaw"] + token.whitespace_
                        break

                    # For any proper nouns not in the ReadLex, match if an identical common noun exists
                    elif (i["tag"] in ["NN", "0"] and token.tag_ == "NNP") or (
                            i["tag"] in ["NNS", "0"] and token.tag_ == "NNPS"):
                        prefix = "·" if token.ent_iob_ == "B" and token.ent_type_ in namer_dot_ents and not i[
                            "Shaw"].startswith("⸰") else ""
                        text_split_shaw += prefix + i["Shaw"] + token.whitespace_
                        break

                    # Match words with only one pronunciation
                    elif i["tag"] == "0":
                        prefix = "·" if token.ent_iob_ == "B" and token.ent_type_ in namer_dot_ents and not i[
                            "Shaw"].startswith("⸰") else ""
                        text_split_shaw += prefix + i["Shaw"] + token.whitespace_
                        break

            # Apply additional tests where there is still no match
            else:
                found: bool = False
                constructed_warning: str = "⚠️"
                '''
                Try to construct a match using common prefixes and suffixes and include a warning symbol to aid proof
                reading
                '''
                for j in affixes:
                    if token.lower_.startswith(j) and j in prefixes:
                        prefix: str = prefixes[j]
                        suffix: str = ""
                        target_word: str = token.lower_[len(j):]
                    elif token.lower_.endswith(j) and j in suffixes:
                        prefix = ""
                        suffix = suffixes[j]
                        target_word = token.lower_[:-len(j)]
                    else:
                        continue
                    if target_word in readlex_dict:
                        found = True
                        for i in readlex_dict.get(target_word):
                            prefix = "·" if token.ent_iob_ == "B" and token.ent_type_ in namer_dot_ents and not \
                                i[
                                    "Shaw"].startswith("⸰") else prefix
                            text_split_shaw += prefix + i[
                                "Shaw"] + suffix + constructed_warning + token.whitespace_
                            break

                # Try to construct plurals if not expressly included in the ReadLex, e.g. plurals of proper names.
                if token.lower_.endswith("s"):
                    target_word = token.lower_[:-1]
                    if target_word in readlex_dict:
                        found = True
                        for i in readlex_dict.get(target_word):
                            suffix = "𐑕" if i["Shaw"][-1] in s_follows else "𐑩𐑟" if i["Shaw"][
                                                                                        -1] in uhz_follows else "𐑟"
                            prefix = "·" if token.ent_iob_ == "B" and token.ent_type_ in namer_dot_ents and not \
                                i[
                                    "Shaw"].startswith("⸰") else ""
                            text_split_shaw += prefix + i[
                                "Shaw"] + suffix + constructed_warning + token.whitespace_
                            break

                if found is not False:
                    continue
                # If there is still no match, do not convert the word
                if token.text.isalpha():
                    text_split_shaw += token.text + "✢" + token.whitespace_
                else:
                    text_split_shaw += token.text + token.whitespace_

        return text_split_shaw

    # Create the string that will contain the Shavianised text.
    text_shaw: str = ""

    # Split up the string to reduce the risk of spaCy exceeding memory limits
    if text.strip().casefold().startswith("<!doctype html"):
        style_pattern: str = r"(<style\b[^>]*>.*?</style>)"
        script_pattern: str = r"(<script\b[^>]*>.*?</script>)"
        html_pattern: str = r"(?!(?:<style[^>]*?>.*?</style>|<script[^>]*?>.*?</script>))(<.*?>)"
        html_patterns: str = f"{style_pattern}|{script_pattern}|{html_pattern}"
        text_split: list[str] = re.split(html_patterns, text, flags=re.DOTALL)
        for text_part in text_split:
            if text_part is None:
                pass
            elif re.fullmatch(style_pattern, text_part, flags=re.DOTALL) or re.fullmatch(
                    script_pattern, text_part, flags=re.DOTALL) or re.fullmatch(html_pattern, text_part,
                                                                                flags=re.DOTALL):
                text_shaw += text_part
            else:
                doc: spacy.tokens.Doc = tokenise(text_part)
                text_shaw += convert(doc)

        # Convert dumb quotes, double hyphens, etc. to their typographic equivalents
        text_shaw = smartypants.smartypants(text_shaw)
        # Convert curly quotes to angle quotes
        quotation_marks: dict[str, str] = {"&#8216;": "&lsaquo;", "&#8217;": "&rsaquo;", "&#8220;": "&laquo;", "&#8221;": "&raquo;"}
        for key, value in quotation_marks.items():
            text_shaw = text_shaw.replace(key, value)

    else:
        text = unidecode.unidecode(text)
        text = re.sub(r"(\S)(\[)", r"\1 \2", text)
        text = re.sub(r"](\S)", r"] \1", text)
        text_split: list[str] = text.splitlines()
        for i in text_split:
            if len(i) < 10000:
                doc: spacy.tokens.Doc = tokenise(i)
                text_shaw += convert(doc) + "\n"
        # Convert dumb quotes, double hyphens, etc. to their typographic equivalents
        text_shaw = smartypants.smartypants(text_shaw)
        quotation_marks: dict[str, str] = {"&#8216;": "&lsaquo;", "&#8217;": "&rsaquo;", "&#8220;": "&laquo;", "&#8221;": "&raquo;"}
        for key, value in quotation_marks.items():
            text_shaw = text_shaw.replace(key, value)
        text_shaw = str(BeautifulSoup(text_shaw, features="html.parser"))

    return text_shaw