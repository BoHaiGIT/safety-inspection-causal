**Cover Letter — Safety Science**

Date: 30 October 2026

To:
Editor-in-Chief
*Safety Science* (Elsevier)
Editorial Manager: https://editorialmanager.com/safety

Dear Editor-in-Chief,

I am pleased to submit my manuscript entitled **“How large is the deterrent effect of safety inspections? Within-establishment evidence from 59,621 U.S. construction establishments”** for consideration as a Research Article in *Safety Science*.

**Fit with the journal’s scope.** *Safety Science* explicitly welcomes research on the effectiveness of inspection and on the evaluation of regulatory interventions. The paper is a direct evaluation of that question — and, unusually, it reports how much of the answer depends on the identification strategy rather than only reporting the estimate.

**What the paper does.** I assemble the complete U.S. federal enforcement registry for construction (2010–2019), recover the establishment identifier that the public data lacks through text-normalised name-and-state resolution, and construct 142,354 inspection-to-inspection transitions across 59,621 establishments. I then estimate the same deterrent effect three ways on the same records:

1. **Pooled comparison**, which yields +22.6% — a *positive* association between programmed inspection and later violations, driven entirely by targeting.
2. **Regression adjustment on observables** (value-added OLS, double machine learning, doubly robust AIPW), which reverses the sign to −4.5%, −3.7%, and −1.9% respectively.
3. **Within-establishment fixed effects**, exploiting the 10,986 establishments observed under both programmed and unprogrammed protocols, which yields a stable **−3.5%** (95% CI −5.9% to −0.4%), or −4.8% in the switcher subsample.

**The diagnostic I would most like reviewers to examine.** I substitute a *future* programmed inspection for the current treatment — an event that cannot affect an outcome that precedes it. Between establishments, this placebo returns +26.1%, stronger than the effect being estimated; within establishments it falls to +10.4%. This is what persuades me to report the regression-adjusted estimates as fragile and the within-establishment estimate as the paper’s main result, and I believe it is a transferable caution for a literature in which registry-based evaluation is common.

**Substantive findings.** The effect is concentrated in large establishments (−6.1%), unionised workplaces (−16.0%), and inspection horizons beyond one year (−5.8%); it is absent among establishments already cited at the index inspection and in the 2015–2019 period. The allocation implication runs against the intuitive targeting rule: the marginal return appears to sit with currently-clean, larger, unionised establishments rather than with the worst performers.

**Declarations.** The manuscript is original, has not been published previously, and is not under consideration elsewhere. The author has approved the submission. There are no conflicts of interest to declare. All data are public; analysis code reproducing every table, including the establishment-resolution routine, is archived at https://github.com/BoHaiGIT/safety-inspection-causal.

One deliberate limitation should be noted at the outset: the public enforcement registry does not contain establishment injury counts, so the outcome is cited serious violations rather than injuries. No injury-rate effect is claimed anywhere in the paper, and this is stated in the Abstract, Section 3.3, and the Limitations.

Suggested potential reviewers (optional): [to be supplied].

Thank you for your consideration.

Sincerely,

Bin Jiang (Jared)
Qingdao Bohai Construction Group, Qingdao, China
13963901396@163.com
ORCID: https://orcid.org/0009-0008-3989-0924
