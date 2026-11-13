# Word list for keyboard suggestions

`tr_words.txt` holds 20,000 Turkish word forms with corpus counts, one
`word count` pair per line, most frequent first.

- Source: `content/2018/tr/tr_50k.txt` from
  [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords),
  generated from the OpenSubtitles 2018 corpus (<http://opus.nlpl.eu/OpenSubtitles2018.php>).
- License: the source repository states CC-BY-SA-4.0 for content. This derived
  file is distributed under the same license.
- Changes: kept the first 20,000 entries made only of lowercase Turkish letters
  (including â, î, û) with at least two letters; entries with q, w, x, digits,
  apostrophes or other characters were dropped. Counts are unchanged.
- Downloaded 2026-11-13. The application reads only this local file.

Limitations: subtitle language is informal and may contain offensive words,
misspellings and names; no filtering beyond the rule above was applied.
