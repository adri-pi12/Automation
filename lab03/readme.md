# Lab 03 — Automatizarea scriptului Python cu cron și Docker

Autor: Pisari Adriana, grupa I2401.

## Scop

Scriptul din laboratorul 2 cere un curs valutar de la API și salvează răspunsul JSON.
În laboratorul 3, cron pornește acest script automat într-un container Docker.

| Programare | Câmpuri cron | Parametri transmiși scriptului |
| --- | --- | --- |
| Zilnic, ora 06:00 | `0 6 * * *` | `MDL EUR` și data de ieri |
| Vineri, ora 17:00 | `0 17 * * 5` | `MDL USD` și data de acum 7 zile |

Orele sunt în fusul `Europe/Chisinau`, inclusiv schimbarea sezonieră a orei.
În această implementare, „previous week” înseamnă aceeași zi din săptămâna trecută,
adică o dată cu 7 zile înaintea execuției. Scriptul lab02 acceptă o singură dată;
nu calculează o medie săptămânală și nu cere toate zilele săptămânii.

## 1. Pregătirea proiectului pe Mac



```bash
cd ~/Desktop/automation
git status
git switch -c lab03
cp -R lab02 lab03
```

`git switch -c lab03` creează branch-ul și comută pe el. `cp -R` copiază fișierele
laboratorului 2 în noul director.

 Arhiva conține deja copia scriptului din lab02 și toate
adaptările descrise la punctul 7. Vechiul `README.md` al lab02 este înlocuit cu
acest `readme.md`; pe macOS acestea reprezintă de obicei același nume de fișier.

Verificăm rezultatul:

```bash
cd ~/Desktop/automation/lab03
ls -la
docker --version
docker compose version
```

Nu este necesară activarea mediului `venv` de pe Mac: imaginea Docker are Python
și dependențele sale proprii. Nu copiem mediul virtual al Mac-ului în imagine.

## 2. Pornirea API-ului din laboratorul 2

Containerul cron este un client al API-ului; API-ul trebuie pornit separat.
Într-un alt Terminal, în directorul serviciului suport folosit la lab02:

```bash
cd ~/Desktop/lab02prep
docker compose up -d
docker compose ps
```

Folosește locația actuală a serviciului dacă între timp l-ai mutat. API-ul trebuie
să fie disponibil pe Mac la `http://localhost:8080`, ca în laboratorul 2.

În directorul `automation/lab03`, creează configurația locală:

```bash
cp sample.env .env
nano .env
```

În `nano`: salvezi cu **Control+O**, confirmi cu **Enter** și ieși cu **Control+X**.
Păstrează cheia de test `EXAMPLE_API_KEY` dacă API-ul lab02 o folosește; dacă ai
schimbat cheia, introdu valoarea actuală în `API_KEY`. Nu publica fișierul `.env`.

```dotenv
API_URL=http://host.docker.internal:8080
API_KEY=EXAMPLE_API_KEY
TZ=Europe/Chisinau
```

În Docker Desktop, `host.docker.internal` ajunge la Mac. În interiorul
containerului, `localhost` ar indica acel container, nu API-ul pornit pe Mac.
Compose transmite variabilele din `.env` prin `env_file`. Entrypoint-ul salvează
doar variabilele necesare într-un fișier intern citit de fiecare sarcină cron.

## 3. Construirea și pornirea containerului cron

