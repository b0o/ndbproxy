from setuptools import setup, find_packages
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md')) as f:
    long_description = f.read()

setup(
    name='ndbproxy',
    version='0.0.1',
    url='https://github.com/b0o/ndbproxy',
    license='MIT',
    author='b0o',
    keywords='ndb node nodejs debugger proxy chrome chromium devtools chrome-devtools',
    description=
    'Bridge between a Node.JS debug server and a Chromium devtools client that adds some additional features',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    platforms='any',
    python_requires='>=3.10',
    install_requires=[
        "requests",
        "websockets",
        "types-requests",
        "click",
    ],
    py_modules=['ndbproxy'],
    entry_points={'console_scripts': ['ndbproxy=ndbproxy:main']},
)
