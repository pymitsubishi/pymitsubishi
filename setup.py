from setuptools import setup, find_packages

setup(
    name='pymitsubishi',
    version='0.1.0',
    description='Control and monitor Mitsubishi Air Conditioners',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Ashleigh Hopkins',
    author_email='ashleigh@example.com',
    url='https://github.com/ashleigh-hopkins/pymitsubishi',
    packages=find_packages(),
    install_requires=[
        'requests',
        'pycryptodome',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
