import re

from setuptools import find_packages, setup

install_requires = [
    'Django>=1.11.28',
    'Wagtail>=2.2',
    'django-otp>=0.8.1',
    'six>=1.14.0',
    'qrcode>=6.1',
]

docs_require = [
    'sphinx>=1.4.1',
    'sphinx_rtd_theme>=0.4.3',
]

tests_require = [
    'coverage==5.3',
    'pytest==6.0.2',
    'pytest-cov==2.10.1',
    'pytest-django==3.10.0',

    # Linting
    'isort==5.5.3',
    'flake8==3.8.3', # 3.7.9
    'flake8-blind-except==0.2.0',
    'flake8-debugger==3.2.1',
]

with open('README.rst') as fh:
    long_description = re.sub(
        '^.. start-no-pypi.*^.. end-no-pypi', '', fh.read(), flags=re.M | re.S)

setup(
    name='wagtail-2fa',
    version='1.4.2',
    description="Two factor authentication for Wagtail",
    long_description=long_description,
    url='https://github.com/LabD/wagtail-2fa',
    author="Lab Digital",
    author_email="opensource@labdigital.nl",
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        'docs': docs_require,
        'test': tests_require,
    },
    python_requires='>=3.6',
    use_scm_version=True,
    entry_points={},
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    zip_safe=False,
)
