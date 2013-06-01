import os

from setuptools import setup

README = os.path.join(os.path.dirname(__file__), 'README.md')

setup(
    name='photofs',
    version = '1.2.1',
    description='virtual FUSE file-system for browsing photos',
    long_description=open(README).read() + 'nn',
    author='Sergey Pisarenko',
    author_email='drseergio@gmail.com',
    url='http://pisarenko.net',
    license='GPL',
    py_modules=['photofs_main'],
    packages=['photofs'],
    entry_points={
        'console_scripts': [
            'photofs=photofs_main:main']},
    install_requires=['fuse-python', 'pyinotify'])
