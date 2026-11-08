# Laboratorul 03 — Automatizarea scriptului Python cu cron și Docker

**Autor:** Pisari Adriana, grupa I2401

## Scopul lucrării

În această lucrare am continuat proiectul `automation` din laboratorul 2. Am copiat fișierele din `lab02` în directorul `lab03` și am lucrat pe branch-ul `lab03`. Am configurat cron pentru a executa automat scriptul `currency_exchange_rate.py` într-un container Docker.

Am stabilit următoarele programări, în fusul orar `Europe/Chisinau`:

| Sarcină | Programare cron | Data solicitată |
| --- | --- | --- |
| Obținerea cursului MDL → EUR, zilnic la ora 06:00 | `0 6 * * *` | Ziua precedentă |
| Obținerea cursului MDL → USD, vineri la ora 17:00 | `0 17 * * 5` | Data de acum 7 zile |

Pentru cerința „previous week”, am folosit aceeași zi din săptămâna precedentă, adică data de acum 7 zile, deoarece scriptul primește o singură dată la fiecare execuție.

## 1. Construirea și pornirea containerului cu cron

### Pregătirea serviciului API

Am folosit Docker Desktop pe macOS și serviciul API din laboratorul 2. Pentru pornirea API-ului am executat următoarele comenzi în Terminal:

```bash
cd ~/Desktop/lab02prep
docker compose up -d
```

Am verificat dacă API-ul răspunde pe portul `8080`:

```bash
curl --max-time 10 -X POST "http://localhost:8080/?currencies" -d "key=EXAMPLE_API_KEY"
```

Am primit un răspuns JSON cu lista valutelor și câmpul `error` gol. La prima încercare de conectare, API-ul era oprit. Am pornit containerul `php_apache`, după care cererea a reușit.

### Configurarea variabilelor de mediu

Am revenit în directorul laboratorului 3 și am creat configurația locală pe baza fișierului `sample.env`:

```bash
cd ~/Desktop/automation/lab03
cp -n sample.env .env
```

Am folosit următoarele valori pentru API-ul de laborator:

```dotenv
API_URL=http://host.docker.internal:8080
API_KEY=EXAMPLE_API_KEY
TZ=Europe/Chisinau
```

Am utilizat `host.docker.internal` pentru ca scriptul din container să ajungă la API-ul disponibil pe Mac. Am transmis variabilele prin opțiunea `env_file` din `docker-compose.yml`.

În `entrypoint.sh`, am configurat fusul orar al containerului și am salvat variabilele necesare într-un fișier intern, `/run/cron-env.sh`. Am inclus citirea acestui fișier în comenzile cron, pentru ca scriptul să primească adresa API-ului și cheia de acces și la execuțiile automate.

### Construirea imaginii și pornirea serviciului

Am folosit imaginea oficială `python:3.12-slim-bookworm`, care include Python. În Dockerfile am prevăzut instalarea pachetelor `cron` și `tzdata`, precum și instalarea bibliotecii `requests` din `requirements.txt`.

Din directorul `lab03`, am construit imaginea și am pornit containerul:

```bash
docker compose up -d --build
```

Prin `--build`, am cerut construirea imaginii folosind Dockerfile. Prin `-d`, am pornit containerul în fundal.

Am verificat starea serviciului și mesajele de pornire:

```bash
docker compose ps
docker compose logs --tail=30 currency-cron
```

Am observat că serviciul `currency-cron` avea starea `healthy`. În log au apărut mesajele „Cron configurat” și „Cron pornit în fundal”. Această verificare mi-a confirmat pornirea daemonului cron; pentru verificarea execuției scriptului am realizat testele de la punctul 2.

În entrypoint am instalat sarcinile prin `crontab /app/lab03/cronjob` și am pornit daemonul cu `/usr/sbin/cron`. Am folosit `tail -n +1 -F /var/log/cron.log` în prim-plan pentru a menține containerul activ și pentru a afișa logul prin Docker Compose.

## 2. Verificarea sarcinilor cron și a fișierului de log

### Verificarea programării instalate

Am afișat sarcinile instalate:

```bash
docker compose exec currency-cron crontab -l
```

Am verificat prezența programărilor `0 6 * * *` și `0 17 * * 5`. În aceste expresii, am folosit ordinea: minut, oră, ziua lunii, lună și ziua săptămânii. Valoarea `5` din ultimul câmp indică ziua de vineri.

Pentru verificarea separată a orei containerului pot folosi:

```bash
docker compose exec currency-cron date
```

Am calculat data fiecărei cereri la momentul execuției, folosind `date -d 'yesterday' +\%F`, respectiv `date -d '7 days ago' +\%F`, în containerul Linux. Am scris semnul procent ca `\%` în fișierul cron pentru a obține formatul datei fără interpretarea specială a caracterului de către cron.

### Verificarea manuală a scriptului și a conexiunii

Am testat scriptul din container cu o dată disponibilă în API:

```bash
docker compose exec currency-cron python -u currency_exchange_rate.py MDL EUR 2025-09-10
```

Am primit mesajul „Cererea a fost realizată cu succes”, iar rezultatul a fost salvat în `/app/data/MDL_EUR_2025-09-10.json`. Am verificat și fișierul de pe Mac:

```bash
ls -l data
```

Prin acest test am verificat scriptul, conexiunea la API și salvarea rezultatului. Pentru declanșarea automată am folosit programarea temporară de mai jos.

### Testarea automată în fiecare minut

Pentru a verifica execuția fără să aștept ora 06:00 sau ziua de vineri, am instalat temporar sarcinile din `cronjob.test`:

```bash
docker compose exec currency-cron crontab /app/lab03/cronjob.test
```

