#!/bin/sh
NOW=$(date "+%I:%M:%S %p")
# Send Dynamic Notification
curl -s -X POST -H "Content-Type: application/json" -d "{\"value1\":\"AQSS-36-OMEGA: Breach at $NOW\", \"value2\":\"Alpha_Unit\", \"value3\":\"Acoustic_Trigger\"}" https://maker.ifttt.com/trigger/audio_breach/with/key/c1AbqekasvebEmcIeW5cSB

# Log to Local Ledger
python3 -c "import datetime; open('acoustic_ledger.csv', 'a').write(f'{datetime.datetime.now()},Acoustic_Trigger,Alpha_Unit,Success\\n')"
