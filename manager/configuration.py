"""Resolve machine-specific settings without modifying native client config."""
from pathlib import Path
import os
import re
import tomllib


class FrameworkError(Exception):
    pass

def destination_path(path):
    """Resolve destination directories while retaining final-file symlink checks."""
    path = Path(path)
    return path.parent.resolve() / path.name

def read_toml(path):
    try:
        return tomllib.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise FrameworkError(f'Cannot read TOML {path}: {exc}') from exc

def resolve_path(value, base):
    if not isinstance(value, str) or not value.strip():
        raise FrameworkError('Paths must be nonempty strings')
    expanded = os.path.expanduser(os.path.expandvars(value))
    if re.search(r'\$[A-Za-z_{]|%[A-Za-z_][A-Za-z_0-9]*%', expanded):
        raise FrameworkError(f'Unresolved environment variable in path: {value}')
    path = Path(expanded)
    if not path.is_absolute():
        path = base / path
    # Resolve parents, but preserve the final component for symlink checks.
    return destination_path(path)

def configure(args):
    home = Path.home()
    machine = read_toml(args.config) if args.config else {}
    instances = machine.get('instances', {})
    if args.instance not in instances and (args.instance != 'default' or args.config):
        raise FrameworkError(f'Unknown instance: {args.instance}')
    instance = instances.get(args.instance, {})
    target = 'codex'  # Kept in registry bindings for existing Codex installations.
    if instance.get('target','codex') != 'codex':
        raise FrameworkError('Only Codex instances are supported')
    if instance.get('profiles'):
        raise FrameworkError('Model profiles were removed. Set models in agents/*.toml or instance.roles overrides.')
    config_base = Path(args.config).expanduser().resolve().parent if args.config else Path.cwd()
    common = getattr(args, 'codex_home', None)
    codex_home = resolve_path(common if common is not None else os.environ.get('CODEX_HOME', str(home / '.codex')), Path.cwd())
    if codex_home.is_symlink():
        codex_home = codex_home.resolve()
    if codex_home.exists() and not codex_home.is_dir():
        raise FrameworkError(f'Codex home must be a directory: {codex_home}')
    override = codex_home / 'AGENTS.override.md'
    defaults = dict(agents=codex_home/'agents',
                    skills=codex_home/'skills' if common is not None else home/'.agents/skills',
                    instructions=override if override.exists() else codex_home/'AGENTS.md',
                    config=codex_home/'config.toml')
    defaults['state'] = (codex_home/'.agent-frameworks/state'/args.instance if common is not None
                         else home/'.agent-frameworks/state'/target/args.instance)
    configured = instance.get('paths', {})
    unknown = set(configured) - set(defaults)
    if unknown:
        raise FrameworkError(f'Unknown path keys: {sorted(unknown)}')
    paths = {}
    for key, default in defaults.items():
        explicit = getattr(args, key + '_path', None)
        paths[key] = resolve_path(explicit, Path.cwd()) if explicit else resolve_path(str(configured.get(key,default)), config_base)
    for key in ('agents','skills','state'):
        if paths[key].is_symlink():
            paths[key] = paths[key].resolve()
        if paths[key].exists() and not paths[key].is_dir():
            raise FrameworkError(f'{key} must be a directory: {paths[key]}')
    for key in ('instructions','config'):
        if paths[key].is_symlink():
            raise FrameworkError(f'Refusing final-file symlink: {paths[key]}')
        if paths[key].exists() and not paths[key].is_file():
            raise FrameworkError(f'{key} must be a file: {paths[key]}')
    if paths['config'].is_relative_to(paths['state']) or paths['instructions'].is_relative_to(paths['state']):
        raise FrameworkError('Native config/instructions must not overlap the manager state directory')
    if paths['instructions'] == paths['config']:
        raise FrameworkError('Instructions collide with native config or registry')
    binding = dict(target=target, instance=args.instance, paths={k:str(v) for k,v in paths.items()})
    return dict(target=target, paths=paths, binding=binding, instance=instance)
