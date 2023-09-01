"""Python setup script for installing ACRO."""

from pathlib import Path

from setuptools import find_packages, setup

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="acro",
    version="0.4.3",
    license="MIT",
    maintainer="Jim Smith",
    maintainer_email="james.smith@uwe.ac.uk",
    description="ACRO: Tools for the Automatic Checking of Research Outputs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AI-SDC/ACRO",
    packages=find_packages(),
    setup_requires=["wheel"],
    package_data={"acro": ["default.yaml"]},
    python_requires=">=3.8",
    install_requires=[
        "lxml",
        "matplotlib",
        "numpy",
        "openpyxl",
        "pandas~=1.5.0",
        "PyYAML",
        "statsmodels",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Operating System :: OS Independent",
    ],
    keywords=[
        "data-privacy",
        "data-protection",
        "privacy",
        "privacy-tools",
        "statistical-disclosure-control",
    ],
)
