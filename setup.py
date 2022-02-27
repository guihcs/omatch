from setuptools import setup

setup(
    name='ont',
    version='0.1',
    packages=[''],
    url='https://github.com/guihcs/omatch',
    license='',
    author='guilherme',
    author_email='guihss.cs@gmail.com',
    description='Ontology Matching Utilities',
    requires=['rdflib', 'pandas', 'numpy', 'multiprocessing_on_dill']
)