Am folosit două conversii cu date istorice disponibile în API:

| Conversie de test | Data solicitată | Frecvență |
| --- | --- | --- |
| MDL → EUR | `2025-09-10` | În fiecare minut |
| MDL → USD | `2025-09-08` | În fiecare minut |

După una-două minute, am verificat ieșirea sarcinilor în fișierul cerut:

```bash
docker compose exec currency-cron tail -n 40 /var/log/cron.log
```

Am observat marcajele `[TEST EUR]` și `[TEST USD]` în minute succesive, urmate de mesajele de succes ale scriptului și de căile fișierelor JSON. Astfel, am confirmat că scriptul este pornit automat de cron și că rezultatele execuțiilor sunt scrise în `/var/log/cron.log`.

Am verificat și cele două fișiere salvate pe Mac:

```bash
ls -l data
```

Am obținut fișierele `MDL_EUR_2025-09-10.json` și `MDL_USD_2025-09-08.json`, vizibile și în directorul local `lab03/data`.

### Restabilirea programării finale

După testare, am reinstalat fișierul `cronjob` și am verificat din nou conținutul:

```bash
docker compose exec currency-cron crontab /app/lab03/cronjob
docker compose exec currency-cron crontab -l
```

Am confirmat revenirea la execuția zilnică la 06:00 și la execuția săptămânală de vineri, la 17:00.

### Urmărirea logurilor

Pentru verificări ulterioare, am la dispoziție următoarele comenzi:

```bash
docker compose exec currency-cron cat /var/log/cron.log
docker compose logs -f currency-cron
```

În sarcinile cron, am folosit redirecționarea `>> /var/log/cron.log 2>&1`. Prin `>>` adaug ieșirea la sfârșitul fișierului, iar prin `2>&1` trimit și mesajele de eroare în același loc. Am folosit opțiunea Python `-u` pentru afișarea imediată a mesajelor.

Am legat `/var/log/cron.log` de `/app/logs/cron.log` și am montat directorul local `logs` în container. Astfel, pot consulta logul și pe Mac, în `lab03/logs/cron.log`. Cu `Control+C` pot opri urmărirea prin `docker compose logs -f`, în timp ce containerul continuă să ruleze.

### Limita datelor disponibile în API

Pentru testele reușite am folosit date istorice, deoarece API-ul laboratorului 2 conține cursuri pentru intervalul `2025-01-01`–`2025-09-15`. Am păstrat în programarea finală datele relative cerute: ieri și data de acum 7 zile. Pentru a obține cursuri și pentru date mai recente, am nevoie de un API sau de un set de date care le include. În cazul unei date indisponibile, pot verifica eroarea în log.

## 3. Structura proiectului și rolul fișierelor

Am organizat fișierele laboratorului în directorul `automation/lab03`:

| Fișier sau director | Rol în proiect |
| --- | --- |
| `currency_exchange_rate.py` | Am folosit scriptul pentru a primi valutele și data ca argumente, a trimite cererea HTTP POST către API, a salva răspunsul JSON și a înregistra erorile. |
| `requirements.txt` | Am declarat biblioteca `requests`, necesară pentru comunicarea HTTP cu API-ul. |
| `cronjob` | Am definit cele două sarcini finale: zilnic la 06:00 pentru MDL/EUR și vineri la 17:00 pentru MDL/USD. |
| `cronjob.test` | Am definit sarcinile temporare care rulează în fiecare minut, cu date istorice, pentru verificarea execuției automate. |
| `Dockerfile` | Am descris construirea imaginii, instalarea dependențelor, copierea fișierelor și folosirea entrypoint-ului. |
| `entrypoint.sh` | Am configurat fusul orar, variabilele necesare cron, logurile și instalarea sarcinilor, apoi am pornit cron și urmărirea logului. |
| `docker-compose.yml` | Am definit serviciul `currency-cron`, construirea imaginii, variabilele de mediu, volumele și politica de repornire. |
| `sample.env` | Am păstrat un model cu adresa API-ului, cheia de test și fusul orar. |
| `.env` | Am păstrat configurația locală transmisă containerului prin Compose. |
| `.dockerignore` | Am exclus configurația locală, mediul virtual, logurile și rezultatele generate din contextul de construire a imaginii. |
| `.gitignore` | Am exclus `.env`, mediile virtuale, logurile și rezultatele generate din fișierele adăugate în Git. |
| `readme.md` | Am descris pornirea containerului, verificarea sarcinilor cron și rolul fișierelor proiectului. |
| `data/` | Am păstrat pe Mac fișierele JSON create de script în `/app/data`. |
| `logs/cron.log` | Am păstrat ieșirea sarcinilor cron, disponibilă în container la `/var/log/cron.log`. |
| `logs/error.log` | Am păstrat erorile înregistrate de scriptul Python, disponibile în container și la `/app/error.log`. |

În container, am plasat scriptul în `/app/lab03`. Am păstrat salvarea rezultatelor în directorul părinte al scriptului, astfel încât fișierele JSON sunt create în `/app/data`. Prin volumele definite în Compose, am făcut rezultatele și logurile accesibile și în directoarele locale `lab03/data` și `lab03/logs`.

## Oprirea și reluarea serviciului

Pentru oprirea serviciului cron pot folosi, din directorul `lab03`:

```bash
docker compose down
```

Pentru reluarea execuției folosesc:

```bash
docker compose up -d
```

După modificarea fișierelor copiate în imagine, reconstruiesc și repornesc serviciul:

```bash
docker compose up -d --build
```

Pentru rularea la orele programate, păstrez Mac-ul și Docker Desktop pornite, containerul activ și API-ul accesibil. Dacă opresc containerul, la repornire cron continuă cu programările următoare.
