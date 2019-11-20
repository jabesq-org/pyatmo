# python setup.py --dry-run --verbose install

from setuptools import find_packages, setup

setup(
    name="pyatmo",
    version="3.1.0",  # Should be updated with new versions
    author="Hugo Dupras",
    author_email="jabesq@gmail.com",
    packages=find_packages(exclude=["tests"], where="src"),
    package_dir={"": "src"},
    scripts=[],
    data_files=[],
    url="https://github.com/jabesq/netatmo-api-python",
    license="MIT",
    description=(
        "Simple API to access Netatmo weather station data from any Python 3 script. "
        "Design for Home-Assitant (but not only)"
    ),
    long_description=open("README.md").read(),
    install_requires=["requests"],
)
