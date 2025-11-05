:orphan:

========
FAQ
========

Frequently Asked Questions (FAQ)
================================

This section provides answers to common questions about the AI-SDC project, including risk explainers for SVM and agreements required from researchers at the design phase.

---------------------------
SVM Risk Explainer
---------------------------

**Q: What is the SVM risk explainer in AI-SDC?**

A: The SVM (Support Vector Machine) risk explainer in AI-SDC provides insights into how SVM models may introduce disclosure risks. It helps researchers understand which features or data points are most influential in model predictions, and assesses the potential for sensitive information leakage through model outputs.

**Q: Why is SVM risk assessment important for statistical disclosure control?**

A: SVMs can inadvertently reveal patterns or individual-level information if not carefully controlled. The risk explainer assists in identifying and mitigating these risks, ensuring that outputs comply with disclosure control policies.

---------------------------
ML Risk Agreements
---------------------------

**Q: What agreements do researchers need to make regarding machine learning risks at the design phase?**

A: Before using AI-SDC for machine learning tasks, researchers must agree to specific terms regarding risk management. These agreements typically include:

- Acknowledging the risks of data leakage and potential re-identification in ML models.
- Committing to follow recommended disclosure control practices for training, testing, and reporting results.
- Agreeing to use risk assessment tools provided by AI-SDC (such as the SVM risk explainer).
- Documenting the intended use, data sources, and mitigation strategies at the project design phase.

**Q: Why are these agreements necessary?**

A: These agreements ensure that all research conducted with AI-SDC aligns with ethical standards, regulatory requirements, and organizational policies on data privacy and disclosure risk.

---------------------------
General
---------------------------

**Q: Where can I find more information about configuring and using AI-SDC?**

A: Please refer to the :doc:`user_guide/configuration` and :doc:`examples` guides in this documentation, or visit the `AI-SDC GitHub repository <https://github.com/AI-SDC/ACRO>`_ for further resources.

**Q: Who should I contact for support or to report a security concern?**

A: Contact the project maintainers via the GitHub Issues page or the email address listed in the repository's README.

---------------------------

*If you have additional questions, please submit an issue or consult the community discussions on GitHub.*
