# IZI Transfer

Applicazione desktop Windows/macOS per trasferire file in rete locale o tramite Synology NAS.

## Specifiche concordate
- L'utente sceglie **Locale** oppure **Internet**.
- **Locale**: trasferimento diretto fra dispositivi sulla stessa LAN, senza NAS.
- **Internet**: caricamento sul Synology DS214, con selezione automatica della connessione LAN quando disponibile e di un canale remoto sicuro quando fuori rete.
- Ogni invio Internet crea una sottocartella in `IZI-Transfer/<nome trasferimento>/`, senza sovrascrivere cartelle omonime.
- Link Synology per la condivisione esterna; dominio personalizzato rimandato.
- Identità visiva coerente con IZI Select e IZI Retrieve.
- Compatibilità iOS/iPadOS prevista nell'architettura.

## NAS verificato
Synology DS214, DSM 7.1.1-42962 Update 9.
API individuate: `SYNO.API.Auth` v1-7, `SYNO.FileStation.CreateFolder` v1-2, `SYNO.FileStation.Upload` v2-3, `SYNO.FileStation.Sharing` v1-3.
L'utente dedicato ha verificato creazione cartelle, upload e link da File Station. Le chiamate API autenticate e l'upload remoto **non sono ancora stati testati**.

## Sicurezza
Non committare password, token, indirizzi privati, file `.env` o configurazioni con credenziali.
Nessuna porta del DSM va esposta pubblicamente per i test iniziali.
L'accesso remoto va progettato e verificato prima di abilitarlo.

## Stato
Pianificazione iniziale. Nessun client funzionante ancora rilasciato.
