from setuptools import setup, find_packages

setup(
    name='ksbanim',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'PyQt5',
        'PyOpenGL',
        'imageio[ffmpeg]'
    ],
    author='Biasini Dario',
    author_email='tunnelrind@lernbaum.ch',
    description='A module for animation using PyQt5, OpenGL, and imageio[ffmpeg]',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/tunnelrind/ksbanim',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)