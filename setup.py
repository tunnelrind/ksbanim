from setuptools import setup

setup(
    name='ksbanim',
    version='1.0.18',
    py_modules=['ksbanim'],
    install_requires=[
        'PyQt5',
        'PyOpenGL',
        'imageio[ffmpeg]',
        'requests',
        'triangle',
        'shapely'
    ],
    author='Your Name',
    author_email='your.email@example.com',
    description='A module for animation using PyQt5, OpenGL, and imageio[ffmpeg]',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/ksbanim',  # Update with your repository URL
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)