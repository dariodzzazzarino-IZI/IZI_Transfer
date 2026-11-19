# Stato della prima implementazione

## Implementato nel codice
- Interfaccia desktop Tkinter con scelta manuale Locale / Internet.
- Trasferimento LAN diretto con ricevitore HTTP temporaneo e codice casuale.
- Client API Synology: login, creazione sottocartella, upload, condivisione.
- Rifiuto di HTTP pubblico; supporto HTTP solo per IP privati LAN e HTTPS.
- Password in memoria, non salvata su disco.

## Da testare su dispositivi reali
- API Synology con il DS214, in particolare payload upload, creazione cartella e formato risposta sharing.
- Avvio Windows e macOS.
- Regole firewall locali e individuazione IP.

## Non ancora implementato
- Connessione remota automatica al NAS.
- Trasferimento cartelle e preservazione gerarchia.
- Ripresa dei trasferimenti, progress bar e grandi file robusti.
- TLS/cifratura end-to-end in LAN (attualmente il codice temporaneo non cifra il traffico).
- Installatori firmati, icona definitiva, app iOS/iPadOS.
- Nome cartella per trasferimento LAN (il nome è usato per NAS).
- Password dei link e scadenza.

Non usare la modalità LAN su reti non fidate. Non esporre la porta 8765 a Internet.
