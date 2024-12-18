from itermv.components import (
    AlphaCounter,
    ArgsWrapper,
    FileEntry,
    NewFile,
    RadixCounter,
    TimeStampType,
    NamePattern,
)
from itermv.utils import isTopLevelPath

import os
import re
import datetime
from typing import Any
from collections.abc import Callable


def askUser(args: ArgsWrapper):
    print()
    if args.quiet:
        return True
    if args.dry_run:
        print("Prompt skipped by dry-run...")
        return True
    MSG = "Do you want to proceed? [Y]es/[N]o: "
    userInput = input(MSG)
    while len(userInput) != 1 or userInput not in "YyNn":
        userInput = input(MSG)
    return len(userInput) > 0 and userInput in "Yy"


def printNameMapping(
    schedule: list[tuple[FileEntry, NewFile]],
    ignored: list[tuple[FileEntry, NewFile]],
    args: ArgsWrapper,
):
    if args.dry_run:
        print("-- DRY RUN")
    if args.verbose:
        print(f"The common directory is: {args.source_dir.path}\n")

        colSize = [0, 0]
        for o, n in schedule + ignored:
            colSize[0] = max(colSize[0], len(o.name))
            colSize[1] = max(colSize[1], len(n.name))

        if len(schedule):
            print("The following files will be changed:")
        for o, n in schedule:
            print(f"    {o.name:{colSize[0]}} -> {n.name:{colSize[1]}}")

        if len(ignored):
            print("The following files will be ignored:")
        for o, n in ignored:
            print(f"    {o.name:{colSize[0]}} -> {n.name:{colSize[1]}}")

    elif not args.quiet:
        print(f"{len(schedule)} files will be changed")
        print(f"{len(ignored)} files will be ignored")


def printChangesMade(schedule: list[tuple[str, str]], args: ArgsWrapper):
    schedule = [(os.path.basename(o), os.path.basename(n)) for o, n in schedule]
    if args.verbose:
        print("Changes performed:")
        colSize = [0, 0]
        for o, n in schedule:
            colSize[0] = max(colSize[0], len(o))
            colSize[1] = max(colSize[1], len(n))
        for o, n in schedule:
            print(f"    {o:{colSize[0]}} -> {n:{colSize[1]}}")
    elif not args.quiet:
        print(f"{len(schedule)} name changes performed")

    if args.dry_run:
        print("DRY RUN --")


def getTimeFormats(file: FileEntry, ttype: TimeStampType, separator: str):
    entries = {}
    sep = separator

    unixstamp = None
    if ttype.byAccessDate():
        unixstamp = file.atime
    if ttype.byModifyDate():
        unixstamp = file.mtime
    if ttype.byMetaDate():
        unixstamp = file.ctime

    filetime = datetime.datetime.fromtimestamp(unixstamp)
    xsec = filetime.microsecond
    filetime = filetime.replace(microsecond=0)

    entries["unixt"] = unixstamp
    entries["d"] = str(filetime.date()).replace("-", sep)
    basetime = str(filetime.time()).replace(":", sep)
    entries["t"] = basetime

    entries["tu"] = f"{basetime}{sep}{xsec:06d}"
    xsec //= 1000
    entries["tm"] = f"{basetime}{sep}{xsec:03d}"
    xsec //= 10
    entries["tc"] = f"{basetime}{sep}{xsec:02d}"

    return entries


def internalCollisions(ifiles: list[str], ofiles: list[str]):
    return set(ifiles).intersection(set(ofiles))


def externalCollisions(ofiles: list[NewFile], innerset: set[FileEntry]):
    outSet = set()
    for file in ofiles:
        if os.path.exists(file.path) and file.path not in innerset:
            outSet.add(file.name)

    return outSet


def getRepeats(files: list, getname: Callable[[Any], str]):
    rset = set()
    fset = set()
    for file in files:
        file = getname(file)
        if file in fset:
            rset.add(file)
        fset.add(file)
    return rset


def inlineReplacer(pattern: NamePattern, **options):
    def inrepl(match: re.Match):
        matches = [match.group(0)]
        matches.extend(match.groups())
        matches = [m if m is not None else "" for m in matches]
        return pattern.evalPattern(*matches, **options)

    return inrepl


