# HEARTBEAT.md

## Обновление контекста топика

При heartbeat (каждые ~30 мин - 1 час):
1. Если в топике Telegram группы — перечитай свой топик через skill `read-topic`
2. Обнови `memory/voice-context.md` если есть новые interactions

## Мониторинг диска

Проверять раз в несколько дней:
```bash
df -h / | awk 'NR==2 {print $4, $5}'
```
Если свободно **< 450GB** (меньше половины от 935GB) — уведомить Дмитрия:
> "Диск заполнен больше чем наполовину, осталось X GB. Возможно, пора докупить второй SSD."



---

## VPN Recovery (если нет ответов в Telegram)

Если watchdog не помог или gateway завис — выполнить вручную:
1. `nmcli connection down "VPN-Komarovo"`
2. `nmcli connection up "VPN-Komarovo"`
3. Проверить внешний IP: `curl -s https://api.ipify.org` → должен быть финский (149.33.x.x, Helsinki)
4. Проверить доступ: `curl -sf --max-time 10 --head https://api.telegram.org`
