#!/usr/bin/env python
from glob import glob
from setuptools import setup, find_packages

setup(
    name="Differential",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'differential': glob('tools/**/*')
    },
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
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.8",
    install_requires=[
        "loguru",
        "requests",
        "Pillow>=9.0.0",
        "pymediainfo>=5.1.0",
        "torf>=3.1.3",
        "bencode.py==4.0.0",
        "lxml>=4.7.1",
    ],
    entry_points={
        "console_scripts": [
            "differential=differential.main:main",
            "dft=differential.main:main",
        ]
    },
)
