"""Python setup script for installing ACRO."""

from pathlib import Path

from setuptools import find_packages, setup

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="acro",
    version="0.0.3",
    license="MIT",
    maintainer="Jim Smith",
    maintainer_email="james.smith@uwe.ac.uk",
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AI-SDC/ACRO",
    packages=find_packages(),
    package_data={"acro": ["default.yaml"]},
    python_requires=">=3.10",
    install_requires=["lxml", "numpy", "openpyxl", "pandas", "PyYAML", "statsmodels"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
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
