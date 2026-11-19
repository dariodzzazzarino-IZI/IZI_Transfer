# Avvio e prove

## Scaricare i programmi
Vai su **Actions > Build IZI Transfer**, apri l'ultima esecuzione riuscita e scarica l'artifact Windows o macOS. Le build sono non firmate e possono richiedere conferma del sistema operativo.

## Modalità Internet (prima prova solo LAN)
- Seleziona Internet.
- Nome: per esempio Prova IZI.
- NAS: indirizzo privato LAN del tuo NAS, porta 5000 (solo rete fidata); preferisci HTTPS con certificato valido.
- Utente: izi-transfer, password: quella impostata su DSM.
- Seleziona un file di prova e avvia.
- Verifica che sul NAS compaia una sottocartella e che venga restituito un link.

Non usare ancora indirizzi pubblici o port forwarding: il caricamento remoto non è configurato.

## Modalità Locale
- Apri l'app su entrambi i computer.
- Sul destinatario seleziona Locale > Avvia ricezione file, scegli la cartella.
- Sul mittente seleziona Locale, inserisci l'IP del destinatario e il codice temporaneo mostrato dal ricevitore.
- Aggiungi i file e premi Avvia trasferimento.
- Consenti la porta TCP 8765 solo nella rete privata se il firewall lo richiede.

La modalità LAN attuale usa HTTP non cifrato e un codice di accesso temporaneo: usala solo su reti locali fidate.

## Limiti della versione iniziale
Non supporta ancora trascinamento, cartelle, ripresa upload, velocità/progresso, link con scadenza, connessione remota automatica e firma dei pacchetti.
