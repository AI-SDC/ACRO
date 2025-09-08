
# ACRO

ACRO is a lightweight, open-source tool for semi-automated statistical disclosure control (SDC). It helps researchers automatically check tables, regressions, and plots for disclosure risks in secure data environments. Instead of manually reviewing outputs after analysis, ACRO runs privacy checks in real time, flags risky results, and generates audit trails for output checkers.

## Table of Contents  
- [Overview]
- [Quick Start]
- [Installation]
- [Basic Usage]
- [Understanding ACRO Output]
- [Configuration]
- [Examples]
- [API Reference]  
- [Support]
- [Contributing]
- [License]
- [Citation] 
- [Acknowledgments]


## Overview  
ACRO acts as a drop-in replacement for common analysis commands, adding privacy-preserving checks on the fly. It transforms standard workflows by running analysis and privacy checks simultaneously.

### What ACRO does:  
- Intercepts analysis commands (e.g., crosstabs, regressions, plots)  
- Applies statistical disclosure control checks in real time  
- Flags potentially disclosive outputs  
- Generates audit trails for output checkers  
- Maintains familiar syntax across Python, R, and Stata  

## Quick Start

### Prerequisites  
- Python 3.9 or higher  
- R 4.0 or higher (for R users)  
- Stata 16 or higher (for Stata users)  

### 30-second setup (Python example)  
```bash
# Install ACRO
pip install acro

# Run first privacy-checked analysis  
python -c "
import acro
session = acro.ACRO()
print('✅ ACRO is ready!')
"
```

## Installation

### Python Installation  
- PyPI (Recommended):  
```bash
pip install acro
```
- Conda:  
```bash
conda install acro
```

## Understanding ACRO Output

When running an ACRO command, you receive three key pieces of information:

1. **Disclosure Status**  
   - ✅ PASS: Output meets privacy requirements  
   - ❌ FAIL: Output violates disclosure rules  
   - ⚠️ REVIEW: Manual review required  

2. **Detailed Check Results**  
   E.g.,  
   | Cell   | Status                              | Reason                              |  
   |--------|-----------------------------------|-----------------------------------|  
   | (1,1)  | PASS                              |                                   |  
   | (1,2)  | FAIL                              | Below frequency threshold (3 < 10)|  
   | (2,1)  | REVIEW                            | Contains missing values            |  
   | (2,2)  | PASS                              |                                   |  

3. **Your Analysis Output**  
Results flagged or suppressed if risky:  
| Category A | Category B |  
|------------|-------------|  
| Group 1    | 15          | 3*         |  
| Group 2    | --          | 28         |  

(* flagged as risky, -- suppressed)  

## Common Disclosure Rules  
- Minimum cell counts (default: 10)  
- Dominant values cannot exceed 90% of cell total  
- Top values sum limit  
- Empty cells flagged for review  

## Configuration  
ACRO parameters and risk appetite can be customized via YAML configuration files.

## Examples  
- Jupyter notebooks with use cases  

## API Reference  
- Python, R, Stata interfaces

## Support  
- [GitHub Issues](https://github.com/AI-SDC/ACRO/issues)  
- [GitHub Discussions](https://github.com/AI-SDC/ACRO/discussions)  
- [Documentation](https://ai-sdc.github.io/ACRO/)  

## Contributing  
Contributions are welcome under the MIT License. See [Contributing.md](https://github.com/AI-SDC/ACRO/blob/main/CONTRIBUTING.md) for details.

## Acknowledgments  
This work was funded by UK Research and Innovation (Grant MC_PC_23006) as part of the DARE UK programme, delivered in partnership with Health Data Research UK and Administrative Data Research UK.

***
