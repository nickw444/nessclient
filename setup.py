import os
import sys

from setuptools import setup


def get_version():
    version_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'VERSION')
    v = open(version_path).read()
    if type(v) == str:
        return v.strip()
    return v.decode('UTF-8').strip()


readme_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)),
    'README.md',
)
long_description = open(readme_path).read()

try:
    version = get_version()
except Exception:
    version = '0.0.0-dev'

needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(
    name='nessclient',
    version=version,
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
    ],
    install_requires=[
        'justbackoff',
        'dataclasses;python_version<"3.7"'
    ],
    extras_require={
        'cli': ['click']
    },
    entry_points={
        'console_scripts': ['ness-cli=nessclient.cli.__main__:cli'],
    },
    test_suite='nessclient_tests',
    setup_requires=[] + pytest_runner,
    tests_require=['pytest==4.3.0', 'pytest-asyncio', 'asynctest'],
)
