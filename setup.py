from pathlib import Path

from setuptools import setup, find_packages

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    src_dir = base_dir / 'src'

    about = {}
    with (src_dir / "gspack" / "__about__.py").open() as f:
        exec(f.read(), about)

    install_requirements = [t.strip() for t in open("requirements.txt", 'r').readlines()]

    test_requirements = [
        'pytest',
        'pandas'
    ]

    doc_requirements = []

    setup(
        name=about['__title__'],
        version=about['__version__'],

        description=about['__summary__'],
        long_description=about['__long_description__'],
        long_description_content_type="text/markdown",
        license=about['__license__'],
        url=about["__uri__"],

        author=about["__author__"],
        author_email=about["__email__"],

        package_dir={'': 'src'},
        packages=find_packages(where='src'),

        package_data={
            "gspack": ["src/gspack/templates/run_autograder",
                       "src/gspack/templates/setup.sh",
                       "src/gspack/templates/gs_debug.sh",
                       ]
        },
        include_package_data=True,

        python_requires='>=3.7',
        install_requires=install_requirements,
        tests_require=test_requirements,
        extras_require={
            'docs': doc_requirements,
            'test': test_requirements,
            'dev': [doc_requirements, test_requirements]
        },
        entry_points='''
            [console_scripts]
            gspack=gspack:create_autograder_from_terminal
            gsgrade=gspack:grade_locally_from_terminal
            gsgrade_gradescope=gspack:grade_on_gradescope
        ''',

        zip_safe=False,
    )
    print("\n[NB] For MATLAB support: \n "+
          "0) Make sure you have MATLAB installed. \n " +
          "1) Install MATLAB Engine Python API. Instruction: \n " +
          " -> https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html \n "
          f"2) Obtain Gradescope MATLAB Credentials directory from your department. \n "
          f" -> For Applied Math at UW: email {about['__author__']} ({about['__email__']}) to get the instructions.")
