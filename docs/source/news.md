# SACRO Tools Latest Release

Release announcements and highlights from **ACRO**, **ACRO-R** and **SACRO-ML**.
These tools help researchers and output checkers assess privacy disclosure risks
in research outputs and trained machine learning models.


## ACRO 1.1.0

**Released 5 November 2026**

This release adds explanations of disclosure risks to help users understand
the checks applied to their outputs, alongside new statistical analysis support.

### Additional Functionality

* Add command shortcuts and factor notation in Stata.
* Add Cox proportional hazards regression support in Python and Stata.
* Add disclosure risk explanations.

### Fix

* Correct the MyBinder link.
* Include custom outputs in XLSX finalisation.
* Join index conditions with `&` to avoid `TypeError`.

[Read the release notes](https://github.com/AI-SDC/ACRO/releases/tag/v1.1.0)
or browse the [full ACRO changelog](acro-changelog.md).

## ACRO-R 1.1.1

**Released 9 November 2026**

ACRO-R brings ACRO's output-checking tools into R. The 1.1 release series adds
Cox proportional hazards support; the latest maintenance release corrects
package-author information.

### Additional Functionality

* Add Cox proportional hazards support in **1.1.0**.

### Fix

* Correct the maintainer roles in the package's `Authors@R` field in **1.1.1**.

[Read the 1.1.1 release notes](https://github.com/AI-SDC/ACRO-R/releases/tag/v1.1.1)
or browse the [full ACRO-R changelog](https://github.com/AI-SDC/ACRO-R/blob/main/NEWS.md).

## SACRO-ML 2.0.1

**Released 25 September 2026**

The 2.0 release series expands the ways researchers can assess information leakage
from trained models. Version 2.0.1 updates compatibility with ACRO.

### Additional Functionality

The following additions were released in **2.0.0**:

* Add individual-record vulnerability reporting for `WorstCaseAttack` and clearer LiRA vulnerability plots.
* Add instance-based leakage assessment for SVM and kNN models, quantile-regression membership inference, and `MetaAttack` to combine assessments from several attacks.
* Add scikit-learn-compatible scorers for membership-inference metrics.

### Compatibility

* Relax the ACRO dependency upper bound to `<2` in **2.0.1**.

[Read the 2.0.1 release notes](https://github.com/AI-SDC/SACRO-ML/releases/tag/v2.0.1),
[explore the 2.0.0 additions](https://github.com/AI-SDC/SACRO-ML/releases/tag/v2.0.0),
or browse the [full SACRO-ML changelog](https://github.com/AI-SDC/SACRO-ML/blob/main/CHANGELOG.md).
Entries marked **Unreleased** in that changelog are not part of these announcements.

## Stay informed

Follow releases for [ACRO](https://github.com/AI-SDC/ACRO/releases),
[ACRO-R](https://github.com/AI-SDC/ACRO-R/releases) and
[SACRO-ML](https://github.com/AI-SDC/SACRO-ML/releases).
For questions, contact [sacro.contact@uwe.ac.uk](mailto:sacro.contact@uwe.ac.uk).

```{toctree}
:hidden:

acro-changelog
```
