"""Setup configuration for MyGit - A minimal distributed version control system."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mygit",
    version="1.0.0",
    author="Ankur Kumar Verma",
    author_email="ankurr2120@gmail.com",
    description="A minimal distributed version control system implementing Git core features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AKV-7/mygit",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "colorama>=0.4.0",
        "tabulate>=0.9.0",
        "flask>=2.3.0",
        "flask-cors>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mygit=mygit:main",
        ],
    },
)
