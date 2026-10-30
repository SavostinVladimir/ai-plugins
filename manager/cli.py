import argparse
import json
from pathlib import Path
from .configuration import FrameworkError, configure
from .render import packages
from .engine import execute

ROOT=Path(__file__).resolve().parents[1]

def parser():
    p=argparse.ArgumentParser(description='Install selected native Codex agent workflows.')
    p.add_argument('command',choices=['list','plan','install','update','status','uninstall','check'])
    p.add_argument('framework',nargs='?')
    p.add_argument('--codex-home',help='Common installation root: agents/, skills/, global instructions, config.toml and manager state')
    p.add_argument('--config',help='Machine-specific TOML file; relative component paths resolve against its directory')
    p.add_argument('--instance',default='default')
    p.add_argument('--installed',action='store_true',help='Select only packages recorded for this instance')
    for component in ('agents','skills','instructions','config','state'):
        p.add_argument('--'+component+'-path',help='Explicit destination override')
    p.add_argument('--model',help='Explicit model override for every role; remembered for this installation')
    p.add_argument('--effort',help='Effort override; use default to omit a native effort field')
    p.add_argument('--reset-overrides',action='store_true',help='Discard remembered overrides, then apply current machine/CLI choices')
    p.add_argument('--adopt',action='store_true',help='Allow replacement of existing unowned payload files, saving originals; never bypasses drift conflicts')
    p.add_argument('--dry-run',action='store_true',help='Plan without creating or changing files')
    p.add_argument('--json',action='store_true')
    return p

def main(argv=None,root=None):
    p=parser(); args=p.parse_args(argv)
    root=Path(root or ROOT)
    try:
        if args.installed and args.command not in ('plan','update','uninstall'):
            raise FrameworkError('--installed is supported for plan, update and uninstall')
        if args.command=='list':
            result={'frameworks':[dict(id=k,version=v['version'],name=v.get('name',k)) for k,v in packages(root).items()]}
            code=0
        else:
            result,code=execute(root,configure(args),args)
        if args.json:
            print(json.dumps(result,indent=2,ensure_ascii=False))
        else:
            print(result.get('message','Agent Frameworks — '+args.command))
            print(json.dumps({k:v for k,v in result.items() if k!='message'},indent=2,ensure_ascii=False))
        return code
    except (FrameworkError,OSError,ValueError,KeyError,TypeError) as exc:
        message={'error':str(exc)}
        print(json.dumps(message,ensure_ascii=False) if args.json else 'Error: '+str(exc))
        return 2
