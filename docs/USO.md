# IZI Transfer — prima prova

## Installazione
Apri **Actions → Build IZI Transfer** nella repository e scarica l'artifact Windows o macOS di una build riuscita. Le applicazioni non sono firmate.

## Trasferimento locale
1. Apri IZI Transfer su entrambi i computer connessi alla stessa LAN.
2. Sul destinatario seleziona **Locale → Attiva ricezione**, scegli la cartella.
3. Sul mittente seleziona **Locale**: l'app rileva i dispositivi automaticamente e mostra i loro nomi.
4. Scegli il computer destinatario, aggiungi i file e avvia.
5. Inserisci il codice temporaneo mostrato sul destinatario (per sicurezza).

**Non è necessario digitare l'IP.** Se non vedi il dispositivo, verifica firewall e isolamento client Wi-Fi. La scoperta usa broadcast UDP 37654 e il trasferimento TCP 8765. Questa versione è solo per reti LAN fidate, senza cifratura del trasferimento.

## Trasferimento Internet (per ora NAS solo in LAN)
Seleziona Internet, inserisci nome trasferimento e credenziali NAS. L'app crea la sottocartella nel NAS, carica i file e richiede un link di condivisione. Le API reali devono ancora essere collaudate sul DS214.

## Grafica
La versione Qt utilizza il foglio di stile QSS originale di IZI Retrieve: pulsanti, bordi, font e colori. Restano da integrare logo, cornice finestra e rifiniture per corrispondenza completa.

## Non ancora disponibile
Accesso NAS remoto automatico, cartelle annidate, ripresa trasferimenti, crittografia LAN, installer firmati, iOS/iPadOS.
