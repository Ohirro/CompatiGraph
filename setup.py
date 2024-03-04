from setuptools import setup, find_packages

setup(
    name="CompatiGraph",
    # TODO Parse it from tag
    version="1.0.0",
    author="Ilya Kuksenok and Darya Kolesova",
    author_email="kuksyenok.i.s@gmail.com, ohirro@gmail.com",
    description="A tool for analyzing dependencies and compatibility between software components.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Ohirro/CompatiGraph",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "compatigraph=compatigraph.main:run",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
