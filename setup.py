# python setup.py --dry-run --verbose install

from distutils.core import setup

setup(
    name="pyatmo",
    version="3.0.0",  # Should be updated with new versions
    author="Hugo Dupras",
    author_email="jabesq@gmail.com",
    py_modules=["pyatmo"],
    packages=["pyatmo"],
    package_dir={"pyatmo": "pyatmo"},
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
