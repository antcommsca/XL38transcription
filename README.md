# XL38transcription

> **Transkribus PAGE XML → TEI P5 conversion pipeline for the diplomatic transcription of manuscript XL (38) (*Virgilius Veronensis*) from the Biblioteca Capitolare di Verona.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)]()
[![TEI P5](https://img.shields.io/badge/TEI-P5-green.svg)]()
[![Horizon Europe](https://img.shields.io/badge/Horizon-Europe-blue.svg)]()

## Overview

This repository contains the code and datasets used to convert **Transkribus PAGE XML** exports into a single **TEI P5 XML** document for manuscript **XL (38)** (*Virgilius Veronensis*), a palimpsest preserved at the **Biblioteca Capitolare di Verona**.

The repository was developed within the **AntCom** project (*From Antiquity to Community: Rethinking Classical Heritage through Citizen Humanities*), funded by the **Horizon Europe Marie Skłodowska-Curie Actions Doctoral Network** (Grant Agreement **101073543**).

## Project background

The undertext of manuscript XL (38) preserves fragments of Virgil's **Eclogae**, **Georgics**, and **Aeneid**. Because of the manuscript's complex preservation state, Handwritten Text Recognition (HTR) was evaluated but found unsuitable. Instead, the manuscript was transcribed manually using **Transkribus** through a citizen humanities initiative involving trained Italian high-school students.

The workflow combined:

- textual criticism and Virgilian philology;
- Latin paleography;
- multispectral imaging (MSI);
- collaborative manual transcription in Transkribus;
- expert review by project researchers;
- automatic conversion from PAGE XML to TEI.

## Repository structure

```text
.
├── page2tei.py
├── tei_header.tei.xml
├── transkribus_export/
├── XL38transcription.tei.xml
└── README.md
```

## Requirements

- Python 3.9+
- Standard library only
- No external dependencies

## Usage

```bash
python3 page2tei.py   --glob "transkribus_export/export_job_*/*/*/page/*.xml"   --header tei_header.tei.xml   -o XL38transcription.tei.xml
```

## Conversion model

Each PAGE XML file becomes:

- `<div type="page">`
- each `TextRegion` → `<div>`
- each `TextLine` → `<l>`

Supported Transkribus annotations:

| Transkribus | TEI |
|-------------|-----|
| abbrev | `<choice><abbr/><expan/></choice>` |
| add | `<add>` |
| corr | `<subst>` |
| del | `<del>` |
| gap | `<gap/>` / `<supplied>` |
| unclear | `<unclear>` / `<choice>` |
| nota | `<seg>` + `<note>` |

The converter preserves reading order, identifiers, structural metadata and editorial annotations while intentionally omitting image coordinates.

## Output

The generated TEI is intended as a **scholarly diplomatic transcription**, preserving editorial markup while remaining suitable for further philological work and publication.

## Citation

If you use this software or the accompanying transcription data, please cite:

> AntCom – *From Antiquity to Community: Rethinking Classical Heritage through Citizen Humanities*. Horizon Europe Marie Skłodowska-Curie Actions Doctoral Network. Grant Agreement No. 101073543.

## Funding

Funded by the **European Union Horizon Europe Programme** under the **Marie Skłodowska-Curie Actions Doctoral Network** (Grant Agreement No. **101073543**).

Project website: https://antcom.eu/

