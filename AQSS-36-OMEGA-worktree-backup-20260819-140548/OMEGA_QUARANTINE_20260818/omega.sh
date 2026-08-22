#!/bin/bash
while true; do
echo "--- AQSS-36-OMEGA LIVE MONITOR ---"
echo -n "Enter dB: "; read db; echo -n "Enter ms: "; read delay; echo -n "Enter Conf %: "; read conf
if [ "$delay" -gt 150 ]; then HAPTIC="DROPPED (Stale)";
elif [ "$conf" -lt 90 ]; then HAPTIC="STONE (Safety Override)";
elif [ "$db" -gt 85 ]; then HAPTIC="STONE";
elif [ "$db" -gt 65 ]; then HAPTIC="BAMBOO";
else HAPTIC="SILK"; fi
echo ">> RESULT: $HAPTIC"; echo "--------------------------------"; done
