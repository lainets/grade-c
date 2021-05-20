# grade-c

[A+] grading container with C compilers. It contains:

* `make`
* `gcc`
* `g++`
* `valgrind`
* [gcheck]
* An optional utility script for gcheck (`gcheck.py` described below)

[gcheck]: https://github.com/lainets/gcheck
[A+]: https://github.com/apluslms/a-plus

## Tags

Images are tagged with gcc and grading-base versions in the format `<gcc>-<grading-base>`.
Version tag can also include `uN` meaning _update N_ where N is an increasing number.
The update part is used to indicate updates to the image, where software versions did not change.
For example, `8.3-3.1u1` includes gcc 8.3 on top of grading-base 3.1 and has one update after the first release.

# Container Config

The cmd can be either `/entrypoint/gcheck.py` for the functionality described below (only for gcheck), or what is described in [grading-base].

[grading-base]: https://github.com/apluslms/grading-base

# Using /entrypoint/gcheck.py

/entrypoint/gcheck.py is a script that handles compilation, execution, scoring, error handling and compiling HTML output for gcheck.

## CSS and JS files

The `gcheck.js` and `gcheck.css` files from the `static` folder should be included in your course material if you use the gcheck.py script. Put them in the static folder and include the following in the `layout.html` file:

```
<script type="text/javascript" async src="{{ pathto('<path>/<to>/gcheck.js', 1) }}" data-aplus></script>

<link rel="stylesheet" href="{{ pathto('<path>/<to>/gcheck.css', 1) }}" type="text/css" data-aplus />
```

## Config

It is configured using a `gcheck.yaml` or `gcheck.json` file at the root of the exercise directory (mount above).
The config file can have the following fields:

    <value>, <default>
        <explanation>

    max_points, None
        The maximum points given. Doesn't matter as the value is scaled to the A+ value anyway,
        So, this can be left out without worry.
    penalty_type, "multiplicative"
        one of "multiplicative", "cumulative", "mul", "cum", "m", "c".
        "multiplicative" means the penalties are multiplied e.g. -20% and -20% is (100%-20%)^2.
        "cumulative" means the penalties are added e.g. -20% and -20% is -40%
    penalties, { }
        penalties given for different things as a fraction e.g. 0.2 is -20%.
        Possible penalty types are "valgrind" and "warning".
        E.g. penalties: { valgrind: 0.2 }
    valgrind_options, [ "--track-origins=yes", "--leak-check=full" ]
        Options passed to valgrind.
    valgrind, False
        Whether to run valgrind or not.
    includedirs, ""
        A list or space separated string of include directories for compiling. Either absolute or relative to the exercise directory.
    testsource, None
        Test source file. Either absolute or relative to the exercise directory. If not specified, uses all *.cpp files found in testsourcedir
    testsourcedir, /exercise
        Test source file directory. Either absolute or relative to the exercise directory.
        Used only if testsource is not specified.
        All *.cpp files found in testsourcedir are used as test sources.
    CPPFLAGS, ""
        Flags for the compiler used for both c++ and c files.
        `-c` and include directories defined by includedirs are always appended.
    CFLAGS, -std=c99 -g -Wall -Wextra -Wno-missing-field-initializers
        Flags for the compiler used for both c files.
        `-std=c99` is appended if no other standard is specified.
    CXXFLAGS, -std=c++17 -g -Wall -Wextra -Wno-missing-field-initializers
        Flags for the compiler used for both c++ files.
        `-std=c++17` is appended if no other standard is specified.
    LDLIBS, ""
        Flags for the linker.
        `-l<GCHECK_LIB>` is always appended.
    LDFLAGS, ""
        Flags for the linker.
        `-L<GCHECK_LIB_DIR>` is always appended.
    TESTCPPFLAGS, ""
        Flags for the compiler used for the test sources.
        `-c -isystem <GCHECK_DIR>` is always appended.
    TESTCXXFLAGS, -std=c++17 -g -Wall
        Flags for the compiler used for the test sources.
        `-I<GCHECK_INCLUDE_DIR>` is always appended.
        `-std=c++17` is appended if no other standard is specified.

## Submitted files

Submitted files are assumed to be C++ or C files if they end in .cpp or .c, respectively. Other files are not compiled.

## Modifying the defaults and/or the html templates

1. Create a new image.
2. Replace the gcheck.env to change the default flags. Replace the files in the templates directory to change the HTML templates. To change anything else you need to modify the entry script.
3. Specify the new image for the exercise in A+.
