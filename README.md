# Read Lexicon

![readlex_header](https://user-images.githubusercontent.com/59408625/207819883-cdbcaf58-a470-44d5-ad89-abe4b6c3e6a7.svg)

The Read Lexicon: a spelling dictionary for the Shavian alphabet following the rhotic Received Pronunciation standard.

This repository contains the data files used for the searchable [Read Lexicon](https://readlex.pythonanywhere.com/).

## readlex.json

The JSON file, readlex.json, contains words grouped by headword, with each word having:

1. the Latin alphabet spelling
2. the Shavian alphabet spelling
3. The part of speech (POS) tagged according to the [C5 tagset used in the British National Corpus](http://www.natcorp.ox.ac.uk/docs/c5spec.html)
4. The Received Pronunciation based pronunciation adopted for the purpose of the Shavian spelling in the International Phonetic Alphabet. This includes some additional information in CAPITAL LETTERs, namely the standard word signs are “the” Ð, “to” T, “and” N, “of” V, and “for” F. The reinserted Rs not normally found in RP are represented by a capital R. Both options for the TRAP-BATH split and the TRAP-BATH merger are represented by capital Ɑː and capital Æ respectively. Some Shavian conventions around the spelling of /ə/ and unstressed /ɪ/ in some contexts are given as Ə and I, and both are transliterated as 𐑩 for the purposes of the Kingsley Read Lexicon. The voiceless /ʍ/ is also distinguished from /w/ for those who want it (e.g. to generate Quikscript spellings), but for the purposes of the Kingsley Read Lexicon both are transliterated as 𐑢.
5. The word frequency from the British National Corpus, for statistical interest and supporting predictive text applications.

## readlex.tsv

The TSV file has five columns representing the above information, but does not group words by headword.

## readlex_converter.json and readlex_converter_phrases.json

The files readlex_converter.json and readlex_converter_phrases.json have been developed for use with the latin2shaw.py script for auto-transliteration (see below).

## readlex.dict

The file readlex.dict (and addendum.dict) is adapted for use with Dave Coffin's scrips available at [Dechifro.org](https://www.dechifro.org/shavian/).

## latin2shaw.py

The file latin2shaw.py is the script I use for the ReadLex Converter. It uses spaCy for part of speech tagging. 

To use latin2shaw.py you'll need to install the following packages with it:
- spaCy and an English language model (I use en_core_web_sm), following the instructions [here](https://spacy.io/usage)
- unidecode
- smartypants
- bs4 (BeautifulSoup)

You will also need to make sure that latin2shaw.py points to the locations where you have saved readlex_converter.json and readlex_converter_phrases.json.

## Futher information

Further information about the Shavian alphabet may be found at https://www.shavian.info.
