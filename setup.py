import os
from setuptools import setup

# Sichere, absolute Pfadermittlung für die README.md
# Falls __file__ durch exec() nicht existiert, nutzen wir das aktuelle Verzeichnis als Fallback
if '__file__' in locals() or '__file__' in globals():
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
else:
    BASE_DIR = os.getcwd()

readme_path = os.path.join(BASE_DIR, 'README.md')

# Überprüfen, ob die Datei da ist (hilft beim Debuggen)
if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()
else:
    long_description = 'A module for animation based on PyQt5 and OpenGL'

setup(
    name='ksbanim',
    version='1.3.9',
    py_modules=['ksbanim'],
    install_requires=[
        'PyQt5',
        'PyOpenGL',
        'imageio[ffmpeg]',
        'requests'
    ],
    author='Biasini Dario',
    author_email='tunnelrind@lernbaum.ch',
    description='A module for animation based on PyQt5 and OpenGL',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tunnelrind/ksbanim', 
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    license="MIT",
)
