"""Omit an optional upstream widget from OUR newly built unsigned browser package."""
from pathlib import Path
import shutil, sys
app=Path(sys.argv[1]).resolve()
if app.name!='Phone Use Remote.app' or app.parent.name!='Payload': raise SystemExit('Unexpected build output path')
plugins=app/'PlugIns'
if plugins.exists():
    entries=list(plugins.iterdir())
    if any(p.name!='AgentActivityWidget.appex' or p.is_symlink() or not p.is_dir() for p in entries):
        raise SystemExit('Unknown extension; stop without removal')
    for p in entries: shutil.rmtree(p)
    plugins.rmdir()
print('Optional Activity widget omitted; browser package only. No installed app modified.')
