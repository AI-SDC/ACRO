=============
SACRO-Viewer
=============

SACRO-Viewer is a graphical user interface for fast, secure, and effective output checking that works in any Trusted Research Environment (TRE).

Overview
========

SACRO-Viewer provides human checkers with an intuitive interface for reviewing research outputs, featuring:

* Visual display of outputs and disclosure check results
* Highlighting of identified privacy risks
* Streamlined approval/rejection workflow
* Audit trail and decision tracking

Key Features
============

Interactive Review Interface
----------------------------

* Side-by-side view of original and checked outputs
* Color-coded risk indicators
* Expandable details for each disclosure check
* Batch processing capabilities

Risk Assessment Display
-----------------------

* Visual risk level indicators (Low, Medium, High, Critical)
* Detailed explanations of identified issues
* Suggested mitigation strategies
* Statistical context for decisions

Workflow Management
-------------------

* Queue-based output review system
* Reviewer assignment and tracking
* Approval status management
* Export approved outputs

Audit and Compliance
---------------------

* Complete decision audit trail
* Reviewer comments and justifications
* Compliance reporting
* Integration with institutional policies

Installation
============

Desktop Application
-------------------

Download the latest release from the GitHub repository:

.. code-block:: bash

   # Download and install (Windows)
   # Visit: https://github.com/AI-SDC/SACRO-Viewer/releases

Web Application
---------------

Deploy using Docker:

.. code-block:: bash

   # Pull Docker image
   docker pull aisdc/sacro-viewer:latest
   
   # Run web application
   docker run -p 8080:8080 aisdc/sacro-viewer:latest

Development Setup
-----------------

.. code-block:: bash

   # Clone repository
   git clone https://github.com/AI-SDC/SACRO-Viewer.git
   cd SACRO-Viewer
   
   # Install dependencies
   npm install
   
   # Start development server
   npm start

Quick Start
===========

For Output Checkers
--------------------

1. **Launch SACRO-Viewer**
   
   .. code-block:: bash
   
      sacro-viewer

2. **Load Output Directory**
   
   Select the folder containing ACRO outputs to review

3. **Review Outputs**
   
   * Click on each output to view details
   * Review disclosure check results
   * Make approval/rejection decisions
   * Add comments as needed

4. **Export Approved Outputs**
   
   Generate final package of approved research outputs

For Researchers
---------------

1. **Generate Outputs with ACRO**
   
   .. code-block:: python
   
      import acro
      
      session = acro.ACRO()
      # ... your analysis ...
      session.finalise("outputs_for_review/")

2. **Submit for Review**
   
   Provide the output directory to your output checker

3. **Receive Feedback**
   
   Review checker comments and resubmit if needed

Interface Overview
==================

Main Dashboard
--------------

* **Output Queue**: List of pending outputs for review
* **Status Overview**: Summary of approval/rejection statistics  
* **Recent Activity**: Timeline of recent checker actions
* **System Status**: Health checks and system information

Output Review Panel
-------------------

* **Output Display**: Rendered view of tables, plots, and models
* **Risk Assessment**: Detailed disclosure check results
* **Decision Panel**: Approve/reject controls with comment box
* **History**: Previous decisions and reviewer comments

Configuration Panel
--------------------

* **Threshold Settings**: Customize disclosure control parameters
* **User Management**: Reviewer accounts and permissions
* **Audit Settings**: Configure logging and reporting
* **Integration**: Connect with institutional systems

Workflow Examples
=================

Standard Review Process
-----------------------

1. Researcher submits outputs via ACRO
2. Outputs appear in SACRO-Viewer queue
3. Checker reviews each output:
   
   * Examines original output
   * Reviews disclosure check results
   * Considers statistical context
   * Makes informed decision
   
4. Approved outputs are released
5. Rejected outputs return to researcher with feedback

Batch Processing
----------------

For high-volume environments:

1. Load multiple output directories
2. Use filtering to prioritize high-risk outputs
3. Bulk approve low-risk outputs
4. Focus detailed review on flagged items
5. Generate batch approval reports

Integration Options
===================

TRE Integration
---------------

SACRO-Viewer integrates with common TRE platforms:

* **Airlock Systems**: Direct integration with approval workflows
* **File Transfer**: Secure output export mechanisms
* **Authentication**: SSO and institutional login support
* **Logging**: Integration with TRE audit systems

API Integration
---------------

.. code-block:: python

   # Programmatic access to SACRO-Viewer
   import sacro_viewer_api
   
   # Submit outputs for review
   client = sacro_viewer_api.Client(base_url="https://your-tre.org/sacro")
   
   submission = client.submit_outputs(
       output_path="path/to/outputs",
       researcher_id="researcher123",
       project_id="project456"
   )
   
   # Check status
   status = client.get_status(submission.id)

Configuration
=============

Basic Configuration
-------------------

.. code-block:: yaml

   # config.yaml
   server:
     port: 8080
     host: "0.0.0.0"
   
   security:
     authentication: "institutional_sso"
     session_timeout: 3600
   
   disclosure_control:
     default_threshold: 10
     auto_approve_threshold: 5
   
   storage:
     output_directory: "/secure/outputs"
     archive_directory: "/secure/archive"

Advanced Configuration
----------------------

.. code-block:: yaml

   # Advanced settings
   review_workflow:
     require_dual_approval: true
     auto_assign_reviewers: true
     escalation_threshold: "high"
   
   integration:
     tre_system: "airlock_v2"
     export_format: ["pdf", "excel", "csv"]
     notification_email: true
   
   audit:
     log_level: "detailed"
     retention_days: 365
     compliance_reporting: true

User Management
===============

Reviewer Roles
--------------

* **Senior Checker**: Full approval authority, can override decisions
* **Standard Checker**: Standard review and approval permissions  
* **Trainee Checker**: Review only, requires senior approval
* **Administrator**: System configuration and user management

Permission Matrix
-----------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 20 20 10

   * - Action
     - Trainee
     - Standard
     - Senior
     - Admin
   * - View outputs
     - ✓
     - ✓
     - ✓
     - ✓
   * - Approve low risk
     - ✗
     - ✓
     - ✓
     - ✓
   * - Approve high risk
     - ✗
     - ✗
     - ✓
     - ✓
   * - System config
     - ✗
     - ✗
     - ✗
     - ✓

Troubleshooting
===============

Common Issues
-------------

**Issue**: Outputs not loading
**Solution**: Check file permissions and network connectivity

**Issue**: Authentication failures  
**Solution**: Verify SSO configuration and user credentials

**Issue**: Slow performance
**Solution**: Check system resources and database optimization

Performance Optimization
------------------------

* Enable output caching for faster loading
* Use database indexing for large output volumes
* Configure appropriate memory allocation
* Implement output archiving for old submissions

See Also
========

* :doc:`index` - Main ACRO documentation
* :doc:`acro_r` - R integration
* :doc:`sacro_ml` - Machine learning tools
* `SACRO-Viewer GitHub Repository <https://github.com/AI-SDC/SACRO-Viewer>`_