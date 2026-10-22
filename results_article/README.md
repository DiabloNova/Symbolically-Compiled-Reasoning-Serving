# SCRS article remediation workspace

This directory preserves the source manuscript and keeps each audit finding's replacement text and calculation artifacts isolated by priority and finding ID.

## Source preservation

- `original.md` contains a PDF-derived text transcription of the supplied 35-page `SCRS_Manuscript.pdf`. Running headers and page numbers are removed and line wrapping is normalized; the paper's wording, reported values, equations, captions, and source inconsistencies are retained. Figures themselves remain represented by their captions.
- The PDF is used as the transcription source because the supplied DOCX archive reports a CRC failure in `word/media/image1.png`. This is an asset-integrity limitation; it does not mean the PDF source is damaged.
- The transcription has not silently corrected the manuscript. Original values are preserved there; proposed replacements are kept separately.

## Finding scope

- `p0/R1/` addresses only expected Oracle output-token accounting and the cost claims directly dependent on it.
- The R1 package replaces the under-specified Equation (17) output accounting with a mutually exclusive, regime-weighted expectation; it carries explicit assumptions and an eight-configuration recalculation.
- Costs based on the explicit API price schedule are API-only scenarios, not all-in costs. Table 2's hosting allocations and several output-token means remain unverified.
- Latency percentiles, accuracy targets, cross-domain safety claims, and unrelated findings remain out of scope for R1.

## Workflow

Keep each finding's sources, assumptions, calculations, and replacement text in its own directory. Do not treat projections as measurements, and do not advance to another finding until the current finding has been reviewed and approved.
