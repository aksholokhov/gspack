# gspack
Programming Assignment Packager for GradeScope Auto Grader.

## Goal
This tool converts your programming assignment solution into a GradeScope Auto-Grader compatible archive. The goal of
this project is to make it easier for an instructor to create a GradeScope programming assignments. In particular,

## Installation

To install `gspack` you need to clone this repo to your machine

```shell script
$ git clone https://github.com/aksholokhov/gspack
```
and then to install it:
```shell script
$ cd gspack 
$ python setup.py install
```
If you want to install it in the developer mode:
```shell script
$ python setup.py develop
```

## Usage 
In order to make your assignment `gspack`-compatible you need to include a brief instruction of your test suite 
and put it to the `test_suite` variable.
 
### Example
Suppose you are writing a solution for "Homework 0" where students are supposed to familiarize themselves with the
 basics of Python:

```python
import numpy as np

x = 10
y = -2
z = np.pi

A1 = x + y - z
A2 = x**3
A3 = np.arange(12).reshape((3, 4))
```
Now you want to make the rubric based on variables `A1`, `A2` and `A3`. All you need to do is to define the following 
dictionary in your solution file:
```python
test_suite = {
    "Addition": {
        "variable_name": "A1",
        "description": "Evaluating x + y - z",
        "score": 1,
        "hint": "Check your signs"
    },
    "Power": {
        "variable_name": "A2",
        "description": "Evaluating x^3",
        "score": 1
    },
    "Arrange": {
        "variable_name": "A3",
        "rtol": 1e-5,
        "atol": 1e-2,
        "score": 3
    }
}
```
This will create three tests "Addition", "Power", and "Arrange", each, being done correctly, will give to a student 
1, 1, and 3 points respectively, with the total of 5 points. In the last part we also define custom relative and absolute
tolerances (sometimes it's necessary for taking round-off and numerical errors into account properly). 

Now we launch the `gspack`: in terminal, type
```shell script
$ gspack --solution path/to/the/hw0_solution.py
```
and you should see something like this:
```shell script
Found the solution file:
-> /from/root/path/to/the/hw0_solution.py
Found the test suite configuration:
-> Addition: ok
-> Power: ok
-> Arrange: ok
Archive created successfully:
-> /from/root/path/to/the/autograder.zip
```
The `autograder.zip` will be in the same directory to your `hw0_solution.py`. This archive contains all necessary
structures, files, and instructions for GradeScope AutoGrader, so you're good to go create a new GradeScope programming
assignment and to upload this archive when prompted. 

Next, suppose a student wrote the following solution for this assignment: 
```python
import numpy as np

x = 10
y = -2
z = np.pi

A1 = x + y + z
A2 = x**3
A3 = np.arange(12).reshape((4, 3))
```

The first part is not right because of the second sign, the second part is right, and the third part is okay
but the transposition is wrong. 

When this solution is submitted, the student should see something like this:

### Formal Syntax
Formally, the `test_suite` instruction has the following syntax:

```python
test_suite = {
    "<test_name>": {                                # Required string. <test_name> is whatever string you want.
        "variable_name": "<variable_name>",         # Required string. Substitute the name of the variable to check.
        "score": <score>,                           # Optional int, default = 1. How many points to give for this part. 
        "description": "<description>",             # Optional string. Description of the test, appears in the test title.
        "hint": "<hint>",                           # Optional string. Appears when a student does this part wrong.
        "rtol": <rtol>,                             # Optional float, default = 1e-8, relative tolerance.
        "atol": <atol>,                             # Optional float, default = 1e-5, absolute tolerance.
    }
}
```

For each test, the grading system will go through the following list of checks:
1. Is this variable defined in the submitted solution? 
2. If it exists, does it have the right type?
3. If the type is right, do the dimmensions match to what's expected?
4. Does the answer contain any NaNs?
5. If everything above is okay, does the answer pass the tolerance requirements?

For the later one, the `numpy.allclose` function is used:
```shell script
passed = np.allclose(student_answer, solution_answer, rtol=rtol, atol=atol)
```

## Q&A
**Q**: What if my, as well as students',  script needs extra files, such as datasets, to work?

**A**: You can list these files in the variable `extra_files`:
```python
extra_files = ["test_data.csv", "train_data.csv"]
``` 
`gspack` expects them to be in the same directory as the solution script. It will add them to the `autograder.csv` 
and will place them accordingly when grading students submissions. 