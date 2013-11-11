from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
#NEWS = open(os.path.join(here, 'NEWS.txt')).read()


version = '0.1'

install_requires = [ "numpy" ]


setup(name='pdf-table-extract',
    version=version,
    description="Extract Tables from PDF files",
    long_description=README + '\n\n',# + NEWS,
    classifiers=[
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    ],
    keywords='PDF, tables',
    author='Ian McEwan',
    author_email='ijm@ashimaresearch.com',
    url='ashimaresearch.com',
    license='MIT-Expat',
    packages=find_packages('src'),
    package_dir = {'': 'src'},include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        'console_scripts':
            ['pdf-table-extract=pdftableextract.scripts:main']
    }
)
