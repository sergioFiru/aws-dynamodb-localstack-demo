# DynamoDB pe LocalStack — proiect demo

Prototip care demonstrează **Amazon DynamoDB rulat local cu LocalStack**: o aplicație Python (boto3) de tip catalog de note pentru studenți, cu operații CRUD, plus aceleași operații executate cu AWS CLI.

- **DynamoDB** este baza de date NoSQL de tip cheie-valoare/document oferită de AWS, complet administrată; datele sunt organizate în tabele, iar fiecare element este identificat printr-o cheie primară (partition key + opțional sort key).
- **LocalStack** este un emulator care rulează serviciile AWS (DynamoDB, S3, Lambda etc.) local, într-un container Docker, pe portul `4566`. Codul scris pentru AWS funcționează neschimbat, doar cu `endpoint_url` îndreptat spre LocalStack — fără cont AWS și fără costuri.

## Cuprins

1. [Cerințe](#1-cerințe)
2. [Instalare](#2-instalare)
3. [Pornire LocalStack](#3-pornire-localstack)
4. [Configurare](#4-configurare)
5. [Utilizare pas cu pas (CLI-ul aplicației)](#5-utilizare-pas-cu-pas-cli-ul-aplicației)
6. [Aceleași operații cu AWS CLI](#6-aceleași-operații-cu-aws-cli)
7. [Rulare teste](#7-rulare-teste)
8. [Oprire și curățare](#8-oprire-și-curățare)
9. [Alternativă: imaginea nouă cu token](#9-alternativă-imaginea-nouă-cu-token)
10. [Depanare](#10-depanare)
11. [Limitări](#11-limitări)
12. [Structura proiectului](#12-structura-proiectului)

## Modelul de date

Aplicația este un **catalog de note pentru studenți**, cu tabelul **`Grades`**:

| Atribut       | Tip | Rol                                      |
|---------------|-----|------------------------------------------|
| `student_id`  | S   | **partition key** (HASH), ex. `S1`       |
| `course_id`   | S   | **sort key** (RANGE), ex. `C1`           |
| `course_name` | S   | denumirea cursului                       |
| `grade`       | N   | nota, număr întreg între 1 și 10         |
| `semester`    | S   | semestrul, ex. `2026-1`                  |
| `updated_at`  | S   | data ultimei modificări, ISO 8601 UTC    |

Cheia primară compusă (`student_id`, `course_id`) înseamnă că un student are cel mult o notă per curs, iar toate notele unui student stau în aceeași partiție și pot fi citite cu un singur `Query`.

Operații DynamoDB folosite: `CreateTable`, `PutItem` (cu `ConditionExpression attribute_not_exists` — refuză duplicatele), `GetItem`, `Query` (pe partition key, nu `Scan`), `UpdateItem` (cu `ConditionExpression attribute_exists`), `DeleteItem`, `DeleteTable`. Media notelor se calculează în Python, pentru că DynamoDB nu are funcții de agregare (`AVG`, `SUM`).

## 1. Cerințe

| Instrument | Versiune | Verificare |
|---|---|---|
| Docker (Docker Desktop pe Windows/macOS) cu Docker Compose v2 | testat cu Docker 28.2.2 | `docker --version` și `docker compose version` |
| Python | 3.11 sau mai nou (testat cu 3.11.15) | `python --version` |
| Git | orice versiune recentă | `git --version` |
| AWS CLI | **opțional**, doar pentru secțiunea 6 | `aws --version` |

> Docker Desktop trebuie să fie **pornit** (iconița din system tray / bara de meniu) înainte de pașii de mai jos.

## 2. Instalare

```bash
git clone https://github.com/sergioFiru/aws-dynamodb-localstack-demo.git
cd aws-dynamodb-localstack-demo
python -m venv .venv
```

Activează mediul virtual (alege varianta pentru sistemul tău):

```bash
# Linux / macOS
source .venv/bin/activate

# Windows - PowerShell
.venv\Scripts\Activate.ps1

# Windows - Git Bash
source .venv/Scripts/activate
```

> Pe Windows, dacă PowerShell refuză scriptul de activare, rulează o dată: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
> Pe unele sisteme Linux/macOS comanda este `python3` în loc de `python`.

Instalează dependențele (boto3 și pytest):

```bash
pip install -r requirements.txt
```

Output (ultima linie):

```
Successfully installed boto3-1.44.3 botocore-1.44.3 colorama-0.4.6 iniconfig-2.3.1 jmespath-1.1.0 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.2.0 python-dateutil-2.9.0.post0 s3transfer-0.19.3 six-1.17.0 urllib3-2.8.0
```

## 3. Pornire LocalStack

```bash
docker compose up -d
```

```
 Network aws-dynamodb-localstack-demo_default  Creating
 Network aws-dynamodb-localstack-demo_default  Created
 Container localstack-dynamodb  Creating
 Container localstack-dynamodb  Created
 Container localstack-dynamodb  Starting
 Container localstack-dynamodb  Started
```

La prima pornire Docker descarcă imaginea `localstack/localstack:4.12` (~1,9 GB pe disc), deci poate dura câteva minute. Așteaptă până când coloana `STATUS` arată **`(healthy)`** (de obicei 5–15 secunde):

```bash
docker compose ps
```

```
NAME                  IMAGE                        COMMAND                  SERVICE      CREATED         STATUS                   PORTS
localstack-dynamodb   localstack/localstack:4.12   "docker-entrypoint.sh"   localstack   8 seconds ago   Up 7 seconds (healthy)   0.0.0.0:4566->4566/tcp, [::]:4566->4566/tcp
```

Opțional, verifică direct starea serviciilor (DynamoDB trebuie să fie `available`, iar ediția `community`, adică fără token):

```bash
curl -s http://localhost:4566/_localstack/health
```

```
{"services": {"acm": "disabled", "apigateway": "disabled", "cloudformation": "disabled", "cloudwatch": "disabled", "config": "disabled", "dynamodb": "available", "dynamodbstreams": "available", "ec2": "disabled", "es": "disabled", "events": "disabled", "firehose": "disabled", "iam": "disabled", "kinesis": "available", "kms": "disabled", "lambda": "disabled", "logs": "disabled", "opensearch": "disabled", "redshift": "disabled", "resource-groups": "disabled", "resourcegroupstaggingapi": "disabled", "route53": "disabled", "route53resolver": "disabled", "s3": "disabled", "s3control": "disabled", "scheduler": "disabled", "secretsmanager": "disabled", "ses": "disabled", "sns": "disabled", "sqs": "disabled", "ssm": "disabled", "stepfunctions": "disabled", "sts": "disabled", "support": "disabled", "swf": "disabled", "transcribe": "disabled"}, "edition": "community", "version": "4.12.0"}
```

> **De ce versiunea 4.12?** Din martie 2026, `localstack/localstack:latest` (și tag-urile noi `2026.x`) cer `LOCALSTACK_AUTH_TOKEN`. Tag-ul fixat `4.12` (decembrie 2025) este imaginea community care pornește **fără token**. Pentru imaginea nouă vezi [secțiunea 9](#9-alternativă-imaginea-nouă-cu-token).

## 4. Configurare

Nu e nevoie de nicio configurare pentru varianta implicită. Aplicația citește următoarele variabile de mediu, toate cu valori implicite:

| Variabilă | Implicit | Descriere |
|---|---|---|
| `DYNAMODB_ENDPOINT` | `http://localhost:4566` | adresa LocalStack |
| `AWS_DEFAULT_REGION` | `us-east-1` | regiunea |
| `AWS_ACCESS_KEY_ID` | `test` | credențiale dummy — LocalStack acceptă orice valoare |
| `AWS_SECRET_ACCESS_KEY` | `test` | idem |
| `TABLE_NAME` | `Grades` | numele tabelului |

Exemplu de suprascriere:

```bash
# Linux / macOS / Git Bash
export TABLE_NAME=GradesDemo

# Windows - PowerShell
$env:TABLE_NAME = "GradesDemo"
```

Fișierul `.env` (pornind de la `.env.example`) este folosit **doar** de Docker Compose, pentru alternativa cu token (secțiunea 9).

## 5. Utilizare pas cu pas (CLI-ul aplicației)

Toate comenzile se rulează din rădăcina proiectului, cu mediul virtual activat și LocalStack pornit. Output-urile de mai jos sunt **reale**, copiate dintr-o rulare de test (doar valorile din coloana `Actualizat` vor diferi la tine).

### Ajutor

```bash
python -m app.cli --help
```

```
usage: python -m app.cli [-h] {init,add,get,list,update,delete,drop} ...

Catalog de note în DynamoDB pe LocalStack

positional arguments:
  {init,add,get,list,update,delete,drop}
    init                creează tabelul Grades
    add                 adaugă o notă (PutItem, refuză duplicatele)
    get                 afișează o notă (GetItem)
    list                toate notele unui student + media (Query)
    update              modifică o notă existentă (UpdateItem)
    delete              șterge o notă (DeleteItem)
    drop                șterge tabelul Grades

options:
  -h, --help            show this help message and exit
```

Fiecare comandă are propriul ajutor, de ex.:

```bash
python -m app.cli add --help
```

```
usage: python -m app.cli add [-h] --student STUDENT --course COURSE --name
                             NAME --grade GRADE --semester SEMESTER

options:
  -h, --help           show this help message and exit
  --student STUDENT    ID student, ex. S1
  --course COURSE      ID curs, ex. C1
  --name NAME          denumirea cursului
  --grade GRADE        nota, întreg 1-10
  --semester SEMESTER  ex. 2026-1
```

### 5.1 `init` — creare tabel (CreateTable)

```bash
python -m app.cli init
```

```
Tabelul 'Grades' a fost creat (PK: student_id, SK: course_id).
```

### 5.2 `add` — adăugare note (PutItem)

Date de test: **2 studenți** (`S1`, `S2`) și **3 cursuri** (`C1` Rețele, `C2` Baze de date, `C3` Programare).

| Student | C1 Rețele | C2 Baze de date | C3 Programare |
|---------|-----------|-----------------|---------------|
| S1      | 9         | 8               | 10            |
| S2      | 7         | —               | 9             |

```bash
python -m app.cli add --student S1 --course C1 --name "Rețele" --grade 9 --semester 2026-1
python -m app.cli add --student S1 --course C2 --name "Baze de date" --grade 8 --semester 2026-1
python -m app.cli add --student S1 --course C3 --name "Programare" --grade 10 --semester 2026-1
python -m app.cli add --student S2 --course C1 --name "Rețele" --grade 7 --semester 2026-1
python -m app.cli add --student S2 --course C3 --name "Programare" --grade 9 --semester 2026-1
```

```
Notă adăugată:
+---------+------+----------+------+----------+----------------------+
| Student | Curs | Denumire | Nota | Semestru | Actualizat           |
+---------+------+----------+------+----------+----------------------+
| S1      | C1   | Rețele   | 9    | 2026-1   | 2026-11-16T20:53:18Z |
+---------+------+----------+------+----------+----------------------+
Notă adăugată:
+---------+------+--------------+------+----------+----------------------+
| Student | Curs | Denumire     | Nota | Semestru | Actualizat           |
+---------+------+--------------+------+----------+----------------------+
| S1      | C2   | Baze de date | 8    | 2026-1   | 2026-11-16T20:53:20Z |
+---------+------+--------------+------+----------+----------------------+
Notă adăugată:
+---------+------+------------+------+----------+----------------------+
| Student | Curs | Denumire   | Nota | Semestru | Actualizat           |
+---------+------+------------+------+----------+----------------------+
| S1      | C3   | Programare | 10   | 2026-1   | 2026-11-16T20:53:20Z |
+---------+------+------------+------+----------+----------------------+
Notă adăugată:
+---------+------+----------+------+----------+----------------------+
| Student | Curs | Denumire | Nota | Semestru | Actualizat           |
+---------+------+----------+------+----------+----------------------+
| S2      | C1   | Rețele   | 7    | 2026-1   | 2026-11-16T20:53:21Z |
+---------+------+----------+------+----------+----------------------+
Notă adăugată:
+---------+------+------------+------+----------+----------------------+
| Student | Curs | Denumire   | Nota | Semestru | Actualizat           |
+---------+------+------------+------+----------+----------------------+
| S2      | C3   | Programare | 9    | 2026-1   | 2026-11-16T20:53:22Z |
+---------+------+------------+------+----------+----------------------+
```

### 5.3 `get` — o singură notă (GetItem)

```bash
python -m app.cli get --student S1 --course C1
```

```
+---------+------+----------+------+----------+----------------------+
| Student | Curs | Denumire | Nota | Semestru | Actualizat           |
+---------+------+----------+------+----------+----------------------+
| S1      | C1   | Rețele   | 9    | 2026-1   | 2026-11-16T20:53:18Z |
+---------+------+----------+------+----------+----------------------+
```

### 5.4 `list` — toate notele unui student + media (Query)

`Query` citește doar partiția studentului cerut; rezultatele vin sortate după sort key (`course_id`):

```bash
python -m app.cli list --student S1
python -m app.cli list --student S2
```

```
Notele studentului 'S1' (3):
+---------+------+--------------+------+----------+----------------------+
| Student | Curs | Denumire     | Nota | Semestru | Actualizat           |
+---------+------+--------------+------+----------+----------------------+
| S1      | C1   | Rețele       | 9    | 2026-1   | 2026-11-16T20:53:18Z |
| S1      | C2   | Baze de date | 8    | 2026-1   | 2026-11-16T20:53:20Z |
| S1      | C3   | Programare   | 10   | 2026-1   | 2026-11-16T20:53:20Z |
+---------+------+--------------+------+----------+----------------------+
Media: 9.00
Notele studentului 'S2' (2):
+---------+------+------------+------+----------+----------------------+
| Student | Curs | Denumire   | Nota | Semestru | Actualizat           |
+---------+------+------------+------+----------+----------------------+
| S2      | C1   | Rețele     | 7    | 2026-1   | 2026-11-16T20:53:21Z |
| S2      | C3   | Programare | 9    | 2026-1   | 2026-11-16T20:53:22Z |
+---------+------+------------+------+----------+----------------------+
Media: 8.00
```

### 5.5 `update` — modificare notă (UpdateItem)

Setează `grade` și `updated_at`. Media lui S1 crește de la 9.00 la 9.67:

```bash
python -m app.cli update --student S1 --course C2 --grade 10
python -m app.cli list --student S1
```

```
Notă actualizată:
+---------+------+--------------+------+----------+----------------------+
| Student | Curs | Denumire     | Nota | Semestru | Actualizat           |
+---------+------+--------------+------+----------+----------------------+
| S1      | C2   | Baze de date | 10   | 2026-1   | 2026-11-16T20:53:25Z |
+---------+------+--------------+------+----------+----------------------+
Notele studentului 'S1' (3):
+---------+------+--------------+------+----------+----------------------+
| Student | Curs | Denumire     | Nota | Semestru | Actualizat           |
+---------+------+--------------+------+----------+----------------------+
| S1      | C1   | Rețele       | 9    | 2026-1   | 2026-11-16T20:53:18Z |
| S1      | C2   | Baze de date | 8    | 2026-1   | 2026-11-16T20:53:20Z |
| S1      | C3   | Programare   | 10   | 2026-1   | 2026-11-16T20:53:20Z |
+---------+------+--------------+------+----------+----------------------+
Media: 9.00
```

### 5.6 `delete` — ștergere notă (DeleteItem)

```bash
python -m app.cli delete --student S2 --course C3
python -m app.cli list --student S2
```

```
Nota studentului 'S2' la cursul 'C3' a fost ștearsă.
Notele studentului 'S2' (2):
+---------+------+------------+------+----------+----------------------+
| Student | Curs | Denumire   | Nota | Semestru | Actualizat           |
+---------+------+------------+------+----------+----------------------+
| S2      | C1   | Rețele     | 7    | 2026-1   | 2026-11-16T20:53:21Z |
| S2      | C3   | Programare | 9    | 2026-1   | 2026-11-16T20:53:22Z |
+---------+------+------------+------+----------+----------------------+
Media: 8.00
```

### 5.7 Tratarea erorilor

Notă duplicată (refuzată prin `ConditionExpression attribute_not_exists`):

```bash
python -m app.cli add --student S1 --course C1 --name "Rețele" --grade 5 --semester 2026-1
```

```
Eroare: Nota pentru studentul 'S1' la cursul 'C1' există deja. Folosește comanda 'update' pentru a o modifica.
```

Notă invalidă: în afara intervalului 1–10, respectiv un număr care nu e întreg (al doilea caz e prins direct de argparse):

```bash
python -m app.cli add --student S2 --course C2 --name "Baze de date" --grade 11 --semester 2026-1
python -m app.cli update --student S1 --course C1 --grade 9.5
```

```
Eroare: Notă invalidă: 11. Nota trebuie să fie un număr întreg între 1 și 10.
usage: python -m app.cli update [-h] --student STUDENT --course COURSE --grade
                                GRADE
python -m app.cli update: error: argument --grade: invalid int value: '9.5'
```

Notă inexistentă (`update`/`delete` refuzate prin `ConditionExpression attribute_exists`) și tabel deja creat:

```bash
python -m app.cli update --student S2 --course C2 --grade 8
python -m app.cli get --student S2 --course C2
python -m app.cli delete --student S2 --course C2
python -m app.cli init
```

```
Eroare: Nu există nicio notă pentru studentul 'S2' la cursul 'C2'.
Nu există nicio notă pentru studentul 'S2' la cursul 'C2'.
Eroare: Nu există nicio notă pentru studentul 'S2' la cursul 'C2'.
Tabelul 'Grades' a fost creat (PK: student_id, SK: course_id).
```

În caz de eroare, codul de ieșire al comenzii este `1` (respectiv `2` pentru argumente invalide, prinse de argparse).

### 5.8 `drop` — ștergere tabel (DeleteTable)

```bash
python -m app.cli drop
python -m app.cli list --student S1
```

```
Tabelul 'Grades' a fost șters.
Notele studentului 'S1' (3):
+---------+------+--------------+------+----------+----------------------+
| Student | Curs | Denumire     | Nota | Semestru | Actualizat           |
+---------+------+--------------+------+----------+----------------------+
| S1      | C1   | Rețele       | 9    | 2026-1   | 2026-11-16T20:53:18Z |
| S1      | C2   | Baze de date | 8    | 2026-1   | 2026-11-16T20:53:20Z |
| S1      | C3   | Programare   | 10   | 2026-1   | 2026-11-16T20:53:20Z |
+---------+------+--------------+------+----------+----------------------+
Media: 9.00
```

## 6. Aceleași operații cu AWS CLI

Scriptul `scripts/aws_cli_examples.sh` face aceleași operații (create-table → put-item → put-item duplicat refuzat → get-item → query → update-item → delete-item → delete-table) direct cu `aws --endpoint-url=http://localhost:4566 dynamodb ...`. Scriptul setează singur credențialele dummy `test`/`test` și regiunea `us-east-1`, deci **nu** e nevoie de `aws configure`.

Instalare AWS CLI (alege una):
- varianta oficială (v2): <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>
- sau, în mediul virtual: `pip install awscli` (v1 — **aceasta este varianta cu care a fost testat scriptul**: `aws-cli/1.46.3`)

> Scriptul creează și șterge el însuși tabelul `Grades`, deci rulează-l când tabelul **nu** există (de ex. după `python -m app.cli drop`). Pe Windows rulează-l din Git Bash. În script, denumirile cursurilor sunt scrise fără diacritice („Retele”), pentru a evita probleme de codificare a argumentelor în consolele Windows.

```bash
bash scripts/aws_cli_examples.sh
```

```
== 1. create-table (init) ==
Grades	ACTIVE
== 2. put-item (add, refuză duplicatele) ==
OK: S1 / C1 / nota 9
OK: S1 / C2 / nota 8
== 3. put-item duplicat (eroare așteptată) ==

An error occurred (ConditionalCheckFailedException) when calling the PutItem operation: The conditional request failed
-> duplicat refuzat, cum era de așteptat
== 4. get-item (get) ==
S1	C1	Retele	9	2026-1
== 5. query (list) ==
---------------------------------------
|                Query                |
+----+----------------+----+----------+
|  C1|  Retele        |  9 |  2026-1  |
|  C2|  Baze de date  |  8 |  2026-1  |
+----+----------------+----+----------+
== 6. update-item (update) ==
C1	10	2026-11-16T13:00:00Z
== 7. delete-item (delete) ==
OK
== 8. delete-table (drop) ==
Grades
```

Corespondența comenzilor:

| CLI aplicație | AWS CLI | API DynamoDB |
|---|---|---|
| `init` | `aws dynamodb create-table` | CreateTable |
| `add` | `aws dynamodb put-item --condition-expression "attribute_not_exists(student_id)"` | PutItem |
| `get` | `aws dynamodb get-item` | GetItem |
| `list` | `aws dynamodb query --key-condition-expression "student_id = :s"` | Query |
| `update` | `aws dynamodb update-item --condition-expression "attribute_exists(student_id)"` | UpdateItem |
| `delete` | `aws dynamodb delete-item` | DeleteItem |
| `drop` | `aws dynamodb delete-table` | DeleteTable |

## 7. Rulare teste

Testele sunt end-to-end: rulează contra LocalStack (care trebuie să fie pornit) și folosesc un tabel separat, `Grades_test`, creat și șters automat, deci nu afectează datele din `Grades`. Acoperă: add, duplicat refuzat, get, list + media, update, delete, notă invalidă (0, 11, -3, 9.5, "9") și tabel inexistent.

```bash
python -m pytest -v
```

Output (fragment; liniile cu căile locale `platform`/`cachedir`/`rootdir` au fost omise):

```
============================= test session starts =============================
collecting ... collected 11 items

tests/test_grades.py::test_add_and_get PASSED                            [  9%]
tests/test_grades.py::test_duplicate_refused PASSED                      [ 18%]
tests/test_grades.py::test_list_and_average PASSED                       [ 27%]
tests/test_grades.py::test_update PASSED                                 [ 36%]
tests/test_grades.py::test_delete PASSED                                 [ 45%]
tests/test_grades.py::test_invalid_grade[0] PASSED                       [ 54%]
tests/test_grades.py::test_invalid_grade[11] PASSED                      [ 63%]
tests/test_grades.py::test_invalid_grade[-3] PASSED                      [ 72%]
tests/test_grades.py::test_invalid_grade[9.5] PASSED                     [ 81%]
tests/test_grades.py::test_invalid_grade[9] PASSED                       [ 90%]
tests/test_grades.py::test_missing_table PASSED                          [100%]

============================= 11 passed in 3.56s ==============================
```

> Folosește `python -m pytest` (nu doar `pytest`), ca directorul proiectului să fie în `sys.path` și pachetul `app` să poată fi importat.

## 8. Oprire și curățare

```bash
docker compose down -v
```

```
 Container localstack-dynamodb  Stopping
 Container localstack-dynamodb  Stopped
 Container localstack-dynamodb  Removing
 Container localstack-dynamodb  Removed
 Network aws-dynamodb-localstack-demo_default  Removing
 Network aws-dynamodb-localstack-demo_default  Removed
```

Datele **nu** sunt persistente: la fiecare pornire LocalStack începe gol (tabelul trebuie recreat cu `init`). Cu LocalStack oprit, aplicația afișează:

```bash
python -m app.cli list --student S1
```

```
Eroare: Nu mă pot conecta la http://localhost:4566. LocalStack rulează? Pornește-l cu: docker compose up -d
```

Curățare completă (opțional):

```bash
deactivate                                   # ieșire din mediul virtual
docker image rm localstack/localstack:4.12   # șterge imaginea (~1,9 GB)
```

Apoi poți șterge directorul `.venv`.

## 9. Alternativă: imaginea nouă cu token

Imaginile LocalStack noi (`latest`, `2026.x`) cer un token. Fără el, containerul se oprește imediat (cod de ieșire 55). Mesaj real din `docker logs localstack-dynamodb`:

```
License activation failed! 🔑❌
Reason: No credentials were found in the environment. Please set the LOCALSTACK_AUTH_TOKEN variable to a valid auth token. ...
Due to this error, Localstack has quit. LocalStack pro features can only be used with a valid license.
```

Pași:

1. Creează un cont gratuit (planul **Hobby**, pentru uz necomercial) pe <https://app.localstack.cloud> și copiază token-ul din secțiunea **Auth Tokens**.
2. Copiază fișierul exemplu și completează token-ul:
   ```bash
   cp .env.example .env
   ```
   ```
   LOCALSTACK_IMAGE=localstack/localstack:latest
   LOCALSTACK_AUTH_TOKEN=tokenul-tau-real
   ```
3. Repornește:
   ```bash
   docker compose down -v
   docker compose up -d
   ```

Docker Compose citește automat `.env`, iar `docker-compose.yml` preia de acolo `LOCALSTACK_IMAGE` și `LOCALSTACK_AUTH_TOKEN`. Fără `.env`, se folosesc valorile implicite: imaginea `4.12` și token gol.

> ⚠️ `.env` este în `.gitignore` — **nu comite niciodată token-ul**. În repository există doar `.env.example`, fără secrete.

## 10. Depanare

**Docker nu rulează** — `docker compose up -d` afișează ceva de genul:
```
unable to get image 'localstack/localstack:4.12': error during connect: ... The system cannot find the file specified.
```
(pe Linux: `Cannot connect to the Docker daemon at unix:///var/run/docker.sock`). Pornește Docker Desktop (sau `sudo systemctl start docker` pe Linux), așteaptă să fie gata și reîncearcă.

**Portul 4566 e ocupat** — alt proces (sau alt container LocalStack) folosește deja portul:
```
Error response from daemon: ports are not available: exposing port TCP 0.0.0.0:4566 -> 127.0.0.1:0: listen tcp 0.0.0.0:4566: bind: Only one usage of each socket address (protocol/network address/port) is normally permitted.
```
Găsește procesul și oprește-l:
```bash
docker ps                          # alt container LocalStack? -> docker stop <nume>
netstat -ano | findstr :4566       # Windows (ultima coloană = PID)
lsof -i :4566                      # Linux / macOS
```

**Problema cu token-ul** — containerul pornește și se oprește imediat, iar `docker compose ps` nu îl mai arată. Verifică `docker logs localstack-dynamodb`. Dacă apare `License activation failed`, ai folosit o imagine nouă fără token: ori revii la varianta implicită (șterge `.env`, apoi `docker compose down -v && docker compose up -d`), ori urmezi [secțiunea 9](#9-alternativă-imaginea-nouă-cu-token).

**„Nu mă pot conecta la http://localhost:4566”** — LocalStack nu e pornit sau încă nu e `healthy`. Rulează `docker compose ps` și așteaptă `(healthy)`.

**„Tabelul 'Grades' nu există”** — LocalStack nu păstrează datele între reporniri. Rulează `python -m app.cli init`.

**`ModuleNotFoundError: No module named 'boto3'` sau `'app'`** — mediul virtual nu e activat, ori nu ești în rădăcina proiectului. Activează `.venv` (secțiunea 2) și rulează din directorul proiectului, cu `python -m ...`.

## 11. Limitări

- LocalStack este un **emulator**, nu AWS real: comportamentul e foarte apropiat, dar nu identic. Nu sunt emulate performanța, latența, limitele de throughput (RCU/WCU), facturarea, replicarea între regiuni sau IAM-ul real (orice credențiale sunt acceptate).
- Datele sunt ținute în memorie și se pierd la oprirea containerului (persistența este o funcție a versiunii plătite).
- Imaginea `4.12` este fixată și nu mai primește actualizări. Pentru versiuni noi e nevoie de token (secțiunea 9).
- `list` face un singur `Query`, fără paginare (DynamoDB întoarce maximum 1 MB per cerere), suficient pentru un demo.
- Proiectul este un prototip didactic: fără autentificare, fără validări avansate și fără indecși secundari (GSI/LSI).

## 12. Structura proiectului

```
aws-dynamodb-localstack-demo/
├── app/
│   ├── __init__.py
│   ├── db.py                  # client boto3 + funcții CRUD + traducerea erorilor
│   └── cli.py                 # interfața în linie de comandă (argparse)
├── scripts/
│   └── aws_cli_examples.sh    # aceleași operații cu AWS CLI
├── tests/
│   └── test_grades.py         # teste end-to-end pytest contra LocalStack
├── docker-compose.yml         # LocalStack 4.12, port 4566, healthcheck
├── requirements.txt           # boto3, pytest
├── .env.example               # model pentru varianta cu token (fără secrete)
├── .gitattributes             # LF pentru scripturile .sh
├── .gitignore                 # exclude .venv, .env, cache-uri
├── LICENSE                    # MIT
└── README.md
```

## Licență

[MIT](LICENSE)
