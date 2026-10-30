from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re
from .configuration import FrameworkError, destination_path
from .render import render, VALID_ID
from .state import read_bytes, encode, decode, transaction, locked

def digest(data):
    return hashlib.sha256(data).hexdigest()

def state_path(cfg):
    return cfg['paths']['state']/'installed.json'

def load_state(cfg,raw):
    if raw is None:
        return {'schema':1,'binding':cfg['binding'],'packages':{}}
    try:
        state=json.loads(raw)
        if state['schema']!=1 or state['binding']!=cfg['binding']:
            raise FrameworkError('State binding differs from target/instance/destination paths; use a separate state directory')
        for name,package in state['packages'].items():
            if not VALID_ID.fullmatch(name): raise ValueError('invalid package')
            files={}
            for path,record in package['files'].items():
                p=destination_path(path)
                logical=Path(record.get('destination',path))
                under_skill=logical.is_relative_to(cfg['paths']['skills']/name)
                under_agents=logical.parent==cfg['paths']['agents'] and logical.suffix in ('.toml','.md')
                if not (under_skill or under_agents): raise ValueError('file outside bound destinations')
                if destination_path(logical)!=p: raise ValueError('destination changed since installation')
                if p in {destination_path(cfg['paths'][key]) for key in ('instructions','config')} | {destination_path(state_path(cfg))}:
                    raise ValueError('destination collision with protected file')
                if str(p) in files: raise ValueError('duplicate package destination')
                files[str(p)]=record
            package['files']=files
        return state
    except (ValueError,KeyError,TypeError) as exc:
        raise FrameworkError(f'Invalid state registry {state_path(cfg)}: {exc}') from exc

def markers(name):
    return f'<!-- agent-frameworks:{name}:begin -->',f'<!-- agent-frameworks:{name}:end -->'

def find_block(text,name):
    begin,end=markers(name)
    if text.count(begin)!=text.count(end) or text.count(begin)>1:
        raise FrameworkError(f'Malformed/duplicate instruction block: {name}')
    if begin not in text: return None
    start=text.index(begin); finish=text.index(end,start)+len(end)
    if finish<len(text) and text[finish]=='\n': finish+=1
    return start,finish,text[start:finish]

