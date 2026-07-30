# XL38transcription

Code and datasets for producing a TEI XML edition of the transcription of manuscript XL (38) (Virgilius Veronensis) from Transkribus PAGE XML exports.

This repository was developed within the AntCom project (From Antiquity to Community: Rethinking Classical Heritage through Citizen Humanities), funded by the Horizon Europe Marie Skłodowska-Curie Actions Doctoral Network (Grant Agreement No. 101073543).

## Project background

Manuscript XL (38) from the Biblioteca Capitolare di Verona is a palimpsest preserving fragments of Virgil's Bucolics, Georgics, and Aeneid as an erased undertext.

Because of the manuscript's complex preservation state, Handwritten Text Recognition (HTR) was evaluated but ultimately deemed unsuitable. Instead, the transcription was produced manually through a citizen humanities initiative involving Italian high school students, who were trained in:

textual criticism and Virgilian philology;
Latin paleography;
multispectral imaging (MSI);
collaborative transcription using Transkribus;
TEI-oriented transcription practices.

Student transcriptions were subsequently reviewed and harmonized by project researchers before export.

## Repository contents
.
├── XL38trasncription.tei.xml  # TEI file with the transcription
├── page2tei.py                # PAGE XML → TEI converter
├── tei_header.tei.xml         # TEI header (user supplied)
├── transkribus_export/        # Original PAGE XML exports
└── README.md
Conversion workflow

The workflow consists of:

manual transcription and annotation in Transkribus;
export of PAGE XML files;
conversion of PAGE XML into a single TEI document using page2tei.py.

## Example usage:

python3 page2tei.py \
  --glob "transkribus_export/export_job_*/*/*/page/*.xml" \
  --header tei_header.tei.xml \
  -o XL38transcription.tei.xml

## PAGE XML → TEI mapping

The converter resolves Transkribus annotations into TEI P5 inline markup.

Transkribus annotation	TEI output
abbrev	<choice><abbr/><expan/></choice>
add	<add>
corr	<subst><add/><del/></subst>
del	<del>
gap	<gap/> or <supplied>
unclear	<unclear> or <choice>
nota	<seg type="nota"> + <note>

The converter preserves:

reading order;
region and line identifiers;
structural metadata assigned in Transkribus;
editorial annotations encoded through the custom attribute.

Image coordinates (baselines and polygons) are intentionally omitted from the TEI output.

## Output

The generated TEI document contains:

one <div type="page"> per PAGE XML file;
one nested <div> per text region;
one <l> element for each transcribed line;
inline TEI markup for editorial interventions and uncertainty.

The resulting TEI is intended as a scholarly, machine-readable transcription suitable for further editorial work and publication.

## Requirements
Python 3
Standard Python library only (no external dependencies)

## Citation

If you use this software or the accompanying transcription data, please cite the AntCom project:

AntCom – From Antiquity to Community: Rethinking Classical Heritage through Citizen Humanities. Horizon Europe Marie Skłodowska-Curie Actions Doctoral Network. Grant Agreement No. 101073543.

## Funding

This work was funded by the European Union Horizon Europe Programme through the Marie Skłodowska-Curie Actions Doctoral Network, Grant Agreement No. 101073543.

Project website: https://antcom.eu/