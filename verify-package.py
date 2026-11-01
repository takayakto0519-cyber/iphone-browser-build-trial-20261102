"""Audit unsigned app contents without printing identity, secrets or private configuration."""
import json,plistlib,sys,struct
from pathlib import Path
app=Path(sys.argv[1]); info=plistlib.loads((app/'Info.plist').read_bytes())
if info.get('CFBundlePackageType')!='APPL': raise SystemExit('Not an application')
if not (app/info['CFBundleExecutable']).is_file(): raise SystemExit('Executable missing')
header=(app/info['CFBundleExecutable']).read_bytes()[:8]
if len(header)!=8 or header[:4]!=b'\xcf\xfa\xed\xfe' or struct.unpack('<I',header[4:])[0]!=0x0100000c:
    raise SystemExit('Expected a real arm64 Mach-O executable')
if any(app.rglob('*.xctest')): raise SystemExit('Native device-control runner unexpectedly present')
for p in app.rglob('Info.plist'):
    data=plistlib.loads(p.read_bytes())
    if data.get('NSExtension',{}).get('NSExtensionPointIdentifier')=='com.apple.networkextension.packet-tunnel':
        raise SystemExit('Unexpected VPN extension')
print(json.dumps({'application':True,'arm64MachOExecutable':True,'nativeControlRunner':False,'vpnExtension':False,'signedOrInstallableVerified':False}))
