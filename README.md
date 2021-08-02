# grade-c

[A+] grading container with C compilers. It contains:

* `make`
* `gcc`
* `g++`
* `valgrind`
* [gcheck]
* An optional utility script for gcheck and others (`/entrypoint/run.py` described below)

[gcheck]: https://github.com/lainets/gcheck
[A+]: https://github.com/apluslms/a-plus

## Tags

Images are tagged with gcc and grading-base versions in the format `<gcc>-<grading-base>`.
Version tag can also include `uN` meaning _update N_ where N is an increasing number.
The update part is used to indicate updates to the image, where software versions did not change.
For example, `8.3-3.1u1` includes gcc 8.3 on top of grading-base 3.1 and has one update after the first release.

The images that have the gcheck script installed use the version number format `<gcc>-<gcheck>-<grading-base>`,
for example, `8.3-1.0-3.4`.

# Container Config

The cmd can be either `/entrypoint/run.py` for the functionality described below, or what is described in [grading-base].

[grading-base]: https://github.com/apluslms/grading-base

# Using /entrypoint/run.py

/entrypoint/run.py is a script that handles compilation, execution, scoring, error handling and compiling HTML output. It is extensible using a Runner python class (see util.py and gcheck/run.py).

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

    runner, "/gcheck/run.py"
        The python file that contains the Runner class used for running and grading the program.
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
        A list or space separated string of test sources to be compiled. Either absolute or relative to the exercise directory.
    testsourcedir, None ("/exercise" if neither this or testsource is specified)
        A list or space separated string of directories of test sources to be compiled. Either absolute or relative to the exercise directory.
        All *.cpp and *.c files found in these directories are used as test sources.
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
        Flags for the compiler used for the .cpp test sources.
        `-c -isystem <GCHECK_DIR>` is always appended.
    TESTCFLAGS, ""
        Flags for the compiler used for the .c test sources.
        `-std=c99` is appended if no other standard is specified.
    TESTCXXFLAGS, -std=c++17 -g -Wall
        Flags for the compiler used for the test sources.
        `-I<GCHECK_INCLUDE_DIR>` is always appended.
        `-std=c++17` is appended if no other standard is specified.
    timeout, 180
        Timeout in seconds. The gcheck process is killed if it takes longer than this.
        Set to null for no timeout.

In addition, it is possible to append a '+' or '-' to add or remove flags from the defaults. E.g. `CFLAGS+: -Werror` adds the `-Werror` flag to the default `-std=c99 -g -Wall -Wextra -Wno-missing-field-initializers` flags. `CFLAGS-: -Wall` would then remove the `-Wall` flag from the defaults. This only works for options that take a list, i.e. the compilation flags and `includedirs`.

## Submitted files

Submitted files are assumed to be C++ or C files if they end in .cpp or .c, respectively. Other files are not compiled.

## Modifying the defaults and/or the html templates

1. Create a new image.
2. Replace the gcheck.env to change the default flags. Replace the files in the templates directory to change the HTML templates. To change anything else you need to modify the entry script.
3. Specify the new image for the exercise in A+.

## Making your own Runner

Take the gcheck/run.py as an example, and work from there. You can either create a new docker image with the new runner or mount it to the grade-c and use `/exercise/...` to refer to the runner in the config.
