# grade-c

A+ grading container with C compilers. It contains:

* `make`
* `gcc`
* `g++`
* `valgrind`

## Tags

Images are tagged with gcc and grading-base versions in the format `<gcc>-<grading-base>`.
Version tag can also include `uN` meaning _update N_ where N is an increasing number.
The update part is used to indicate updates to the image, where software versions did not change.
For example, `8.3-3.1u1` includes gcc 8.3 on top of grading-base 3.1 and has one update after the first release.

