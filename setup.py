from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="terraform-ingest",
    version="0.1.0",
    author="",
    description="A terraform multi-repo module AI RAG ingestion engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "pyyaml>=6.0",
        "gitpython>=3.1.0",
        "python-hcl2>=4.3.0",
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "terraform-ingest=terraform_ingest.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
