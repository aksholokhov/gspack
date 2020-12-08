from pathlib import Path

from setuptools import setup, find_packages


if __name__ == "__main__":

    base_dir = Path(__file__).parent
    src_dir = base_dir / 'src'

    about = {}
    with (src_dir / "gspack" / "__about__.py").open() as f:
        exec(f.read(), about)

    with (base_dir / "README.md").open() as f:
        long_description = f.read()

    install_requirements = [t.strip() for t in open("requirements.txt", 'r').readlines()]

    test_requirements = [
        'pytest',
    ]

    doc_requirements = []

    setup(
        name=about['__title__'],
        version=about['__version__'],

        description=about['__summary__'],
        long_description=long_description,
        license=about['__license__'],
        url=about["__uri__"],

        author=about["__author__"],
        author_email=about["__email__"],

        package_dir={'': 'src'},
        packages=find_packages(where='src'),

        package_data = {
            "gspack": ["src/gspack/templates/run_autograder",
                       "src/gspack/templates/run_tests.py",
                       "src/gspack/templates/setup.sh"
                       ]
        },
        include_package_data=True,

        python_requires='>3.5.2',
        install_requires=install_requirements,
        tests_require=test_requirements,
        extras_require={
            'docs': doc_requirements,
            'test': test_requirements,
            'dev': [doc_requirements, test_requirements]
        },
        entry_points='''
            [console_scripts]
            gspack=gspack:create_autograder_from_console
        ''',

        zip_safe=False,
    )

