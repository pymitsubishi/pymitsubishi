from setuptools import setup, find_packages

setup(
    name='pymitsubishi',
    version="0.1.7",
    description='Control and monitor Mitsubishi Air Conditioners',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Ashleigh Hopkins',
    author_email='ashleigh@example.com',
    url='https://github.com/pymitsubishi/pymitsubishi',
    packages=find_packages(),
    install_requires=[
        'requests',
        'pycryptodome',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'flake8',
            'mypy',
            'build',
            'twine',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.12',
)