def expandPatterns(
    entries: list[tuple[FileEntry, NamePattern]],
    regex: str | None,
    args: ArgsWrapper,
    useRepl: bool,
):
    outFiles: list[NewFile] = []
    spath = args.source_dir.path
    indexStart = args.start_number
    alpha = AlphaCounter(indexStart)
    index = RadixCounter(args.radix, indexStart)
    largestNum = RadixCounter(args.radix, indexStart + len(entries))
    padsize = len(largestNum.str())

    for file, pattern in entries:
        idx = index.str(False)
        idxUp = index.str(True)
        timeEntries = getTimeFormats(file, args.time_stamp_type, args.time_separator)
        matches = []
        rgxMatch = None

        nameopts = {
            "n": idx,
            "N": idxUp,
            "n0": f"{idx:0>{padsize}}",
            "N0": f"{idxUp:0>{padsize}}",
            "a": alpha.str(upper=False),
            "A": alpha.str(upper=True),
            "ext": file.extension,
            "name": file.noextname,
            **timeEntries,
        }

        if regex is not None and not useRepl:
            rgxMatch = re.search(regex, file.name)
        elif regex is not None:
            destName = re.sub(regex, inlineReplacer(pattern, **nameopts), file.name)
            if not isTopLevelPath(spath, destName):
                args.arg_error("Destination must also result in a top level path")
            outFiles.append(NewFile(os.path.join(spath, os.path.basename(destName))))
            continue

        if rgxMatch is None and regex is not None:
            outFiles.append(NewFile(os.path.join(spath, file.name)))
            continue
        elif rgxMatch is not None:
            # get the full match and capture groups
            matches = [rgxMatch.group(0)]
            matches.extend(rgxMatch.groups())

        alpha.increase()
        index.increase()

        matches = [m if m is not None else "" for m in matches]
        destName = pattern.evalPattern(*matches, **nameopts)
        if not isTopLevelPath(spath, destName):
            args.arg_error("Destination must also result in a top level path")
        destName = NewFile(os.path.join(spath, os.path.basename(destName)))
        outFiles.append(destName)

    return outFiles


def getFileNames(args: ArgsWrapper):
    inFiles = args.get_sources()

    if not args.include_self:
        inFiles = [f for f in inFiles if f.path != __file__]

    if inFiles is None:
        args.arg_error("fatal error: input file list is None")

    if getRepeats(inFiles, lambda f: f.name):
        args.arg_error("fatal error: input files are guaranteed to be unique.")

    if not args.is_source_ordered():
        if args.sort.byName():
            inFiles = sorted(
                inFiles, key=lambda file: file.name, reverse=args.reverse_sort
            )
        if args.sort.byAccessDate():
            inFiles = sorted(
                inFiles, key=lambda file: file.atime, reverse=args.reverse_sort
            )
        if args.sort.byModifyDate():
            inFiles = sorted(
                inFiles, key=lambda file: file.mtime, reverse=args.reverse_sort
            )
        if args.sort.bySize():
            inFiles = sorted(
                inFiles, key=lambda file: file.size, reverse=args.reverse_sort
            )

    destGen = args.get_destinations()
    outFiles: list[NewFile] = []

    match args.get_dest_type():
        case ArgsWrapper.OUT_PATTERN:
            # destGen: NamePattern
            outFiles = expandPatterns(
                [(f, destGen) for f in inFiles], args.regex, args, False
            )
        case ArgsWrapper.OUT_REGEX_INLINE:
            # destGen: tuple(str, NamePattern)
            rgx, patt = destGen
            outFiles = expandPatterns([(f, patt) for f in inFiles], rgx, args, True)
        case ArgsWrapper.OUT_PAIR_LIST | ArgsWrapper.OUT_FILE_LIST:
            if not args.no_plain_text:
                # destGen: list[NewFile]
                outFiles = destGen
            else:
                # destGen: list[NamePattern]
                outFiles = expandPatterns(
                    [(f, p) for f, p in zip(inFiles, destGen)], None, args, False
                )

    if len(inFiles) != len(outFiles):
        args.arg_error("Number of entries in source and destination must match.")

    oreps = getRepeats(outFiles, lambda f: f.name)
    if oreps:
        args.arg_error(f"Generated output files are not unique: {oreps}")

    intcoll = internalCollisions((f.path for f in inFiles), (f.path for f in outFiles))
    extcoll = externalCollisions(outFiles, intcoll)

    if not args.overlap and intcoll:
        args.arg_error(f"Try using --overlap. There are internal collisions: {intcoll}")
    if extcoll:
        args.arg_error(f"There are collisions with files not selected: {extcoll}")

    included: list[tuple[FileEntry, NewFile]] = []
    ignored: list[tuple[FileEntry, NewFile]] = []
    for ifile, ofile in zip(inFiles, outFiles):
        if ifile.parent != ofile.parent:
            args.arg_error(
                f"Cannot change path of output file\n{ifile.path} {ofile.path}"
            )
        if ifile.path == ofile.path:
            ignored.append((ifile, ofile))
        else:
            included.append((ifile, ofile))

    return included, ignored
