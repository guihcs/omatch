from setuptools import setup

setup(
    name='om',
    version='0.6.6',
    packages=['om'],
    url='https://github.com/guihcs/omatch',
    license='',
    author='guilherme',
    author_email='guihss.cs@gmail.com',
    description='Ontology Matching Utilities',
    install_requires=['numpy', 'rdflib', 'pandas', 'tqdm', 'termcolor', 'multiprocessing_on_dill', 'nltk']
)
