from setuptools import setup, find_packages

setup(
    name='pyforma',
    version='0.1dev',
    description='Installs and runs pyforma.',
    author='Oakland Analytics',
    author_email='oaklandanalytics@gmail.com',
    license='BSD',
    url='https://github.com/fscottfoti/pyforma',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: BSD License'
    ],
    packages=find_packages(exclude=['*.tests'])
)