def build_plan(root,cfg,args,state,original_state):
    selected=sorted(state['packages']) if args.installed else [args.framework] if args.framework else []
    if not selected:
        if args.installed: return dict(changes={},before={},state=state,operations=[],conflicts=[],packages=[])
        raise FrameworkError('Specify a framework or --installed')
    if args.installed and args.framework:
        raise FrameworkError('Choose a framework or --installed, not both')
    new=deepcopy(state)
    changes,before,operations,conflicts={},{},[],[]
    instruction_path=str(destination_path(cfg['paths']['instructions']))
    original_instruction=read_bytes(instruction_path)
    try: instruction_text=(original_instruction or b'').decode('utf-8')
    except UnicodeDecodeError as exc: raise FrameworkError('Instructions must be UTF-8') from exc
    source_instruction=instruction_text
    owners={path:name for name,package in state['packages'].items() for path in package['files']}
    planned_owners={}
    def change(path,data,old):
        if old!=data:
            changes[path]=data; before[path]=old
    for name in selected:
        if not VALID_ID.fullmatch(name): raise FrameworkError(f'Invalid framework ID: {name}')
        previous=state['packages'].get(name)
        if args.command in ('update','uninstall') and previous is None:
            raise FrameworkError(f'Not installed: {name}')
        block=find_block(instruction_text,name)
        if previous and (not block or block[2]!=previous['block']):
            conflicts.append(f'Modified/missing managed instruction block: {name}')
        if not previous and block:
            conflicts.append(f'Untracked instruction block: {name}')
        if args.command=='uninstall':
            for path,record in previous['files'].items():
                current=read_bytes(path)
                if current is None or digest(current)!=record['hash']:
                    conflicts.append(f'Modified/missing managed file: {path}')
                else: change(path,decode(record['original']),current)
            if block:
                start,end,_=block
                spacer=previous.get('spacer','')
                if spacer and instruction_text[:start].endswith(spacer): start-=len(spacer)
                instruction_text=instruction_text[:start]+instruction_text[end:]
            del new['packages'][name]
            operations.append(dict(package=name,action='uninstall',version=previous['version']))
            continue
        built=render(root,name,cfg,args,previous)
        if not previous:
            invocation='$'+name
            if invocation in source_instruction:
                conflicts.append(f'Existing unmarked {name} instruction: reconcile it manually into a managed block; --adopt never rewrites global instructions')
        files={}
        for path,data in built['files'].items():
            if path in (instruction_path,str(destination_path(state_path(cfg))),str(destination_path(cfg['paths']['config']))):
                raise FrameworkError(f'Destination collision: {path}')
            if path in planned_owners and planned_owners[path]!=name:
                raise FrameworkError(f'Duplicate package destination: {path}')
            planned_owners[path]=name
            if path in owners and owners[path]!=name:
                conflicts.append(f'Destination owned by {owners[path]}: {path}')
            current=read_bytes(path)
            record=(previous or {}).get('files',{}).get(path)
            if record:
                if current is None or digest(current)!=record['hash']:
                    conflicts.append(f'Modified/missing managed file: {path}')
                original=record['original']
            else:
                if current is not None and current!=data and not args.adopt:
                    conflicts.append(f'Existing unowned file (use --adopt after review): {path}')
                original=encode(current)
            files[path]={'hash':digest(data),'original':original}
            if built['destinations'][path]!=path:
                files[path]['destination']=built['destinations'][path]
            change(path,data,current)
        # Remove only unchanged old artifacts that no longer belong to this package.
        for path,record in (previous or {}).get('files',{}).items():
            if path in files: continue
            current=read_bytes(path)
            if current is None or digest(current)!=record['hash']:
                conflicts.append(f'Modified retired artifact: {path}')
            else: change(path,decode(record['original']),current)
        begin,end=markers(name)
        desired=begin+'\n'+built['rule']+'\n'+end+'\n'
        spacer=(previous or {}).get('spacer','')
        if block:
            instruction_text=instruction_text[:block[0]]+desired+instruction_text[block[1]:]
        else:
            spacer='\n\n' if instruction_text and not instruction_text.endswith('\n\n') else ''
            instruction_text+=spacer+desired
        new['packages'][name]=dict(version=built['version'],files=files,block=desired,spacer=spacer,
            instructions_existed=(previous or {}).get('instructions_existed',original_instruction is not None),
            settings=built['settings'],overrides=built['overrides'])
        operations.append(dict(package=name,action='update' if previous else 'install',version=built['version'],models=built['settings']))
    if instruction_text!=source_instruction:
        keep_empty = original_instruction is not None
        if args.command=='uninstall' and not instruction_text:
            keep_empty=any(state['packages'][n].get('instructions_existed',True) for n in selected)
        change(instruction_path,instruction_text.encode('utf-8') if instruction_text or keep_empty else None,original_instruction)
    registry=str(destination_path(state_path(cfg)))
    data=(json.dumps(new,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    if new!=state: change(registry,data,original_state)
    return dict(changes=changes,before=before,state=new,operations=operations,conflicts=conflicts,packages=selected)

def report(plan,cfg):
    return dict(target=cfg['target'],instance=cfg['binding']['instance'],paths=cfg['binding']['paths'],
        operations=plan['operations'],changes=[dict(path=p,action='remove' if v is None else 'write') for p,v in plan['changes'].items()],
        conflicts=plan['conflicts'],runtime_verification='NOT VERIFIED: client discovery, model access, tool availability and fresh-context support require a live session. Custom corporate paths must be configured in the harness itself.')

def execute(root,cfg,args):
    if args.command in ('status','check'):
        state=load_state(cfg,read_bytes(state_path(cfg))); rows=[]
        for name,record in state['packages'].items():
            if args.framework and args.framework!=name: continue
            issues=[]
            for path,entry in record['files'].items():
                data=read_bytes(path)
                if data is None or digest(data)!=entry['hash']: issues.append('drift: '+path)
            text=(read_bytes(cfg['paths']['instructions']) or b'').decode('utf-8')
            block=find_block(text,name)
            if not block or block[2]!=record['block']: issues.append('drift: instructions')
            desired=render(root,name,cfg,args,record)
            desired_hashes={p:digest(v) for p,v in desired['files'].items()}
            current_hashes={p:v['hash'] for p,v in record['files'].items()}
            update_available=desired['version']!=record['version'] or desired_hashes!=current_hashes or desired['rule'] not in record['block']
            rows.append(dict(package=name,version=record['version'],update_available=update_available,issues=issues,models=record['settings']))
        if args.framework and not rows: raise FrameworkError(f'Not installed: {args.framework}')
        result=dict(target=cfg['target'],paths=cfg['binding']['paths'],packages=rows,
                    runtime_verification='NOT VERIFIED: filesystem checks only; test discovery, model access and fresh-context delegation in the target client.')
        if args.command=='check' and not rows: raise FrameworkError('No installed packages to check')
        return result,2 if any(row['issues'] for row in rows) else 0
    if args.command=='plan' or args.dry_run:
        original_state=read_bytes(state_path(cfg))
        plan=build_plan(root,cfg,args,load_state(cfg,original_state),original_state)
        return report(plan,cfg),2 if plan['conflicts'] else 0
    with locked(cfg['paths']['state']):
        original_state=read_bytes(state_path(cfg))
        plan=build_plan(root,cfg,args,load_state(cfg,original_state),original_state)
        result=report(plan,cfg)
        if plan['conflicts']: return result,2
        backup=transaction(cfg['paths']['state'],plan['changes'],plan['before'])
        result['completed']=True
        result['backup']=backup
        result['message']='Completed '+args.command+': '+(', '.join(plan['packages']) or 'no installed packages')+f'; {len(plan["changes"])} file changes. Originals restored where applicable on uninstall; unrelated content preserved.'
        return result,0
