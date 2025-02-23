# itermv
**itermv** is a command-line utility designed to simplify the renaming of multiple files in a directory. It provides flexible pattern matching using regular expressions (regex) and allows for advanced renaming options with capture groups. Additionally, `itermv` supports automatic name collision avoidance, making batch file renaming smooth and error-free.

## Log
There are some bugs.

The first is that if you create a chain of renaming that starts in a file that exists but the next item uses a file that does not exist then the renaming fails. For example, assume the only file in the cwd is `X` then
```
X -> Y
Y -> Z
Z -> X
```
which does absolutely nothing or if the last `X` was something else like `A` then the whole chain is equivalent to `X -> A`. The problem this brings up is that using a file with accumulated changes from this program itself, then temporary names may create a chain that runs into this problem. **The quick solution is to make it so that the `--verbose-export` flag prints the names prior to them being processed by the scheduler** (since this type of chain clearly requires the `--overlap` flag as well).

However, there is an extra problem; namely, these types of chains collide with the definition of solving overlapping file renaming. For example, look at the example, just above. What should happen if `Y` does exist in the cwd? **Is it safe to simply "sqash" the names that do not exist?** Z in this case. Furthermore, this invites the idea of non unique sets of either source names or target names. This violates the guarantee under which my current scheduling argorithm works. It would seem that this reducing algoirhtm would have to happen prior during the preparation of arguments. What is for sure is that my `FileEntry` would no longer be able to guarantee that its datamember represents a file that exists. The solution would be either a middle man approach, or allow dirty states in the `FileEntry` class.

This certainly complicates things. Is it worth it?

## Features
- **Flexible Renaming Methods**:
  - Use patterns with placeholders (`{name}`, `{ext}`, `{n}`, etc.) for dynamic renaming.
  - Leverage regex capture groups for fine-grained control.
  - Support for explicit rename lists or source-destination pairs.
- **Comprehensive File Selection**:
  - Filter files with regex or provide a list of filenames.
  - Options to exclude directories or include the program file itself.
- **Customizable Sorting**:
  - Sort files by name, size, or timestamps (creation, modification, or access time).
  - Reverse sorting for descending order.
- **Collision Handling**:
  - Automatically resolve naming conflicts with existing files.
- **Dry-Run Mode**:
  - Preview changes without altering any files.
- **Verbose Logging**:
  - See detailed outputs of renaming operations.
- **Other Features**:
  - Time-based placeholders (`{t}`, `{d}`).
  - Adjustable radix for numbering and custom time separators.
  - Quiet mode to suppress prompts.

## Requirements
Requires python 3.10 or newer (mostly because of match). Other than that there is no dependencies required! `itermv` is a self-contained utility that runs out of the box.

## Installation
As this utility is part of a monorepo, refer to the monorepo's [instructions for installation and setup](../README.md).

## Usage
The scripts works in a single directory. It has four replacement methods
```
itermv --replace-pattern PATTERN
itermv --rename-each REGEX PATTERN
itermv --rename-list DEST [DEST ...]
itermv --rename-pairs SRC DEST [SRC DEST ...]
```
and two selection methods
```
--regex REGEX
--file-list SRC [SRC ...]
```
At exception of `--rename-pairs` you can mix and match from either of them as it is convenient. `--rename-pairs` has its own source and destination file names so it simply ignores any selection method used. `--rename-list` in combination with `--file-list` is equivalent to doing to the same with `--rename-pairs` but they provide flexibility. The separate arguments are friendly with globbing patterns while the unified argument is useful for column formatted files or piping.

A `PATTERN` is a string formatted using Python native string interpolation. Capture groups from regex matches `{1}`, `{2}`, and so on. The zeroth group represents the whole match. The `--rename-each` argument ignores the capture groups from `--regex` and instead uses its own `REGEX` argument to get the capture groups.

Another important note about `--rename-each` is that currently it replaces ALL instances of the match in each filename. Currently there is no way to control that. This behavior may become default with an option to define max number of replacements. 

Finally, `SRC` and `DEST` are both plain text. However, you may activate `PATTERN` behavior if you use the `--no-plain-text` flag.

The following will describe the commands succinctly. For the full documentation consult the `--help` flag.

### Patterns
There are more options for the patterns than capture groups, and are the following:
- `{n}` or `{N}` a sequential number in the order specified (uppercase applies when radix is greater than 10).
- `{n0}` or `{N0}` a sequential number in the order specified padded with zeroes to largest integer.
- `{n:0Kd}` a sequential number in the order specified padded with zeroes to a length of K characters.
- `{a}` or `{A}` alphabetical counting.
- `{d}` the date in yyyy-mm-dd format using specified separator.
- `{t}` time in hh-mm-ss format using specified separator.
- `{t<c,m,u>}` time in hh-mm-ss-ccmuuu format where c, m, and u stand for are centi- mili- and micro-seconds respectively.
- `{ext}` the extension of the original file (including the dot).
- `{name}` the name of the original file without the extension.
- `{<number>}` the string matched by REGEX where 0 is the entire match, and any subsequent number identifies a capturing group.
- `{unixt}` unix time of the last modification.

### Sorting Options
These are useful in combination with sequential numbering such as `{n0}`, alphabetical counting `{a}` since they increase in the order they are "dispatched".
- `-s {mtime,atime,name,ctime,size}`, `--sort {mtime,atime,name,ctime,size}` Allows sorting files by some criterion.
- `-r`, `--reverse-sort` If present sorting is reversed.

For full documentation on all the flags see the command help (`-h`).

### Other Options
- `-i SOURCE_DIR`, `--source-dir SOURCE_DIR` source directory. If omitted the current working directory will be used.
- `-n NUMBER`, `--start-number NUMBER` Specifies the initial value (0 is default).
- `-d`, `--dry-run` Does not change anything. Useful in combination with verbose.
- `-O`, `--overlap` Allow and automatically resolve collisions with existing names.
- `-F`, `--include-self` If present regex selection considers itself.
- `-X`, `--exclude-dir` If present regex selection ignores directories.
- `-v`, `--verbose` Lists all names to be changed.
- `-t {ctime,mtime,atime}`, `--time-stamp-type {ctime,mtime,atime}` Specifies the type of the time stamps.
- `-T SEPARATOR`, `--time-separator SEPARATOR` Specifies the separator used for the time stamps.
- `-k NUMBER`, `--radix NUMBER` Specifies the radix of the counting (10 is default).
- `-N`, `--no-plain-text` Enables pattern replacement in DEST arguments.
- `-q`, `--quiet` If present all prompts are skipped.
- `-h`, `--help` show this help message and exit
- `--version` show program's version number and exit

### Examples
#### Pattern replacement
Change the extension of all .txt files in the current directory using regex to capture parts of the name and reformat them
```bash
itermv -R '(\d+)-(.+)\.txt' -p '{2}-{1}.md'
```

#### Individual name replacement

The following renames all files in the current directory by swapping all non-overlapping instances of letters followed by a hyphen and numbers.
```bash
itermv -Ne '([A-Za-z]+)-(\d+)' '{2}-{1}'
```

#### Collision avoidance
All the previous ones will fail if there are cycles of any sort or self references between source and destination names. The following showcases the collision avoidance
```bash
itermv -OL A B C X Y Z -l B C D Y Z X
```
This will not use any temporary name because it automatically recognizes that it can use `A` as a temporary name since it will overridden and not re-added. If there is only pure cycles it will use at most one randomly generated name as temporary.
