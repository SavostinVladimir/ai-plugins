"""Compile portable source packages into client-specific files."""
import json
import re
import tomllib
from pathlib import Path
from .configuration import FrameworkError, read_toml

VALID_ID = re.compile(r'^[a-z][a-z0-9-]*$')

def source_file(package, relative):
    path = (package / relative).resolve()
    if not path.is_relative_to(package.resolve()) or not path.is_file():
        raise FrameworkError(f'Invalid package source: {relative}')
    return path.read_text(encoding='utf-8')

def packages(root):
    result = {}
    for path in sorted((root/'frameworks').glob('*/manifest.toml')):
        data = read_toml(path)
        name = data.get('id','')
        if not VALID_ID.fullmatch(name) or name != path.parent.name:
            raise FrameworkError(f'Invalid package id: {name}')
        if name in result:
            raise FrameworkError(f'Duplicate package: {name}')
        result[name] = data
    return result

def render(root, name, cfg, args, saved=None):
    if name not in packages(root):
        raise FrameworkError(f'Unknown framework: {name}')
    manifest = packages(root)[name]
    package = root/'frameworks'/name
    previous = {} if args.reset_overrides else (saved or {}).get('overrides',{})
    overrides = {'roles': {}}
    settings, output = {}, {}
    role_files = sorted((package/'agents').glob('*.toml'))
    if not role_files:
        raise FrameworkError(f'Package {name} has no native agent TOML files')
    for path in role_files:
        text = source_file(package,str(path.relative_to(package)))
        role = tomllib.loads(text)
        agent = role.get('name','')
        if not VALID_ID.fullmatch(agent) or agent != path.stem or agent in settings:
            raise FrameworkError(f'Invalid/duplicate native role name: {agent}')
        local = dict(previous.get('roles',{}).get(agent,{}))
        local.update(cfg['instance'].get('roles',{}).get(agent,{}))
        if args.model: local['model'] = args.model
        if args.effort: local['effort'] = args.effort
        if set(local) - {'model','effort'}:
            raise FrameworkError(f'Unknown role override keys: {agent}')
        selected = {'model':role.get('model')}
        if role.get('model_reasoning_effort'): selected['effort']=role['model_reasoning_effort']
        selected.update(local)
        if not isinstance(selected.get('model'),str) or not selected['model'].strip():
            raise FrameworkError(f'Model is missing for {agent}')
        if selected.get('effort') == 'default': selected.pop('effort')
        if selected.get('effort') and selected['effort'] not in ('none','minimal','low','medium','high','xhigh','max','ultra'):
            raise FrameworkError(f'Unknown effort for {agent}')
        if not isinstance(role.get('developer_instructions'),str) or not role['developer_instructions'].strip():
            raise FrameworkError(f'Instructions are missing for {agent}')
        # Preserve native source byte-for-byte when no local override is needed.
        for key,value in [('model',selected['model']),('model_reasoning_effort',selected.get('effort'))]:
            original=role.get(key)
            if original==value: continue
            pattern=r'(?m)^'+re.escape(key)+r'\s*=.*(?:\n|$)'
            replacement='' if value is None else key+' = '+json.dumps(value,ensure_ascii=False)+'\n'
            if re.search(pattern,text): text=re.sub(pattern,lambda _:replacement,text,count=1)
            elif value is not None: text=replacement+text
        tomllib.loads(text)
        settings[agent]=selected
        overrides['roles'][agent]=local
        output[str(cfg['paths']['agents']/path.name)]=text.encode('utf-8')
    skill_root=package/'skills'/name
    if not (skill_root/'SKILL.md').is_file():
        raise FrameworkError(f'Package requires skills/{name}/SKILL.md')
    for path in sorted(skill_root.rglob('*')):
        if path.is_dir():
            if path.is_symlink(): raise FrameworkError(f'Symlinked source directory: {path}')
            continue
        relative=path.relative_to(package)
        actual=path.resolve()
        if not actual.is_relative_to(package.resolve()):
            raise FrameworkError(f'Invalid package source: {relative}')
        data=path.read_bytes()
        if path.name=='SKILL.md':
            text=data.decode('utf-8').replace('{{agents_path}}',str(cfg['paths']['agents']))
            if re.search(r'\{\{[^}]+\}\}',text): raise FrameworkError('Unresolved skill placeholder')
            data=text.encode('utf-8')
        output[str(cfg['paths']['skills']/name/path.relative_to(skill_root))]=data
    rule=source_file(package,'instructions.md').replace('{{invocation}}','$'+name).strip()
    return dict(files=output,rule=rule,version=manifest['version'],settings=settings,overrides=overrides)
