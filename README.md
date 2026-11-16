# DynamoDB pe LocalStack — proiect demo

Prototip care demonstrează **Amazon DynamoDB rulat local cu LocalStack**: o aplicație Python (boto3) pentru gestionarea unor task-uri, cu operații CRUD, plus aceleași operații executate cu AWS CLI.

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

Tabelul **`Tasks`**:

| Atribut      | Tip | Rol                                 |
|--------------|-----|-------------------------------------|
| `user_id`    | S   | **partition key** (HASH)            |
| `task_id`    | S   | **sort key** (RANGE), generat automat (8 caractere hex) |
| `title`      | S   | titlul task-ului                    |
| `status`     | S   | `todo` sau `done`                   |
| `created_at` | S   | data creării, ISO 8601 UTC          |

Operații DynamoDB folosite: `CreateTable`, `PutItem`, `GetItem`, `Query` (pe partition key, nu `Scan`), `UpdateItem` (cu `ConditionExpression`), `DeleteItem`, `DeleteTable`.

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
git clone https://github.com/sergio-humble/aws-dynamodb-localstack-demo.git
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

La prima pornire Docker descarcă imaginea `localstack/localstack:4.12` (~1 GB), deci poate dura câteva minute. Așteaptă până când coloana `STATUS` arată **`(healthy)`** (de obicei 5–15 secunde):

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
| `TABLE_NAME` | `Tasks` | numele tabelului |

Exemplu de suprascriere:

```bash
# Linux / macOS / Git Bash
export TABLE_NAME=TasksDemo

# Windows - PowerShell
$env:TABLE_NAME = "TasksDemo"
```

Fișierul `.env` (pornind de la `.env.example`) este folosit **doar** de Docker Compose, pentru alternativa cu token (secțiunea 9).

## 5. Utilizare pas cu pas (CLI-ul aplicației)

Toate comenzile se rulează din rădăcina proiectului, cu mediul virtual activat și LocalStack pornit. Output-urile de mai jos sunt **reale**, copiate dintr-o rulare de test. ID-urile task-urilor (`d100d32e` etc.) sunt generate aleator, deci la tine vor fi altele — folosește ID-urile afișate de comanda ta `add` / `list`.

### Ajutor

```bash
python -m app.cli --help
```

```
usage: python -m app.cli [-h] {init,add,get,complete,delete,list,drop} ...

Task-uri în DynamoDB pe LocalStack

positional arguments:
  {init,add,get,complete,delete,list,drop}
    init                creează tabelul Tasks
    add                 adaugă un task
    get                 afișează un task
    complete            marchează un task ca 'done' (UpdateItem)
    delete              șterge un task (DeleteItem)
    list                listează task-urile unui user (Query)
    drop                șterge tabelul Tasks

options:
  -h, --help            show this help message and exit
```

### 5.1 `init` — creare tabel (CreateTable)

```bash
python -m app.cli init
```

```
Tabelul 'Tasks' a fost creat (PK: user_id, SK: task_id).
```

### 5.2 `add` — adăugare task (PutItem)

```bash
python -m app.cli add ana "Citește documentația DynamoDB"
python -m app.cli add ana "Scrie referatul"
python -m app.cli add bogdan "Pregătește prezentarea"
```

```
Task adăugat pentru 'ana':
[ ] d100d32e  Citește documentația DynamoDB  (status: todo, creat: 2026-11-16T18:39:02Z)
Task adăugat pentru 'ana':
[ ] 29eeef77  Scrie referatul  (status: todo, creat: 2026-11-16T18:39:03Z)
Task adăugat pentru 'bogdan':
[ ] 7c68b619  Pregătește prezentarea  (status: todo, creat: 2026-11-16T18:39:04Z)
```

### 5.3 `list` — task-urile unui utilizator (Query)

`Query` citește doar partiția `user_id = ana`, deci task-ul lui `bogdan` nu apare:

```bash
python -m app.cli list ana
```

```
Task-urile lui 'ana' (2):
[ ] d100d32e  Citește documentația DynamoDB  (status: todo, creat: 2026-11-16T18:39:02Z)
[ ] 29eeef77  Scrie referatul  (status: todo, creat: 2026-11-16T18:39:03Z)
```

### 5.4 `get` — un singur task (GetItem)

```bash
python -m app.cli get ana d100d32e
```

```
[ ] d100d32e  Citește documentația DynamoDB  (status: todo, creat: 2026-11-16T18:39:02Z)
```

### 5.5 `complete` — marcare ca finalizat (UpdateItem)

```bash
python -m app.cli complete ana d100d32e
```

```
Task marcat ca finalizat:
[x] d100d32e  Citește documentația DynamoDB  (status: done, creat: 2026-11-16T18:39:02Z)
```

