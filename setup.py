import setuptools

setuptools.setup(
    use_scm_version={
        "local_scheme": "no-local-version",
        "tag_regex": r"^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$",
        "write_to": "src/pyatmo/__version__.py",
        "write_to_template": '''"""
Pyatmo: Simple API to access Netatmo devices and data

DO NO EDIT THIS FILE - VERSION IS MANAGED BY SETUPTOOLS_SCM
"""
__version__ = "{version}"
''',
    },
)
