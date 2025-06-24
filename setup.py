from setuptools import setup
from pathlib import Path

setup(
    name='ksbanim',
    version='1.1.34',
    py_modules=['ksbanim'],
    install_requires=[
        'PyQt5',
        'PyOpenGL',
        'imageio[ffmpeg]',
        'requests',
        'triangle',
        'shapely',
        'setuptools'
    ],
    author='Biasini Dario',
    author_email='tunnelrind@lernbaum.ch',
    description='A module for animation based on PyQt5, OpenGL, and imageio[ffmpeg]',
    long_description = Path(__file__).with_name("README.md").read_text(),
    long_description_content_type='text/markdown',
    url='https://github.com/tunnelrind/ksbanim', 
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    licence="MIT",
)