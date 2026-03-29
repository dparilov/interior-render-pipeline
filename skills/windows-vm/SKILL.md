# Windows VM Skill

## Purpose

Access and control Windows VM (Surface DP) for Windows-specific tasks, SketchUp, and GUI applications.

## Connection Methods

### Priority Order
1. SSH (preferred for automation)
2. RDP via Tailscale (for GUI)
3. VNC (fallback for black screen issues)

## VM Details

| Property | Value |
|----------|-------|
| Hostname | surfacedp |
| Tailscale IP | 100.82.18.44 |
| User | dima |
| OS | Windows |

## SSH Access

### Connect
```bash
ssh dima@surfacedp
# or
ssh dima@100.82.18.44
```

### Ensure SSH persists after reboot
On Windows (PowerShell as Admin):
```powershell
# Check OpenSSH Server installed
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH*'

# Install if needed
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Start and enable service
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# Firewall rule
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

### Test SSH
```bash
ssh -o ConnectTimeout=10 dima@100.82.18.44 "hostname && whoami"
```

## RDP Access

### From your machine (mstsc)
```
Computer: surfacedp
# or
Computer: 100.82.18.44
Username: dima
```

### Ensure RDP enabled
On Windows:
1. Settings → System → Remote Desktop → Enable
2. Or PowerShell: `Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name "fDenyTSConnections" -Value 0`

### Firewall for RDP
```powershell
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
```

## VNC Fallback

### When to use
- RDP shows black screen
- Need headless session
- Multiple simultaneous viewers

### VNC Server Setup (if not installed)
1. Download TightVNC: https://tightvnc.com/download.php
2. Install with "TightVNC Server" selected
3. Set password during install
4. Default port: 5900

### Connect via VNC
```bash
# Linux
vncviewer 100.82.18.44:5900

# Or use Remmina
remmina -c vnc://100.82.18.44
```

## Browser Control

### Via OpenClaw
```
browser action=open target=node node=surfacedp url=https://example.com
browser action=snapshot target=node node=surfacedp
```

### Requirements
- Chrome/Edge installed on Windows
- Debugging port enabled

## Health Check

### Quick connectivity test
```bash
# Ping
ping -c 3 100.82.18.44

# SSH
ssh -o ConnectTimeout=5 dima@100.82.18.44 "echo OK"

# RDP port
nc -zv 100.82.18.44 3389 -w 5

# VNC port
nc -zv 100.82.18.44 5900 -w 5
```

## Troubleshooting

### SSH connection refused
1. Check OpenSSH Server running: `Get-Service sshd`
2. Check firewall: `Get-NetFirewallRule -Name *ssh*`
3. Restart service: `Restart-Service sshd`

### RDP black screen
1. Try VNC instead
2. Or: disconnect all sessions, wait 30s, reconnect
3. Or: `query session` on Windows to see active sessions

### VM not responding to Tailscale
1. Check Tailscale running on Windows
2. `tailscale status` should show surfacedp
3. May need to restart Tailscale service on Windows

### Firewall blocking everything
Temporary disable for testing:
```powershell
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
# Re-enable after:
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

## Common Tasks

### Run PowerShell command
```bash
ssh dima@surfacedp "powershell -Command 'Get-Process | Select-Object -First 5'"
```

### Copy file to Windows
```bash
scp file.txt dima@surfacedp:C:/Users/dima/Desktop/
```

### Copy file from Windows
```bash
scp dima@surfacedp:C:/Users/dima/file.txt ./
```
