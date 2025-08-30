# Requirements Document

## Introduction

Questo documento definisce i requisiti per la ristrutturazione dell'architettura TADA in tre moduli distinti: "tada_admin" (gestione centralizzata dati Chain2Gate), TADA_USER (interfaccia utente per singole company) e mantenimento di alcune funzionalità in "tada_partner". L'obiettivo è risolvere i problemi di sicurezza dei dati multi-company e centralizzare l'accesso a Chain2Gate SDK.

## Requirements

### Requirement 1: Modulo "tada_admin" Centralizzato

**User Story:** Come amministratore di sistema, voglio un modulo centralizzato che gestisca tutti i dati provenienti da Chain2Gate, così da avere un unico punto di controllo e evitare accessi diretti non sicuri.

#### Acceptance Criteria

1. WHEN il sistema viene avviato THEN "tada_admin" SHALL essere l'unica istanza che accede direttamente a Chain2Gate SDK
2. WHEN "tada_admin" riceve dati da Chain2Gate THEN SHALL salvarli nei propri modelli interni
3. WHEN "tada_admin" gestisce i dati THEN SHALL mantenere tutti i record di tutte le company in un'unica istanza
4. IF "tada_admin" non è disponibile THEN nessun modulo TADA_USER SHALL poter accedere ai dati Chain2Gate

### Requirement 2: Sistema di Autorizzazione per Company

**User Story:** Come amministratore TADA, voglio controllare quali funzionalità ogni company può utilizzare, così da gestire centralmente i permessi di accesso.

#### Acceptance Criteria

1. WHEN una company viene configurata THEN "tada_admin" SHALL creare un record di permessi specifico per quella company
2. WHEN TADA_USER richiede una funzionalità THEN "tada_admin" SHALL verificare i permessi della company chiamante
3. IF una company non ha permessi per una funzionalità THEN "tada_admin" SHALL bloccare la richiesta con AccessError
4. WHEN i permessi vengono modificati THEN SHALL essere applicati immediatamente a tutte le richieste successive

### Requirement 3: Filtro Dati per POD Autorizzati

**User Story:** Come utente di una company specifica, voglio vedere solo i dati dei POD che mi appartengono, così da mantenere la separazione dei dati tra company diverse.

#### Acceptance Criteria

1. WHEN TADA_USER richiede dati THEN "tada_admin" SHALL identificare la company chiamante
2. WHEN "tada_admin" elabora la richiesta THEN SHALL filtrare i dati basandosi sull'anagrafica POD della company
3. WHEN vengono restituiti i dati THEN SHALL contenere solo i POD autorizzati per quella company
4. IF una company richiede POD non autorizzati THEN "tada_admin" SHALL escluderli dalla risposta

### Requirement 4: Service Layer per Comunicazione

**User Story:** Come sviluppatore, voglio un'interfaccia pulita tra TADA_USER e "tada_admin", così da mantenere separazione delle responsabilità e facilità di manutenzione.

#### Acceptance Criteria

1. WHEN TADA_USER necessita di dati THEN SHALL utilizzare esclusivamente il service layer di "tada_admin"
2. WHEN il service layer riceve una richiesta THEN SHALL validare autorizzazioni prima di elaborare
3. WHEN il service layer restituisce dati THEN SHALL includere solo informazioni autorizzate
4. IF il service layer rileva errori THEN SHALL restituire messaggi di errore appropriati

### Requirement 5: Gestione Modifiche Bidirezionale

**User Story:** Come utente finale, voglio poter modificare i dati e vedere le modifiche propagate correttamente, così da mantenere la consistenza tra tutti i sistemi.

#### Acceptance Criteria

1. WHEN TADA_USER invia una modifica THEN SHALL passare attraverso "tada_admin" per la validazione
2. WHEN "tada_admin" riceve una modifica THEN SHALL verificare che la company possa modificare quel POD
3. WHEN la modifica è autorizzata THEN "tada_admin" SHALL inviarla a Chain2Gate via API POST
4. WHEN Chain2Gate conferma la modifica THEN "tada_admin" SHALL aggiornare i propri dati locali
5. WHEN i dati locali sono aggiornati THEN SHALL notificare TADA_USER del completamento

### Requirement 6: Cache e Performance

**User Story:** Come utente del sistema, voglio tempi di risposta rapidi per le operazioni comuni, così da avere un'esperienza utente fluida.

#### Acceptance Criteria

1. WHEN "tada_admin" riceve richieste frequenti per gli stessi dati THEN SHALL utilizzare cache locale
2. WHEN i dati in cache sono obsoleti THEN "tada_admin" SHALL aggiornarli da Chain2Gate
3. WHEN vengono effettuate modifiche THEN "tada_admin" SHALL invalidare la cache appropriata
4. WHEN le performance sono critiche THEN i tempi di risposta SHALL essere inferiori a 2 secondi

### Requirement 7: Audit e Tracciabilità

**User Story:** Come amministratore di sistema, voglio tracciare tutte le operazioni sui dati, così da avere visibilità completa sulle attività del sistema.

#### Acceptance Criteria

1. WHEN qualsiasi operazione viene eseguita THEN "tada_admin" SHALL registrare company, utente, azione e timestamp
2. WHEN vengono richiesti dati THEN SHALL essere tracciata la richiesta con i filtri applicati
3. WHEN vengono effettuate modifiche THEN SHALL essere registrato il before/after dei dati
4. WHEN si verificano errori di autorizzazione THEN SHALL essere loggati per analisi di sicurezza

### Requirement 8: Strategia di Migrazione Incrementale

**User Story:** Come amministratore di sistema, voglio una migrazione graduale che parta dall'attuale "tada_partner" per creare "tada_admin", così da minimizzare i rischi e garantire continuità operativa.

#### Acceptance Criteria

1. WHEN inizia la migrazione THEN "tada_partner" SHALL essere utilizzato come base per creare "tada_admin"
2. WHEN "tada_admin" è operativo THEN SHALL mantenere tutte le funzionalità esistenti di "tada_partner"
3. WHEN "tada_admin" è stabile THEN SHALL essere creato il nuovo modulo TADA_USER
4. WHEN TADA_USER è completato THEN le funzionalità utente SHALL essere migrate da "tada_admin" a TADA_USER
5. IF si verificano problemi durante qualsiasi fase THEN SHALL essere possibile il rollback alla fase precedente