### 5.6 `delete` — ștergere task (DeleteItem)

```bash
python -m app.cli delete ana 29eeef77
python -m app.cli list ana
```

```
Task-ul '29eeef77' a fost șters.
Task-urile lui 'ana' (1):
[x] d100d32e  Citește documentația DynamoDB  (status: done, creat: 2026-11-16T18:39:02Z)
```

### 5.7 Tratarea erorilor

Task inexistent, tabel deja creat:

```bash
python -m app.cli get ana inexistent
python -m app.cli complete ana inexistent
python -m app.cli init
```

```
Task-ul 'inexistent' nu există pentru 'ana'.
Eroare: Task-ul nu există.
Eroare: Tabelul 'Tasks' există deja.
```

În caz de eroare, codul de ieșire al comenzii este `1`.

### 5.8 `drop` — ștergere tabel (DeleteTable)

```bash
python -m app.cli drop
python -m app.cli list ana
```

```
Tabelul 'Tasks' a fost șters.
Eroare: Tabelul 'Tasks' nu există. Creează-l cu: python -m app.cli init
```

## 6. Aceleași operații cu AWS CLI

Scriptul `scripts/aws_cli_examples.sh` face aceleași operații (create-table → put-item → get-item → query → update-item → delete-item → delete-table) direct cu `aws --endpoint-url=http://localhost:4566 dynamodb ...`. Scriptul setează singur credențialele dummy `test`/`test` și regiunea `us-east-1`, deci **nu** e nevoie de `aws configure`.

Instalare AWS CLI (alege una):
- varianta oficială (v2): <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>
- sau, în mediul virtual: `pip install awscli` (v1 — **aceasta este varianta cu care a fost testat scriptul**: `aws-cli/1.46.3`)

> Scriptul creează și șterge el însuși tabelul `Tasks`, deci rulează-l când tabelul **nu** există (de ex. după `python -m app.cli drop`). Pe Windows rulează-l din Git Bash.

```bash
bash scripts/aws_cli_examples.sh
```

```
== 1. create-table (init) ==
Tasks	ACTIVE
== 2. put-item (add) ==
OK
== 3. get-item (get) ==
{
    "Item": {
        "created_at": {
            "S": "2026-11-16T12:00:00Z"
        },
        "task_id": {
            "S": "cli00001"
        },
        "title": {
            "S": "Task creat din AWS CLI"
        },
        "user_id": {
            "S": "ana"
        },
        "status": {
            "S": "todo"
        }
    }
}
== 4. query (list) ==
------------------------------------------------
|                     Query                    |
+-----------+--------------------------+-------+
|  cli00001 |  Task creat din AWS CLI  |  todo |
+-----------+--------------------------+-------+
== 5. update-item (complete) ==
cli00001	done
== 6. delete-item (delete) ==
OK
== 7. delete-table (drop) ==
Tasks
```

Corespondența comenzilor:

| CLI aplicație | AWS CLI | API DynamoDB |
|---|---|---|
| `init` | `aws dynamodb create-table` | CreateTable |
| `add` | `aws dynamodb put-item` | PutItem |
| `get` | `aws dynamodb get-item` | GetItem |
| `list` | `aws dynamodb query` | Query |
| `complete` | `aws dynamodb update-item` | UpdateItem |
| `delete` | `aws dynamodb delete-item` | DeleteItem |
| `drop` | `aws dynamodb delete-table` | DeleteTable |

## 7. Rulare teste

Testele sunt end-to-end: rulează contra LocalStack (care trebuie să fie pornit) și folosesc un tabel separat, `Tasks_test`, creat și șters automat, deci nu afectează datele din `Tasks`.

```bash
python -m pytest -v
```

Output (fragment; liniile cu căile locale `cachedir`/`rootdir` au fost omise):

```
============================= test session starts =============================
platform win32 -- Python 3.11.15, pytest-9.2.0, pluggy-1.7.0
collecting ... collected 3 items

tests/test_tasks.py::test_crud_flow PASSED                               [ 33%]
tests/test_tasks.py::test_missing_task_errors PASSED                     [ 66%]
tests/test_tasks.py::test_missing_table_error PASSED                     [100%]

============================== 3 passed in 2.01s ==============================
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
python -m app.cli list ana
```

```
Eroare: Nu mă pot conecta la http://localhost:4566. LocalStack rulează? Pornește-l cu: docker compose up -d
```

Curățare completă (opțional):

```bash
deactivate                                   # ieșire din mediul virtual
docker image rm localstack/localstack:4.12   # șterge imaginea (~1 GB)
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

**„Tabelul 'Tasks' nu există”** — LocalStack nu păstrează datele între reporniri. Rulează `python -m app.cli init`.

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
│   └── test_tasks.py          # teste end-to-end pytest contra LocalStack
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
