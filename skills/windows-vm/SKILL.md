# Windows VM Skill (QEMU/KVM)

## Purpose

Windows 11 VM for SketchUp, GUI applications, and Windows-specific tasks.

## VM Details

| Property | Value |
|----------|-------|
| Name | sketchup |
| Type | QEMU/KVM with UEFI |
| OS | Windows 11 Enterprise Evaluation |
| RAM | 8 GB |
| vCPUs | 4 |
| Disk | /home/dima/vm-setup/sketchup.qcow2 (80GB) |
| UEFI | OVMF (GPT boot required) |
| User | dmitrii |
| Password | dmitrii |
| SketchUp | 2026 (88 days license) |

## Connection Methods

| Method | Port | Status |
|--------|------|--------|
| VNC | localhost:5900 | ✅ Primary |
| RDP | localhost:3389 | ✅ Works |
| SSH | localhost:2222 | ✅ Works |

## Quick Commands

### Start VM
```bash
virsh start sketchup
```

### Stop VM (graceful)
```bash
virsh shutdown sketchup
```

### Force stop
```bash
virsh destroy sketchup
```

### Check status
```bash
virsh list --all
```

### Take screenshot
```bash
virsh screenshot sketchup /tmp/vm_screenshot.png
```

## VNC Access (Primary)

### Connect
```bash
vncviewer localhost:5900
# or
remmina -c vnc://localhost:5900
```

### Via browser (if noVNC installed)
```
http://localhost:6080/vnc.html
```

## RDP Access

### Connect from Linux
```bash
xfreerdp /v:localhost:3389 /u:dmitrii /p:dmitrii /f
# or
remmina -c rdp://localhost:3389
```

### Connect from another machine
```
mstsc /v:<host-ip>:3389
```

## SSH Setup (Required)

SSH is not configured by default. To enable:

### On Windows (PowerShell Admin):
```powershell
# Install OpenSSH Server
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Start and enable
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# Firewall (if needed)
New-NetFirewallRule -Name 'SSH' -DisplayName 'SSH' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

### Test from host
```bash
ssh -p 2222 dmitrii@localhost
```

## VM Configuration

### Current XML location
```
/tmp/sketchup_fixed.xml  # temporary
```

### Key settings
- Machine: q35 with UEFI
- Disk: SATA (not virtio - Windows driver issue)
- Network: User mode with port forwards
- Video: QXL

### Port forwards
- 3389 → 3389 (RDP)
- 2222 → 22 (SSH)

## Troubleshooting

### "No bootable device"
Windows uses GPT → requires UEFI boot, not SeaBIOS.

**Fix:** Use OVMF loader in VM config:
```xml
<os>
  <loader readonly='yes' type='pflash'>/usr/share/OVMF/OVMF_CODE_4M.fd</loader>
  <nvram>/home/dima/vm-setup/sketchup_VARS.fd</nvram>
</os>
```

### PCI slot conflicts
Error: "slot X not available for Y, in use by Z"

**Fix:** Explicitly assign PCI addresses to avoid conflicts:
```xml
<video>
  <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x0'/>
</video>
```

### Network not working
**Fix:** Use -net none and explicit device:
```xml
<qemu:commandline>
  <qemu:arg value='-netdev'/>
  <qemu:arg value='user,id=net0,hostfwd=tcp::3389-:3389,hostfwd=tcp::2222-:22'/>
  <qemu:arg value='-device'/>
  <qemu:arg value='e1000,netdev=net0,addr=0x04'/>
</qemu:commandline>
```

### Black screen on RDP
1. Try VNC first
2. Check Windows is not on lock screen
3. May need to unlock via VNC first

### VM won't start after reboot
Check if libvirtd is running:
```bash
sudo systemctl start libvirtd
virsh start sketchup
```

## Autostart

To start VM on host boot:
```bash
virsh autostart sketchup
```

## Files

| File | Purpose |
|------|---------|
| /home/dima/vm-setup/sketchup.qcow2 | Main disk image |
| /home/dima/vm-setup/sketchup_VARS.fd | UEFI variables |
| /usr/share/OVMF/OVMF_CODE_4M.fd | UEFI firmware |
