#!/bin/bash
DOMAIN="omsk-chess"
TOKEN="f4390304-56e0-44a0-9462-d6d848fb04f8"
IP=$(curl -s https://ipv4.icanhazip.com)
echo url="https://www.duckdns.org/update?domains=$DOMAIN&token=$TOKEN&ip=$IP" | curl -k -o ~/projects/omsk-chess-broadcast/duckdns/duck.log -K -
echo "Updated at $(date): $IP" >> ~/projects/omsk-chess-broadcast/duckdns/update.log
