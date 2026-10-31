# Synthetic demonstration / evaluation dataset

Five fictional English, text-based PDFs cover a civil summons, payment demand, consumer hearing, multiple deadlines, and missing dates. All names, authorities, case numbers and claims are invented. These are not authentic legal documents, legal advice, or a representative benchmark.

`expected_results.json` contains source text and manually specified expected facts. `null` means information is absent: the model should not invent it. Dates use ISO format for comparison; equivalent unambiguous date formatting is acceptable. Document-type wording, translations and action summaries may vary while preserving meaning. The payment notice's reference is not a court case number.

Generate/reproduce the PDFs from the project root:

```sh
python3 dataset/generate_pdfs.py
```

## Manual AI evaluation

1. Start the app using the root README and log in.
2. Select the target language **before** upload.
3. Upload each PDF from `dataset/pdfs/`.
4. Compare court, parties, case number, hearing date, deadline dates and action facts with `expected_results.json`.
5. Verify that missing information is not fabricated; manually review translation meaning with a speaker of the selected language.
6. Ask a date/action question in chat and compare it with the notice.
7. Record provider/model, language, date, observed output and pass/fail. Do not claim live accuracy until this is performed.

| Sample | Key edge case |
|---|---|
| 01 | Hearing date differs from reply deadline |
| 02 | Payment deadline, no court hearing or court case |
| 03 | Hearing in a different calendar year |
| 04 | Two filing deadlines plus a separate hearing |
| 05 | No dates, case number or court; avoid invented facts |

Automated tests verify extraction of all five PDFs. They do not establish real-world legal accuracy or live translation quality. No model is trained or fine-tuned on this data.
