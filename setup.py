import os

from setuptools import setup

README = os.path.join(os.path.dirname(__file__), 'README.md')

setup(
    name='photofs',
    version = '1.1.1',
    description='virtual FUSE file-system for browsing photos',
    long_description=open(README).read() + 'nn',
    author='Sergey Pisarenko',
    author_email='drseergio@gmail.com',
    url='http://grow-slowly.com',
    license='GPL',
    py_modules=['main'],
    packages=['photofs'],
    entry_points={
        'console_scripts': [
            'photofs=main:main']},
    install_requires=['fuse-python', 'pyinotify'])
