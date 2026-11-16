"""CLI pentru gestionarea task-urilor în DynamoDB (LocalStack).

Exemplu: python -m app.cli add ana "Citește documentația DynamoDB"
"""

import argparse
import sys

from app import db


def print_task(t):
    mark = "[x]" if t["status"] == "done" else "[ ]"
    print(f"{mark} {t['task_id']}  {t['title']}  (status: {t['status']}, creat: {t['created_at']})")


def cmd_init(args):
    db.create_table()
    print(f"Tabelul '{db.TABLE_NAME}' a fost creat (PK: user_id, SK: task_id).")


def cmd_add(args):
    t = db.add_task(args.user_id, args.title)
    print(f"Task adăugat pentru '{args.user_id}':")
    print_task(t)


def cmd_get(args):
    t = db.get_task(args.user_id, args.task_id)
    if t is None:
        print(f"Task-ul '{args.task_id}' nu există pentru '{args.user_id}'.")
        return 1
    print_task(t)


def cmd_list(args):
    tasks = db.list_tasks(args.user_id)
    if not tasks:
        print(f"Niciun task pentru '{args.user_id}'.")
        return
    print(f"Task-urile lui '{args.user_id}' ({len(tasks)}):")
    for t in tasks:
        print_task(t)


def cmd_complete(args):
    t = db.complete_task(args.user_id, args.task_id)
    print("Task marcat ca finalizat:")
    print_task(t)


def cmd_delete(args):
    db.delete_task(args.user_id, args.task_id)
    print(f"Task-ul '{args.task_id}' a fost șters.")


def cmd_drop(args):
    db.delete_table()
    print(f"Tabelul '{db.TABLE_NAME}' a fost șters.")


def build_parser():
    p = argparse.ArgumentParser(prog="python -m app.cli", description="Task-uri în DynamoDB pe LocalStack")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="creează tabelul Tasks").set_defaults(func=cmd_init)

    s = sub.add_parser("add", help="adaugă un task")
    s.add_argument("user_id")
    s.add_argument("title")
    s.set_defaults(func=cmd_add)

    for name, func, help_ in [
        ("get", cmd_get, "afișează un task"),
        ("complete", cmd_complete, "marchează un task ca 'done' (UpdateItem)"),
        ("delete", cmd_delete, "șterge un task (DeleteItem)"),
    ]:
        s = sub.add_parser(name, help=help_)
        s.add_argument("user_id")
        s.add_argument("task_id")
        s.set_defaults(func=func)

    s = sub.add_parser("list", help="listează task-urile unui user (Query)")
    s.add_argument("user_id")
    s.set_defaults(func=cmd_list)

    sub.add_parser("drop", help="șterge tabelul Tasks").set_defaults(func=cmd_drop)
    return p


def main(argv=None):
    # Consola Windows poate folosi o codificare fără diacritice.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args) or 0
    except db.DbError as e:
        print(f"Eroare: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
