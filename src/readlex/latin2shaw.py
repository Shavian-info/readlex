import json
import csv
import re
import unidecode
import smartypants

import spacy
from spacy.util import (
    compile_infix_regex,
    compile_prefix_regex,
    compile_suffix_regex,
    filter_spans,
)
from spacy.tokens import Span
from spacy.matcher import PhraseMatcher  # , Matcher

from bs4 import BeautifulSoup
from pathlib import Path


def latin2shaw(text):
    # path where resource files (readlex.json etc.) are kept
    resource_path = Path(__file__).parent.parent

    with resource_path.with_name("readlex_converter.json").open(
        "r", encoding="utf-8"
    ) as f:
        json_data = f.read()

    readlex_dict = json.loads(json_data)

    # Categories of letters that determine how a following 's is pronounced
    s_follows = {"𐑐", "𐑑", "𐑒", "𐑓", "𐑔"}
    uhz_follows = {"𐑕", "𐑖", "𐑗", "𐑟", "𐑠", "𐑡"}
    z_follows = {
        "𐑚",
        "𐑛",
        "𐑜",
        "𐑝",
        "𐑞",
        "𐑙",
        "𐑤",
        "𐑥",
        "𐑯",
        "𐑸",
        "𐑹",
        "𐑺",
        "𐑻",
        "𐑼",
        "𐑽",
    }
    consonants = set.union(s_follows, uhz_follows, z_follows)
    # vowels = {"𐑦", "𐑰", "𐑧", "𐑱", "𐑨", "𐑲", "𐑩", "𐑳", "𐑪", "𐑴", "𐑫", "𐑵", "𐑬", "𐑶", "𐑭", "𐑷", "𐑾", "𐑿"}
    # The following are never final other than in initialisms: "𐑣", "𐑢", "𐑘", "𐑮".

    # Contractions that need special treatment since the separate words are not as they appear in the dictionary
    contraction_start = {
        "ai": "𐑱",
        "ca": "𐑒𐑭",
        "do": "𐑛𐑴",
        "does": "𐑛𐑳𐑟",
        "did": "𐑛𐑦𐑛",
        "sha": "𐑖𐑭",
        "wo": "𐑢𐑴",
        "y'": "𐑘",
    }
    contraction_end = {
        "n't": "𐑯𐑑",
        "all": "𐑷𐑤",
        "'ve": "𐑝",
        "'ll": "𐑤",
        "'m": "𐑥",
        "'d": "𐑛",
        "'re": "𐑼",
    }

    # Common prefixes and suffixes used in new coinings
    prefixes = {
        "anti": "𐑨𐑯𐑑𐑦",
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
        "under": "𐑳𐑯𐑛𐑼",
    }
    suffixes = {
        "able": "𐑩𐑚𐑩𐑤",
        "bound": "𐑚𐑬𐑯𐑛",
        "ful": "𐑓𐑩𐑤",
        "hood": "𐑣𐑫𐑛",
        "ish": "𐑦𐑖",
        "ism": "𐑦𐑟𐑩𐑥",
        "less": "𐑤𐑩𐑕",
        "like": "𐑤𐑲𐑒",
        "ness": "𐑯𐑩𐑕",
    }
    affixes = prefixes | suffixes

    # Words that sometimes change spelling before 'to'
    have_to = {"have": "𐑣𐑨𐑓", "has": "𐑣𐑨𐑕"}
    vbd_to = {"used": "𐑿𐑕𐑑", "unused": "𐑳𐑯𐑿𐑕𐑑", "supposed": "𐑕𐑩𐑐𐑴𐑕𐑑"}
    before_to = have_to | vbd_to

    # Suffixes that follow numerals in ordinal numbers
    ordinal_suffixes = {"st": "𐑕𐑑", "nd": "𐑯𐑛", "rd": "𐑮𐑛", "th": "𐑔", "s": "𐑟"}

    # Load spaCy, excluding pipeline components that are not required
    nlp = spacy.load("en_core_web_sm", exclude=["parser", "lemmatizer", "textcat"])

    # Customise the spaCy tokeniser to ensure that initial and final dashes and dashes between words aren't stuck to one
    # of the surrounding words
    # Prefixes
    spacy_prefixes = nlp.Defaults.prefixes + [
        r"""^[-–—]+""",
    ]
    prefix_regex = compile_prefix_regex(spacy_prefixes)
    nlp.tokenizer.prefix_search = prefix_regex.search
    # Infixes
    spacy_infixes = nlp.Defaults.infixes + [
        r"""[-–—\"\~\(\[]+""",
    ]
    infix_regex = compile_infix_regex(spacy_infixes)
    nlp.tokenizer.infix_finditer = infix_regex.finditer
    # Suffixes
    spacy_suffixes = nlp.Defaults.suffixes + [
        r"""[-–—]+$""",
    ]
    suffix_regex = compile_suffix_regex(spacy_suffixes)
    nlp.tokenizer.suffix_search = suffix_regex.search

    def add_span(matcher, doc, i, matches):
        match_id, start, end = matches[i]

    # Define the phrase to match
    with resource_path.with_name("readlex_converter_phrases.json").open(
        "r", newline=""
    ) as f:
        reader = csv.reader(f)
        phrases = []
        for i in reader:
            phrases.append(i[0])
    phrase_patterns = [nlp.make_doc(phrase) for phrase in phrases]
    phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    phrase_matcher.add("phrases", phrase_patterns, on_match=add_span)

    # # Define the HTML element patterns to match
    # html_patterns = [[{"TEXT": {"REGEX": "(?<=<)"}},
    #                   {"OP": "*", "TEXT": {"REGEX": "[^<>]"}},
    #                   {"TEXT": {"REGEX": "(?=>)"}}],
    #                  [{'LOWER': '<'},
    #                   {'LOWER': 'style'},
    #                   {'OP': '*', 'IS_ASCII': True},
    #                   {'LOWER': '/style'},
    #                   {'LOWER': '>'}],
    #                  [{'LOWER': '<'},
    #                   {'LOWER': 'script'},
    #                   {'OP': '*', 'IS_ASCII': True},
    #                   {'LOWER': '/script'},
    #                   {'LOWER': '>'}]
    #                  ]
    # matcher = Matcher(nlp.vocab)
    # matcher.add("html_elements", html_patterns, on_match=add_span)

    namer_dot_ents = [
        "PERSON",
        "FAC",
        "ORG",
        "GPE",
        "LOC",
        "PRODUCT",
        "EVENT",
        "WORK_OF_ART",
        "LAW",
    ]

    def tokenise(str):
        # Tokenise and tag the text using spaCy as doc

        doc = nlp(str)
        # matches = matcher(doc)
        phrase_matches = phrase_matcher(doc)

        # html_spans = []
        # for match_id, start, end in matches:
        #     span = Span(doc, start, end, label=match_id)
        #     html_spans.append(span)

        phrase_spans = []
        for match_id, start, end in phrase_matches:
            span = Span(doc, start, end, label=match_id)
            phrase_spans.append(span)

        # all_spans = html_spans
        # for i in phrase_spans:
        #     all_spans.append(i)
        # filtered_spans = filter_spans(all_spans)

        filtered_spans = filter_spans(phrase_spans)

        with doc.retokenize() as retokenizer:
            for span in filtered_spans:
                # if span.label_ == "html_elements":
                #     retokenizer.merge(span, attrs={"TAG": "HTML"})
                # else:
                retokenizer.merge(span)

        # Expand person entities to include titles and take initial 'the' out of entity names
        titles = [
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
            "viscountess",
        ]
        new_ents = []
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
        doc.ents = filter_spans(new_ents)

        return doc

    def convert(doc):
        # Apply a series of tests to each token to determine how to Shavianise it.
        text_split_shaw = ""
        for token in doc:
            # Leave HTML tags unchanged
            if token.tag_ == "HTML":
                text_split_shaw += token.text

            # Convert contractions
            elif (
                token.lower_ in contraction_start
                and doc[token.i + 1].lower_ in contraction_end
            ):
                text_split_shaw += contraction_start[token.lower_]
            elif token.lower_ in contraction_end:
                if (
                    token.lower_ != "𐑼"
                    and len(text_split_shaw) > 0
                    and text_split_shaw[-1] in consonants
                ):
                    text_split_shaw += (
                        "𐑩" + contraction_end[token.lower_] + token.whitespace_
                    )
                else:
                    text_split_shaw += contraction_end[token.lower_] + token.whitespace_

            # Convert possessive 's
            elif token.lower_ == "'s":
                if text_split_shaw[-1] in s_follows:
                    text_split_shaw += "𐑕" + token.whitespace_
                elif text_split_shaw[-1] in uhz_follows:
                    text_split_shaw += "𐑩𐑟" + token.whitespace_
                else:
                    text_split_shaw += "𐑟" + token.whitespace_

            # Convert possessive '
            elif token.lower_ == "'" and token.tag_ == "POS":
                text_split_shaw += token.whitespace_

            # Convert verbs that change pronunciation before 'to', e.g. 'have to', 'used to', 'supposed to'
            elif (
                token.lower_ in before_to
                and token.i < (len(doc) - 1)
                and doc[token.i + 1].lower_ == "to"
            ):
                # 'have' only changes pronunciation where 'have to' means 'must'
                if token.lower_ in have_to:
                    if doc[token.i + 2].tag_ in ["VB", "VBP"]:
                        text_split_shaw += have_to[token.lower_] + token.whitespace_
                    # else:
                    # text_split_shaw += "𐑣𐑨𐑟" + token.whitespace_
                # 'used', 'supposed' etc. only change pronunciation in the past tense, not past participle
                elif token.lower_ in vbd_to and token.tag_ in ["VBD", "VBN", "."]:
                    text_split_shaw += vbd_to[token.lower_] + token.whitespace_

            # Match ordinal numbers represented by a numeral and a suffix
            elif re.fullmatch(
                r"([0-9]+(?:[, .]?[0-9]+)*)(st|nd|rd|th|s)", token.lower_
            ):
                match = re.match(
                    r"([0-9]+(?:[, .]?[0-9]+)*)(st|nd|rd|th|s)", token.lower_
                )
                number = match.group(1)
                number_suffix = match.group(2)
                text_split_shaw += (
                    number + ordinal_suffixes[number_suffix] + token.whitespace_
                )

            # Loop through the words in the ReadLex and look for matches, and only apply the namer dot to the first word
            # in a name (or not at all for initialisms marked with ⸰)
            elif token.lower_ in readlex_dict:
                for i in readlex_dict.get(token.lower_, []):
                    # Match the part of speech for heteronyms
                    if i["tag"] == token.tag_:
                        if (
                            token.ent_iob_ == "B"
                            and token.ent_type_ in namer_dot_ents
                            and not i["Shaw"].startswith("⸰")
                        ):
                            text_split_shaw += "·" + i["Shaw"] + token.whitespace_
                        else:
                            text_split_shaw += i["Shaw"] + token.whitespace_
                        break
                    # For any proper nouns not in the ReadLex, match if an identical common noun exists
                    elif (
                        i["tag"] in ["NN", "0"]
                        and token.tag_ == "NNP"
                        or i["tag"] in ["NNS", "0"]
                        and token.tag_ == "NNPS"
                    ):
                        if (
                            token.ent_iob_ == "B"
                            and token.ent_type_ in namer_dot_ents
                            and not i["Shaw"].startswith("⸰")
                        ):
                            text_split_shaw += "·" + i["Shaw"] + token.whitespace_
                        else:
                            text_split_shaw += i["Shaw"] + token.whitespace_
                        break
                    # Match words with only one pronunciation
                    elif i["tag"] == "0":
                        if (
                            token.ent_iob_ == "B"
                            and token.ent_type_ in namer_dot_ents
                            and not i["Shaw"].startswith("⸰")
                        ):
                            text_split_shaw += "·" + i["Shaw"] + token.whitespace_
                        else:
                            text_split_shaw += i["Shaw"] + token.whitespace_
                        break

            # Apply additional tests where there is still no match
            else:
                found = False
                constructed_warning = "⚠️"
                # Try to construct a match using common prefixes and suffixes and include a warning symbol to aid proof
                # reading
                for j in affixes:
                    if token.lower_.startswith(j) and j in prefixes:
                        prefix = prefixes[j]
                        suffix = ""
                        target_word = token.lower_[len(j) :]
                    elif token.lower_.endswith(j) and j in suffixes:
                        prefix = ""
                        suffix = suffixes[j]
                        suffix_length = len(j)
                        target_word = token.lower_[:-suffix_length]
                    else:
                        continue
                    if target_word in readlex_dict:
                        found = True
                        for i in readlex_dict.get(target_word):
                            if i["tag"] != "0" and i["tag"] == token.tag_:
                                if (
                                    token.ent_iob_ == "B"
                                    and token.ent_type_ in namer_dot_ents
                                    and not i["Shaw"].startswith("⸰")
                                ):
                                    text_split_shaw += (
                                        "·"
                                        + prefix
                                        + i["Shaw"]
                                        + suffix
                                        + constructed_warning
                                        + token.whitespace_
                                    )
                                else:
                                    text_split_shaw += (
                                        prefix
                                        + i["Shaw"]
                                        + suffix
                                        + constructed_warning
                                        + token.whitespace_
                                    )
                                break
                            elif i["tag"] == "0":
                                if (
                                    token.ent_iob_ == "B"
                                    and token.ent_type_ in namer_dot_ents
                                    and not i["Shaw"].startswith("⸰")
                                ):
                                    text_split_shaw += (
                                        "·"
                                        + prefix
                                        + i["Shaw"]
                                        + suffix
                                        + constructed_warning
                                        + token.whitespace_
                                    )
                                else:
                                    text_split_shaw += (
                                        prefix
                                        + i["Shaw"]
                                        + suffix
                                        + constructed_warning
                                        + token.whitespace_
                                    )
                                break

                # Try to construct plurals if not expressly included in the ReadLex, e.g. plurals of proper names.
                if token.lower_.endswith("s"):
                    target_word = token.lower_[:-1]
                    if target_word in readlex_dict:
                        found = True
                        for i in readlex_dict.get(target_word):
                            if i["Shaw"][-1] in s_follows:
                                suffix = "𐑕"
                            elif i["Shaw"][-1] in uhz_follows:
                                suffix = "𐑩𐑟"
                            else:
                                suffix = "𐑟"
                            if i["tag"] != "0" and i["tag"] == token.tag_:
                                if (
                                    token.ent_iob_ == "B"
                                    and token.ent_type_ in namer_dot_ents
                                    and not i["Shaw"].startswith("⸰")
                                ):
                                    text_split_shaw += (
                                        "·"
                                        + i["Shaw"]
                                        + suffix
                                        + constructed_warning
                                        + token.whitespace_
                                    )
                                else:
                                    text_split_shaw += (
                                        i["Shaw"]
                                        + suffix
                                        + constructed_warning
                                        + token.whitespace_
                                    )
                                break
                            elif i["tag"] == "0":
                                if (
                                    token.ent_iob_ == "B"
                                    and token.ent_type_ in namer_dot_ents
                                    and not i["Shaw"].startswith("⸰")
                                ):
                                    text_split_shaw += (
                                        "·"
                                        + i["Shaw"]
                                        + suffix
                                        + constructed_warning
                                        + token.whitespace_
                                    )
                                else:
                                    text_split_shaw += (
                                        i["Shaw"]
                                        + suffix
                                        + constructed_warning
                                        + token.whitespace_
                                    )
                                break

                # If there is still no match, do not convert the word
                if found is False:
                    if token.text.isalpha():
                        text_split_shaw += token.text + "✢" + token.whitespace_
                    else:
                        text_split_shaw += token.text + token.whitespace_

        return text_split_shaw

    # Create the string that will contain the Shavianised text.
    text_shaw = ""

    # Split up the string to reduce the risk of spaCy exceeding memory limits
    if text.strip().casefold().startswith("<!doctype html"):
        style_pattern = r"(<style\b[^>]*>.*?</style>)"
        script_pattern = r"(<script\b[^>]*>.*?</script>)"
        html_pattern = (
            r"(?!(?:<style[^>]*?>.*?</style>|<script[^>]*?>.*?</script>))(<.*?>)"
        )
        html_patterns = f"{style_pattern}|{script_pattern}|{html_pattern}"
        text_split = re.split(html_patterns, text, flags=re.DOTALL)
        for text_part in text_split:
            if text_part is None:
                pass
            elif re.fullmatch(style_pattern, text_part, flags=re.DOTALL):
                text_shaw += text_part
            elif re.fullmatch(script_pattern, text_part, flags=re.DOTALL):
                text_shaw += text_part
            elif re.fullmatch(html_pattern, text_part, flags=re.DOTALL):
                text_shaw += text_part
            else:
                doc = tokenise(text_part)
                text_shaw += convert(doc)
        # Convert dumb quotes, double hyphens, etc. to their typographic equivalents
        text_shaw = smartypants.smartypants(text_shaw)
        # # Convert curly quotes to angle quotes
        # quotation_marks = {"&#8216;": "&lsaquo;", "&#8217;": "&rsaquo;", "&#8220;": "&laquo;", "&#8221;": "&raquo;"}
        # for key, value in quotation_marks.items():
        #     text_shaw = text_shaw.replace(key, value)

    else:
        text = unidecode.unidecode(text)
        text = re.sub(r"(\S)(\[)", r"\1 \2", text)
        text = re.sub(r"](\S)", r"] \1", text)
        text_split = text.splitlines()
        for i in text_split:
            if len(i) < 10000:
                doc = tokenise(i)
                text_shaw += convert(doc) + "\n"
        # Convert dumb quotes, double hyphens, etc. to their typographic equivalents
        text_shaw = smartypants.smartypants(text_shaw)
        quotation_marks = {
            "&#8216;": "&lsaquo;",
            "&#8217;": "&rsaquo;",
            "&#8220;": "&laquo;",
            "&#8221;": "&raquo;",
        }
        for key, value in quotation_marks.items():
            text_shaw = text_shaw.replace(key, value)
        text_shaw = str(BeautifulSoup(text_shaw, features="html.parser"))

    return text_shaw


from tap import Tap
import sys


class Args(Tap):
    in_file: str = ""
    """File to read latin text from, if not given, text will be read from stdin"""
    out_file: str = ""
    """File to output Shaw text to, if not given, text will be written to stdout"""


def main():
    args = Args().parse_args()

    if args.in_file != "":
        with open(args.in_file, "r") as in_file:
            text_latin = in_file.read()
    else:
        text_latin = sys.stdin.read()

    text_shaw = latin2shaw(text_latin)

    if args.out_file != "":
        with open(args.out_file, "w") as out_file:
            out_file.write(text_shaw)
    else:
        sys.stdout.write(text_shaw)
