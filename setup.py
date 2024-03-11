from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf8") as file_io:
    desc_long = file_io.read()

setup(
    name="CompatiGraph",
    # TODO Parse it from tag
    version="1.0.0",
    author="Ilya Kuksenok and Darya Kolesova",
    author_email="kuksyenok.i.s@gmail.com, ohirro@gmail.com",
    description="A tool for analyzing dependencies and compatibility between software components.",
    long_description=desc_long,
    long_description_content_type="text/markdown",
    url="https://github.com/Ohirro/CompatiGraph",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "compatigraph=compatigraph.__main__:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