Execută în `~/Desktop/automation/lab03`:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=30 currency-cron
```

`--build` construiește imaginea folosind Dockerfile; `-d` lasă containerul să ruleze
în fundal. Dockerfile instalează cron, baza de fusuri orare și biblioteca requests.
Entrypoint-ul configurează ora, logurile și crontab-ul, pornește daemonul cron în
fundal cu `/usr/sbin/cron` și lasă `tail` să urmărească logul în prim-plan.
Astfel, containerul rămâne activ și mesajele apar în `docker compose logs`.

Starea `healthy`, după aproximativ 30 de secunde, confirmă că procesul cron există;
nu dovedește că API-ul răspunde sau că o sarcină a fost deja executată.

## 4. Verificarea programării și a logurilor

```bash
docker compose exec currency-cron date
docker compose exec currency-cron crontab -l
docker compose exec currency-cron cat /var/log/cron.log
docker compose logs -f currency-cron
```

Prima comandă verifică ora containerului. A doua trebuie să arate cele două
programări din `cronjob`. La pornire logul poate fi gol: sarcinile normale se
execută la 06:00 și vineri la 17:00, fără o execuție automată imediată.
Cu **Control+C** oprești doar urmărirea logurilor; containerul continuă să ruleze.

În `cronjob`, cele cinci câmpuri sunt: minut, oră, ziua lunii, luna, ziua săptămânii.
`*` înseamnă orice valoare. În ultimul câmp, `5` înseamnă vineri.

Comenzile folosesc `date -d 'yesterday' +\%F` și `date -d '7 days ago' +\%F`.
Data se calculează la fiecare execuție, în Linux-ul containerului. Nu executăm
aceste comenzi GNU `date` direct în Terminalul macOS. În cron, `%` trebuie scris
`\%`; altfel cron îl interpretează special, chiar dacă apare între ghilimele.

`>> /var/log/cron.log 2>&1` adaugă atât ieșirea standard, cât și erorile în fișier.
`python -u` trimite mesajele imediat, fără tamponarea ieșirii.
Gruparea cu `{ ...; }` redirecționează și eventualele erori de configurare.

Fișierul este instalat cu `crontab`, ca tabel al utilizatorului root. De aceea,
liniile sale NU conțin un câmp suplimentar `root`. Nu instalăm aceleași sarcini
și în `/etc/cron.d`, deoarece ar rula de două ori.

## 5. Testarea fără să aștepți ora programată

### Limita API-ului vechi

API-ul utilizat la laboratorul 2 avea date doar pentru intervalul
**2025-01-01 – 2025-09-15**. Programările normale cer ieri și data de acum 7 zile.
Dacă aceste date nu există în API, vei vedea o eroare în log și nu se va crea JSON.
Cron poate funcționa corect chiar dacă API-ul nu are cursul solicitat.
Pentru cursuri actuale reușite este necesar un API/set de date actualizat care
păstrează același contract HTTP; înlocuiești adresa prin `API_URL`, după caz.
Scriptul nu inventează și nu înlocuiește automat datele cerute de programare.

### 5.1. Test manual cu o dată istorică

```bash
docker compose exec currency-cron python -u currency_exchange_rate.py MDL EUR 2025-09-10
```

Dacă API-ul este accesibil și are cursul, trebuie să apară mesajul de succes și
fișierul `data/MDL_EUR_2025-09-10.json` pe Mac. Această comandă verifică scriptul
și API-ul; nu constituie o execuție declanșată de cron și nu redirecționează în log.

### 5.2. Test real prin cron, în fiecare minut

Instalează temporar programarea de test:

```bash
docker compose exec currency-cron crontab /app/lab03/cronjob.test
docker compose exec currency-cron crontab -l
```

Așteaptă una-două minute, apoi verifică:

```bash
docker compose exec currency-cron tail -n 40 /var/log/cron.log
docker compose exec currency-cron ls -l /app/data
ls -l data
```

`cronjob.test` pornește ambele conversii în fiecare minut, cu date istorice:
MDL/EUR pentru `2025-09-10` și MDL/USD pentru `2025-09-08`.
În log trebuie să apară marcajele `[TEST EUR]` și `[TEST USD]`, urmate de rezultatul
real al scriptului. Mesajul de succes și cele două fișiere JSON confirmă și
funcționarea API-ului; un mesaj de eroare trebuie analizat, nu raportat drept succes.

**După verificare, restabilește obligatoriu programarea cerută:**

```bash
docker compose exec currency-cron crontab /app/lab03/cronjob
docker compose exec currency-cron crontab -l
```

Ultima ieșire trebuie să conțină `0 6 * * *` și `0 17 * * 5`.
Fișierul normal `cronjob` nu este modificat de test. La recrearea/pornirea
containerului, entrypoint-ul reinstalează tot programarea normală.

## 6. Structura proiectului și rolul fișierelor

Toate fișierele de mai jos sunt în `automation/lab03`.

| Fișier/director | Rol |
| --- | --- |
| `currency_exchange_rate.py` | Primește `FROM TO DATE`, cere cursul prin HTTP POST, salvează JSON și jurnalizează erorile. |
| `requirements.txt` | Declară biblioteca externă requests; celelalte module folosite sunt din biblioteca standard Python. |
| `cronjob` | Conține cele două programări cerute, cu date calculate dinamic. |
| `entrypoint.sh` | Configurează fusul orar, variabilele cron și logurile; instalează sarcinile și pornește cron. |
| `Dockerfile` | Construiește mediul Linux pe baza imaginii oficiale Python 3.12, cu cron și tzdata. |
| `docker-compose.yml` | Construiește și pornește serviciul `currency-cron`, transmite configurația și montează directoarele persistente. |
| `sample.env` | Model de configurație fără secrete reale. |
| `.env` | Configurația locală, creată de utilizator și ignorată de Git/Docker build. |
| `cronjob.test` | Programare temporară pentru verificare în fiecare minut cu date istorice. |
| `.dockerignore` | Exclude configurația locală, mediul virtual, rezultatele și logurile din contextul de build. |
| `.gitignore` | Exclude `.env`, mediile virtuale și fișierele generate din commit-uri. |
| `readme.md` | Instrucțiunile de construire, rulare, verificare și explicațiile proiectului. |
| `data/` | Apare la rulare; păstrează pe Mac fișierele JSON create în `/app/data`. |
| `logs/cron.log` | Apare la rulare; păstrează ieșirea sarcinilor, accesibilă și ca `/var/log/cron.log`. |
| `logs/error.log` | Apare la rulare; păstrează erorile Python, accesibile și ca `/app/error.log`. |

În container, scriptul se află în `/app/lab03`; părintele său `/app` înlocuiește
rădăcina repository-ului din lab02. Astfel sunt păstrate regulile originale pentru
`data` și `error.log`. Legăturile simbolice și volumele fac rezultatele vizibile
în directoarele `lab03/data` și `lab03/logs` de pe Mac.
Aceste directoare persistă după `docker compose down`.

## 7. Modificări față de lab02

Am păstrat scriptul din repository-ul Automation și interfața `FROM TO DATE`.
Adaptările din copia lab03 sunt:

1. `API_URL` este citit din mediu, pentru conectarea containerului la API-ul de pe Mac.
2. Validarea verifică formatul și existența datei; intervalul fix din 2025 a fost
   eliminat din client. API-ul decide dacă are datele cerute. Eliminarea limitei
   din client nu adaugă date noi în API.
3. Scriptul întoarce codul `0` la succes și `1` la eroare, util la automatizare.
4. `requirements.txt` declară requests și lasă pip să aleagă dependențe compatibile
   cu Linux/Python 3.12, în locul listei exportate din mediul Mac.

Directorul original `lab02` nu trebuie modificat.

## 8. Oprire, reluare și salvare în Git

```bash
docker compose down
docker compose up -d
```

Pentru modificări ale Dockerfile/scriptului/cronjob-ului, reconstruiește imaginea:

```bash
docker compose up -d --build
```

Modificarea doar a `.env` necesită recrearea containerului:

```bash
docker compose up -d --force-recreate
```

Mac-ul și Docker Desktop trebuie să fie pornite la ora programată. Cron nu
recuperează automat toate execuțiile ratate când containerul este oprit sau Mac-ul
doarme. Politica `restart` ajută la reluare după repornirea Docker.

Din rădăcina proiectului:

```bash
cd ~/Desktop/automation
git status
git add lab03
git diff --cached --stat
git commit -m "Add lab03 cron automation with Docker"
git push -u origin lab03
```

Verifică înaintea commit-ului că `.env`, logurile și rezultatele generate nu sunt
incluse. Branch-ul rămâne `lab03`; această cerință nu impune un merge în `main`.

## 9. Dovezi de capturat la execuția pe Mac

| Cerință | Verificare / captură |
| --- | --- |
| Branch și director lab03 | `git branch --show-current` și `ls lab03` din rădăcina proiectului. |
| Imagine și container pornit | Finalul construirii și `docker compose ps`. |
| Ora și cele două sarcini | `date` și `crontab -l` în container. |
| Execuție reală prin cron | Marcajele TEST, ieșirea scriptului și JSON-urile, după instalarea temporară a `cronjob.test`. |
| Scriere în fișierul cerut | `tail -n 40 /var/log/cron.log` în container. |
| Programarea finală corectă | `crontab -l` după restabilirea fișierului `cronjob`. |

Acestea sunt instrucțiuni și rezultate de verificat pe Mac; nu sunt dovezi că
serviciul Docker sau API-ul tău au fost deja pornite în această sesiune.

## 10. Documentație

- [Debian: formatul crontab și regulile pentru `%`](https://manpages.debian.org/bookworm/cron/crontab.5.en.html)
- [Debian: daemonul cron](https://manpages.debian.org/bookworm/cron/cron.8.en.html)
- [Docker Desktop: accesul la serviciile gazdei](https://docs.docker.com/desktop/features/networking/networking-how-tos/)
- [Docker Compose: variabile de mediu și env_file](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/)
