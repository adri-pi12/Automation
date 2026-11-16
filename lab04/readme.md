# Laboratorul 04 — Automatizarea sarcinilor DevOps cu Jenkins

**Autor:** Pisari Adriana, grupa I2401

## 1. Descrierea proiectului

În această lucrare am configurat Jenkins pentru automatizarea instalării dependențelor și rulării testelor unui proiect PHP. Am folosit Docker Compose pentru a porni două servicii: Jenkins Controller și un agent SSH. Am organizat fișierele lucrării în directorul `lab04` din proiectul `automation`.

Pentru testare am ales proiectul public [composer/semver](https://github.com/composer/semver), o bibliotecă PHP pentru compararea versiunilor și verificarea constrângerilor de versiune. Am folosit codul și testele existente ale acestui proiect. Definiția pipeline-ului pentru laborator se află în [Jenkinsfile](Jenkinsfile).

| Componentă | Rol în lucrare |
| --- | --- |
| Jenkins Controller | Am folosit interfața web pentru administrarea credențialelor, a nodului și a pipeline-ului. |
| SSH Agent | Am folosit containerul pentru executarea comenzilor PHP și a testelor. |
| Jenkinsfile | Am definit etapele `Install Dependencies` și `Test`, precum și mesajele afișate după execuție. |
| Composer | Am instalat dependențele proiectului PHP și am lansat comanda de testare definită de acesta. |

Am lucrat pe macOS, cu Docker Desktop și Docker Compose. În verificările efectuate, Jenkins avea versiunea `2.580.2`, iar agentul avea PHP CLI `8.4.27`.

## 2. Configurarea Jenkins Controller

### 2.1. Configurarea serviciului Docker

În [docker-compose.yml](docker-compose.yml), am definit serviciul `jenkins-controller` folosind imaginea `jenkins/jenkins:lts`. Am configurat porturile `8080:8080` și `50000:50000`, volumul `jenkins_home` pentru directorul `/var/jenkins_home` și rețeaua comună `jenkins-network`.

Portul `8080` era folosit de containerul `php_apache` din laboratorul anterior. Am eliberat portul oprind temporar acel container:

```bash
docker stop php_apache
```

În prima etapă, când fișierul Compose conținea doar serviciul controllerului, am pornit Jenkins din directorul `lab04`:

```bash
docker compose up -d jenkins-controller
```

După adăugarea agentului, configurația finală are nevoie și de cheia publică din fișierul `automation/.env`. Pentru pornirea configurației finale folosesc comenzile de la punctul 3.2, după pregătirea cheilor de la punctul 3.1.

### 2.2. Configurarea inițială în browser

Am deschis [http://localhost:8080](http://localhost:8080). În pagina `Unlock Jenkins`, am introdus parola inițială, pe care am copiat-o din container în clipboard cu:

```bash
docker exec jenkins-controller cat /var/jenkins_home/secrets/initialAdminPassword | pbcopy
```

Am ales `Install suggested plugins`, am creat contul administrator și am păstrat adresa Jenkins `http://localhost:8080/`. După finalizarea configurării, am ajuns la pagina principală Jenkins.

Am verificat pluginurile necesare:

| Plugin | Utilizare |
| --- | --- |
| Pipeline | Am folosit funcționalitățile necesare joburilor de tip Pipeline. |
| Pipeline: Declarative | Am folosit sintaxa declarativă `pipeline { ... }`. |
| Pipeline: Basic Steps | Am folosit pașii de bază ai pipeline-ului, inclusiv curățarea directorului de lucru. |
| Git | Am descărcat proiectul PHP din GitHub. |
| SSH Build Agents | Am conectat controllerul la agent prin SSH. |

La instalare am întâlnit o dependență lipsă, `workflow-basic-steps`. Am instalat `Pipeline: Basic Steps` din lista pluginurilor disponibile și am repornit controllerul. După această corectare, mesajele de încărcare eșuată pentru Pipeline au dispărut.

## 3. Configurarea agentului SSH

### 3.1. Crearea cheilor și a configurației locale

În rădăcina proiectului `automation`, am creat directorul `secrets` și am generat o pereche de chei RSA de 4096 de biți, în format PEM:

```bash
cd ~/Desktop/automation
mkdir -p secrets
ssh-keygen -t rsa -b 4096 -m PEM -f secrets/jenkins_agent_ssh_key
```

Am obținut următoarele fișiere:

| Fișier | Rol |
| --- | --- |
| `secrets/jenkins_agent_ssh_key` | Am înregistrat cheia privată în Jenkins Credentials pentru autentificarea controllerului la agent. |
| `secrets/jenkins_agent_ssh_key.pub` | Am transmis cheia publică agentului prin variabila de mediu `JENKINS_AGENT_SSH_PUBKEY`. |

Am adăugat în `.gitignore` din rădăcina proiectului:

```gitignore
/secrets/
/.env
```

Am creat variabila cu cheia publică în fișierul `automation/.env`:

```bash
printf 'JENKINS_AGENT_SSH_PUBKEY=%s\n' "$(cat secrets/jenkins_agent_ssh_key.pub)" >> .env
```

Am verificat că fișierele locale sunt ignorate de Git:

```bash
git check-ignore secrets/jenkins_agent_ssh_key .env
```

### 3.2. Construirea și pornirea containerului agentului

În [Dockerfile](Dockerfile), am folosit imaginea `jenkins/ssh-agent` și am prevăzut instalarea PHP CLI, a extensiilor `php-mbstring` și `php-xml`, precum și a programelor Composer, Git și unzip.

În Compose am adăugat serviciul `ssh-agent`, volumul `jenkins_agent_volume` montat în `/home/jenkins/agent`, variabila cu cheia publică și aceeași rețea ca pentru controller.

Din directorul `lab04`, am validat configurația și am construit și pornit serviciile:

```bash
cd ~/Desktop/automation/lab04
docker compose --env-file ../.env config --quiet
docker compose --env-file ../.env up -d --build
```

Am folosit `--env-file ../.env` deoarece fișierul cu cheia publică se află în rădăcina `automation`, cu un nivel mai sus decât `lab04`.

Am verificat starea containerelor și versiunea PHP:

```bash
docker compose --env-file ../.env ps
docker compose --env-file ../.env exec ssh-agent php -v
```

Am observat ambele servicii în execuție și versiunea PHP `8.4.27` pe agent.

### 3.3. Înregistrarea cheii private în Jenkins

Am deschis `Manage Jenkins → Credentials → System → Global credentials → Add Credentials` și am ales tipul `SSH Username with private key`.

Am configurat credențiala astfel:

| Câmp | Valoare |
| --- | --- |
| ID | `jenkins-agent-ssh` |
| Username | `jenkins` |
| Description | `Cheie SSH pentru agentul PHP` |
| Scope | `Global` |
| Private Key | `Enter directly`, cu cheia privată din directorul `secrets` |

Pentru copierea cheii pe Mac am folosit:

```bash
pbcopy < ~/Desktop/automation/secrets/jenkins_agent_ssh_key
```

### 3.4. Crearea nodului Jenkins

Am creat un nod de tip `Permanent Agent`, cu numele `ssh-agent1`, și am completat următoarele setări:

| Setare | Valoare |
| --- | --- |
| Number of executors | `1` |
| Remote root directory | `/home/jenkins/agent` |
| Labels | `php-agent` |
| Launch method | `Launch agents via SSH` |
| Host | `ssh-agent` |
| Port | `22` |
| Credentials | `jenkins-agent-ssh` |
| Host Key Verification Strategy | `Manually provided key Verification Strategy` |

Pentru verificarea identității serverului SSH, am copiat cheia publică a serverului din container și am introdus-o în câmpul `Key / SSH Key`:

```bash
docker exec ssh-agent awk 'NR==1 {printf "%s %s", $1, $2}' /etc/ssh/ssh_host_ed25519_key.pub | pbcopy
```

Am folosit `printf` pentru a copia cheia fără un caracter de rând nou la final. Această cheie a serverului este folosită pentru verificarea identității agentului, iar credențiala `jenkins-agent-ssh` este folosită pentru autentificarea utilizatorului `jenkins`.

După salvare, în logul nodului am verificat mesajele:

```text
SSH host key matched the key required for this connection.
Authentication successful.
Agent successfully connected and online
```

Aceste mesaje mi-au confirmat verificarea cheii serverului, autentificarea și pornirea procesului agentului.

## 4. Crearea și configurarea pipeline-ului

Am creat fișierul [Jenkinsfile](Jenkinsfile) în `lab04`. Am configurat rularea pe agentul cu eticheta `php-agent` și două etape:

| Etapă | Acțiuni |
| --- | --- |
| `Install Dependencies` | Am curățat directorul de lucru al jobului cu `deleteDir()`, am descărcat branch-ul `main` din `composer/semver` și am instalat dependențele cu Composer. |
| `Test` | Am executat `composer test`, comanda de testare definită în `composer.json` al proiectului PHP. |

Am folosit următoarea comandă pentru instalarea dependențelor, inclusiv a celor necesare testării:

```bash
composer install --no-interaction --prefer-dist --no-progress
```

Pentru teste am folosit:

```bash
composer test
```

În proiectul `composer/semver`, această comandă lansează testele prin Symfony PHPUnit Bridge. Am păstrat comanda de testare a proiectului pentru a utiliza configurația sa existentă.

În interfața Jenkins am creat jobul `php-tests-lab04`, de tip `Pipeline`. La `Definition` am ales `Pipeline script` și am introdus conținutul fișierului Jenkinsfile în câmpul `Script`.

Am lansat execuția prin `Build Now` și am verificat rezultatul în `Console Output`. Am obținut:

```text
OK (2303 tests, 7121 assertions)
Pipeline completed.
All stages completed successfully!
Finished: SUCCESS
```

Rezultatul confirmă că cele două etape au fost executate cu succes și că au trecut 2303 de teste, cu 7121 de verificări ale rezultatelor prin assertions.

## 5. Răspunsuri la întrebări

### 5.1. Care sunt avantajele utilizării Jenkins pentru automatizarea sarcinilor DevOps?

Prin această lucrare am observat următoarele avantaje:

- Am executat instalarea dependențelor și testele printr-un singur pipeline, în aceeași ordine la fiecare rulare.
- Am definit pașii în Jenkinsfile, pe care îl pot păstra și urmări în Git.
- Am separat administrarea de execuție: controllerul gestionează jobul, iar agentul rulează comenzile PHP.
- Am urmărit rezultatele și erorile într-un singur loc, în consola build-ului.
- Am folosit pluginuri pentru integrarea cu Git și pentru conectarea prin SSH.

Pot extinde un astfel de pipeline cu etape suplimentare, de exemplu analiză statică, construire sau publicare, în funcție de cerințele proiectului.

### 5.2. Ce alte tipuri de agenți Jenkins există?

În lucrare am folosit un nod permanent, într-un container Docker, conectat prin SSH. Am separat modul de conectare de modul de administrare a resurselor:

| Criteriu | Variante |
| --- | --- |
| Conectarea la controller | Pot folosi SSH, când controllerul inițiază conexiunea, sau un agent inbound, când procesul agentului inițiază conexiunea către controller. |
| Mediul de execuție | Pot folosi mașini fizice, mașini virtuale sau containere, în funcție de uneltele necesare build-ului. |
| Durata de utilizare | Pot configura noduri permanente sau agenți creați dinamic, de exemplu în Docker, Kubernetes ori servicii cloud, folosind pluginurile corespunzătoare. |

Astfel, un agent Docker poate fi permanent, ca în lucrarea mea, sau poate fi creat temporar pentru un anumit build.

### 5.3. Ce probleme am întâlnit și cum le-am rezolvat?

| Problemă întâlnită | Rezolvare aplicată |
| --- | --- |
| Portul `8080` era ocupat de API-ul laboratorului anterior. | Am oprit temporar containerul `php_apache` înainte de folosirea portului pentru Jenkins. |
| `Pipeline` și `Pipeline: Declarative` nu se încărcau deoarece lipsea `workflow-basic-steps`. | Am instalat `Pipeline: Basic Steps` din pluginurile disponibile și am repornit Jenkins Controller. |
| Compose afișa `yaml: line 33: mapping values are not allowed in this context`. | Am verificat fișierul cu `nl -ba docker-compose.yml`. Am identificat două configurații lipite la linia `driver: bridgeservices:` și am rescris fișierul cu o singură configurație validă. |
| Formularul nodului afișa erori pentru directorul de lucru, Host și Credentials. | Am completat `/home/jenkins/agent`, `ssh-agent` și credențiala `jenkins-agent-ssh`, apoi am salvat formularul complet. |
| La salvarea nodului apărea o eroare internă, iar logul indica `Illegal base64 character a`. | Am identificat caracterul de rând nou de la sfârșitul cheii serverului. Am înlocuit copierea cu `print` prin comanda cu `printf`, apoi am lipit cheia pe o singură linie și am salvat nodul. |

## 6. Fișierele proiectului

| Cale | Rol |
| --- | --- |
| `lab04/docker-compose.yml` | Am definit controllerul, agentul, rețeaua și volumele. |
| `lab04/Dockerfile` | Am definit imaginea agentului cu PHP și uneltele necesare testelor. |
| `lab04/Jenkinsfile` | Am definit etapele pipeline-ului și mesajele pentru succes sau eșec. |
| `lab04/readme.md` | Am descris realizarea lucrării, rezultatele și răspunsurile la întrebări. |
| `.env`, în rădăcina `automation` | Am păstrat variabila locală `JENKINS_AGENT_SSH_PUBKEY`. |
| `secrets/`, în rădăcina `automation` | Am păstrat perechea de chei SSH generată local. |
| `.gitignore`, în rădăcina `automation` | Am exclus configurația locală și directorul cu chei din fișierele adăugate în Git. |

În Compose, am păstrat configurația controllerului în volumul `jenkins_home` și directorul de lucru al agentului în `jenkins_agent_volume`.

Pentru oprirea și reluarea acelorași containere pot folosi, din `lab04`:

```bash
docker compose --env-file ../.env stop
docker compose --env-file ../.env start
```

La recrearea containerului agentului, cheia serverului SSH se poate schimba. În acest caz, o copiez din nou cu comanda de la punctul 3.4 și actualizez câmpul de verificare a cheii din configurația nodului.

## 7. Publicarea fișierelor în GitHub

Pentru publicare, verific branch-ul `lab04` și lista fișierelor pregătite pentru commit:

```bash
cd ~/Desktop/automation
git branch --show-current
git status --short
git add lab04 .gitignore
git diff --cached --stat
git commit -m "Add lab04 Jenkins pipeline and report"
git push -u origin lab04
```

Repository-ul pentru predare este [adri-pi12/Automation](https://github.com/adri-pi12/Automation). După publicarea branch-ului, directorul lucrării poate fi accesat la [Automation — lab04](https://github.com/adri-pi12/Automation/tree/lab04/lab04).

## 8. Surse consultate

- [Jenkins — instalarea cu Docker](https://www.jenkins.io/doc/book/installing/docker/)
- [Jenkins — administrarea pluginurilor](https://www.jenkins.io/doc/book/managing/plugins/)
- [Jenkins — utilizarea credențialelor](https://www.jenkins.io/doc/book/using/using-credentials/)
- [Jenkins — utilizarea agenților](https://www.jenkins.io/doc/book/using/using-agents/)
- [Jenkins — arhitectura distribuită](https://www.jenkins.io/doc/book/scaling/architecting-for-scale/)
- [SSH Build Agents — ghid de configurare](https://github.com/jenkinsci/ssh-agents-plugin/blob/main/doc/CONFIGURE.md)
- [Imaginea oficială Jenkins SSH Agent](https://github.com/jenkinsci/docker-ssh-agent)
- [Proiectul PHP composer/semver](https://github.com/composer/semver)
