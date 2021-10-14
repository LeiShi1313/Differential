#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="Differential",
    packages=find_packages(include=["differential", "differential.*"]),
    long_description=open("README.md", "r", encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    description="a Python script for easy uploading torrents to varies PT sites.",
    author="Lei Shi",
    author_email="me@leishi.io",
    url="https://github.com/leishi1313/Differential",
    keywords=["PT", "mediainfo", "ptgen", "ptpimg"],
    classifiers=[
        "Environment :: Console",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.6.2",
    install_requires=[
        "loguru>=0.5.0",
        "Pillow>=8.0.0",
        "pymediainfo>=5.0",
        "torf>=3.0.0",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "differential=differential.main:main",
            "dft=differential.main:main",
        ]
    },
)
