# Research question and method comparison

Question: Does combining PDF cryptographic verification, revision comparison and image forensics detect additional suspicious cases without making benign documents unusably noisy?

| Method | What it establishes | What it cannot establish |
|---|---|---|
| CMS digest and public-key verification | Integrity of signed bytes and mathematical validity | Truth of content, signer authority, safety of later visible content |
| pyHanko policy plus parsed revision/render comparison | Classification of changes and evidence of post-signing visible content changes | Every shadow exploit, cross-viewer differential or invisible semantic change |
| Localisation plus ORB/RANSAC | Geometrically consistent repeated image regions | Whether copying was authorised or images represent real signatures |
| ELA | Measured JPEG recompression residuals | Reliable proof of PDF manipulation or signer identity |
| Combined system | Traceable evidence across complementary methods | Legal authenticity certification or generalised real-world accuracy |

The benchmark saves crypto-only, crypto-plus-revision and full-pipeline results. Thresholds remain fixed across development and held-out seeds. Inspect false positives (including repeated logos and benign annotations) and missed image edits. A high recall alone is insufficient. No claim of being the first framework or outperforming existing tools is made.

Reference starting points for the project report:

- PDF signature format and ByteRange: ISO 32000 PDF specification; Adobe PDF Reference, signature section.
- pyHanko validation and difference-analysis documentation: https://docs.pyhanko.eu/
- PDF signature and shadow-attack research: https://www.pdf-insecurity.org/
- ORB: Rublee et al., *ORB: An efficient alternative to SIFT or SURF*, ICCV 2011.
- RANSAC: Fischler and Bolles, *Random Sample Consensus*, Communications of the ACM, 1981.

These references explain the methods; they are not evidence that SignGuard outperforms other systems. An external real-document dataset and independently reviewed attack corpus remain future validation work.
