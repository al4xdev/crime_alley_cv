# Bill (Editor)

Module responsible for the critical review and automated optimization of the candidate's resume based on the evaluator's feedback report.

## Role in the Multi-Agent Loop (Generator)

While Karen acts as the rigorous validator (Critic) who dissects the resume pointing out gaps and inconsistencies, **Bill** (referenced as the original writer/co-creator of Batman, abbreviated `billf`) acts as the intelligent editor (Generator):

1. **Input Reading**: Ingests the original CV (`cv.md`), the job description (`job.md`), and the gaps and alerts mapped in Karen's report (`evaluation.md`).
2. **Defect Correction**: Rewrites sections of the resume to address Karen's criticisms (e.g., suggesting phrasing corrections for inflated terms, detailing optimization techniques applied).
3. **Stack Alignment**: Refines the resume's focus to highlight actual technologies found in the candidate's repositories, ensuring the CV remains highly competitive but 100% truthful.
4. **Hardening**: Produces an optimized CV ready to pass automated and human screening with higher technical fit scores.

## Planned Structure

```
billf/
├── README.md
├── Dockerfile               ← Isolated environment for editing
├── run.sh                   ← Starts the CV review process
└── prompt_revisor.txt       ← Instructions for Bill's technical editor persona
```
