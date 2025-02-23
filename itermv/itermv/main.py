from itermv.helpers import (
    askUser,
    createValidSchedule,
    createValidTasklist,
    getArguments,
    getFileNames,
    printIntro,
    printOutro,
    printSchedule,
    renameBySchedule,
    undoSchedule,
)


def main():
    success = False
    args = getArguments()
    included, ignored = getFileNames(args)

    printIntro(args)

    if len(included) > 0:
        if args.overlap:
            schedule = createValidSchedule(included)
        else:
            schedule = createValidTasklist(included)

        strSelected = (
            [(a.name, b.name) for a, b in included] if args.verbose_export else schedule
        )
        strIgnored = [(a.name, b.name) for a, b in ignored]
        printSchedule(strSelected, strIgnored, args)

        if args.dry_run and askUser("Dummy prompt", args):
            success = True
        elif askUser("Do you want to proceed? [Y]es/[N]o: ", args):
            success, tasklog = renameBySchedule(schedule)
            if not success and askUser(
                "Do you want to undo partial changes? [Y]es/[N]o: ", args
            ):
                undoSchedule(tasklog)
                success = True

    printOutro(included, ignored, args, success)
