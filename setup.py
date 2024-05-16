import os
import sys

from setuptools import setup

readme_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)),
    'README.md',
)
long_description = open(readme_path).read()

try:
    version = get_version()
except Exception:
    version = '0.0.0-dev'

setup(
    name='nessclient',
    packages=['nessclient', 'nessclient.cli', 'nessclient.cli.server'],
    author="Nick Whyte",
    author_email='nick@nickwhyte.com',
    description="Implementation/abstraction of the Ness D8x / D16x Serial "
                "Interface ASCII protocol",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/nickw444/nessclient',
    zip_safe=False,
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
    ],
    install_requires=[
        'justbackoff',
        'dataclasses;python_version<"3.7"',
        'pyserial_asyncio'
    ],
    extras_require={
        'cli': ['click']
    },
    entry_points={
        'console_scripts': ['ness-cli=nessclient.cli.__main__:cli'],
    },
    setup_requires=[],
)
