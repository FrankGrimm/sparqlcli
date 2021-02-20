import os
from setuptools import setup

requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
install_requires = []
if os.path.isfile(requirements_file):
    with open(requirements_file) as infile:
        install_requires = infile.read().splitlines()

setup(
    name='sparqlcli',
    author='Frank Grimm',
    author_email='git@frankgrimm.net',
    version='1.0',
    url='http://github.com/FrankGrimm/sparqlcli',
    py_modules=['sparqlcli'],
    description='SPARQL CLI client',
    long_description="",
    entry_points={
        'console_scripts': [
            'sparqlcli = sparqlcli:main'
        ]
    },
    zip_safe=False,
    install_requires=install_requires,
    classifiers=[
        'Programming Language :: Python'
    ]
)
