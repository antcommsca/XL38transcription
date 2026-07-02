# XL38transcription
Code and dataset for exporting from Transkribus to TEI the transcription of the manuscript XL (38) of the Capitolare Library of Verona.

## Generating the transcription

The manuscript XL (38) (_Virgilius Veronensis_) has been transcribed during
the citizen science project using Transkribus.
Because of the complex conservative status of the codex, it was not feasible to
train a model for HTR. Tranksribus has been used as a Graphical User Interface for manual annotation of the codex by the citizens supervised by the project memebers.

The original Transkribus exports are archived in the  `transkribus_export` folder.

To create the XML TEI file we use `page2tei.py` Python script:

```
python3.12 page2tei.py --glob "transkribus_export/export_job_*/*/*/page/*.xml" > XL38transcription.tei.xml
```

# Funding
Funded by the Horizon Europe Programme, MSCA Doctoral Network, Grant Agreement No. 101073543.

