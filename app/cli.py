"""CLI pentru catalogul de note în DynamoDB (LocalStack).

Exemplu: python -m app.cli add --student S1 --course C1 --name "Rețele" --grade 9 --semester 2026-1
"""

import argparse
import sys

from app import db

COLUMNS = [
    ("student_id", "Student"),
    ("course_id", "Curs"),
    ("course_name", "Denumire"),
    ("grade", "Nota"),
    ("semester", "Semestru"),
    ("updated_at", "Actualizat"),
]


def print_table(rows):
    """Afișează rândurile ca tabel text simplu."""
    headers = [h for _, h in COLUMNS]
    data = [[str(r[k]) for k, _ in COLUMNS] for r in rows]
    widths = [max(len(x) for x in col) for col in zip(headers, *data)]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def line(cells):
        return "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths)) + " |"

    print(sep)
    print(line(headers))
    print(sep)
    for d in data:
        print(line(d))
    print(sep)


def cmd_init(args):
    db.create_table()
    print(f"Tabelul '{db.TABLE_NAME}' a fost creat (PK: student_id, SK: course_id).")


def cmd_add(args):
    g = db.add_grade(args.student, args.course, args.name, args.grade, args.semester)
    print("Notă adăugată:")
    print_table([g])


def cmd_get(args):
    g = db.get_grade(args.student, args.course)
    if g is None:
        print(f"Nu există nicio notă pentru studentul '{args.student}' la cursul '{args.course}'.")
        return 1
    print_table([g])


def cmd_list(args):
    grades = db.list_grades(args.student)
    if not grades:
        print(f"Studentul '{args.student}' nu are nicio notă.")
        return
    print(f"Notele studentului '{args.student}' ({len(grades)}):")
    print_table(grades)
    print(f"Media: {db.average(grades):.2f}")


def cmd_update(args):
    g = db.update_grade(args.student, args.course, args.grade)
    print("Notă actualizată:")
    print_table([g])


def cmd_delete(args):
    db.delete_grade(args.student, args.course)
    print(f"Nota studentului '{args.student}' la cursul '{args.course}' a fost ștearsă.")


def cmd_drop(args):
    db.delete_table()
    print(f"Tabelul '{db.TABLE_NAME}' a fost șters.")


def build_parser():
    p = argparse.ArgumentParser(prog="python -m app.cli", description="Catalog de note în DynamoDB pe LocalStack")
    sub = p.add_subparsers(dest="command", required=True)

    def cmd(name, func, help_, student=True, course=False):
        s = sub.add_parser(name, help=help_)
        if student:
            s.add_argument("--student", required=True, help="ID student, ex. S1")
        if course:
            s.add_argument("--course", required=True, help="ID curs, ex. C1")
        s.set_defaults(func=func)
        return s

    cmd("init", cmd_init, "creează tabelul Grades", student=False)

    s = cmd("add", cmd_add, "adaugă o notă (PutItem, refuză duplicatele)", course=True)
    s.add_argument("--name", required=True, help="denumirea cursului")
    s.add_argument("--grade", required=True, type=int, help="nota, întreg 1-10")
    s.add_argument("--semester", required=True, help="ex. 2026-1")

    cmd("get", cmd_get, "afișează o notă (GetItem)", course=True)
    cmd("list", cmd_list, "toate notele unui student + media (Query)")

    s = cmd("update", cmd_update, "modifică o notă existentă (UpdateItem)", course=True)
    s.add_argument("--grade", required=True, type=int, help="noua notă, întreg 1-10")

    cmd("delete", cmd_delete, "șterge o notă (DeleteItem)", course=True)
    cmd("drop", cmd_drop, "șterge tabelul Grades", student=False)
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
