import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch

from manager.cli import main, ROOT, parser
from manager.configuration import configure
from manager import state

class CommonRootTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve()
        self.home=self.base/'sandbox-codex'
        self.catalog=self.base/'catalog'
        shutil.copytree(ROOT/'frameworks',self.catalog/'frameworks')

    def call(self, *args, extra=(), expected=0):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            code=main([*args,'--codex-home',str(self.home),'--json',*extra],root=self.catalog)
        result=json.loads(output.getvalue())
        self.assertEqual(code,expected,result)
        return result

    def test_one_root_plan_and_complete_lifecycle(self):
        result=self.call('plan','spec-review')
        self.assertFalse(self.home.exists())
        for path in result['paths'].values():
            self.assertTrue(Path(path).is_relative_to(self.home),path)
        self.assertEqual(result['paths']['skills'],str(self.home/'skills'))
        self.call('install','spec-review')
        self.assertEqual(len(list((self.home/'agents').glob('*.toml'))),5)
        self.assertTrue((self.home/'skills/spec-review/SKILL.md').is_file())
        self.assertTrue((self.home/'.agent-frameworks/state/default/installed.json').is_file())
        self.call('update','--installed')
        self.call('status')
        self.call('check')
        self.call('uninstall','spec-review')
        self.assertFalse((self.home/'agents/spec-cuj.toml').exists())

    def test_native_config_and_permissions_preserved(self):
        self.home.mkdir()
        config=self.home/'config.toml';config.write_bytes(b'# existing config\r\nmodel="existing"\r\n')
        rules=self.home/'AGENTS.override.md';rules.write_bytes(b'Corporate rules.\n')
        rules.chmod(0o640)
        original_config=config.read_bytes();original_rules=rules.read_bytes()
        self.call('plan','spec-review')
        self.call('install','spec-review')
        self.assertTrue(rules.read_bytes().startswith(original_rules))
        self.assertEqual(stat.S_IMODE(rules.stat().st_mode),0o640)
        self.assertFalse((self.home/'AGENTS.md').exists())
        self.call('update','spec-review')
        self.call('uninstall','spec-review')
        self.assertEqual(config.read_bytes(),original_config)
        self.assertEqual(rules.read_bytes(),original_rules)
        self.assertEqual(stat.S_IMODE(rules.stat().st_mode),0o640)

    def test_foreign_file_conflict_preserves_config_and_rules(self):
        self.home.mkdir()
        config=self.home/'config.toml';config.write_text('model="company"\n')
        rules=self.home/'AGENTS.md';rules.write_text('Keep these rules.\n')
        foreign=self.home/'agents/spec-cuj.toml';foreign.parent.mkdir();foreign.write_text('foreign')
        snapshots={p:p.read_bytes() for p in [config,rules,foreign]}
        self.call('install','spec-review',expected=2)
        for p,content in snapshots.items(): self.assertEqual(p.read_bytes(),content)
        self.assertFalse((self.home/'agents/spec-alignment.toml').exists())
        self.assertFalse((self.home/'skills/spec-review/SKILL.md').exists())

    def test_failure_on_instruction_write_rolls_back_payloads(self):
        self.home.mkdir()
        rules=self.home/'AGENTS.md';rules.write_text('Existing rules\n')
        config=self.home/'config.toml';config.write_text('model="original"\n')
        original_rules=rules.read_bytes();original_config=config.read_bytes()
        actual_write=state.atomic_write
        failed=False
        def fail_once(path,data):
            nonlocal failed
            if Path(path)==rules and not failed:
                failed=True
                raise PermissionError('simulated instruction write failure')
            return actual_write(path,data)
        with patch.object(state,'atomic_write',side_effect=fail_once):
            result=self.call('install','spec-review',expected=2)
        self.assertIn('restored',result['error'])
        self.assertEqual(rules.read_bytes(),original_rules)
        self.assertEqual(config.read_bytes(),original_config)
        self.assertFalse((self.home/'agents/spec-cuj.toml').exists())
        self.assertFalse((self.home/'.agent-frameworks/state/default/installed.json').exists())

    def test_explicit_component_override_and_relative_root(self):
        machine=self.base/'machine.toml'
        machine.write_text('[instances.default.paths]\nskills="custom-skills"\n')
        args=parser().parse_args(['plan','spec-review','--codex-home','relative-root','--config',str(machine)])
        with patch('manager.configuration.Path.cwd',return_value=self.base):
            cfg=configure(args)
        self.assertEqual(cfg['paths']['agents'],self.base/'relative-root/agents')
        self.assertEqual(cfg['paths']['skills'],self.base/'custom-skills')
        args=parser().parse_args(['plan','spec-review','--codex-home',str(self.home),
             '--config',str(machine),'--skills-path',str(self.base/'cli-skills')])
        self.assertEqual(configure(args)['paths']['skills'],self.base/'cli-skills')

    def test_no_flag_defaults_unchanged(self):
        with patch.dict(os.environ,{'CODEX_HOME':str(self.home)}):
            cfg=configure(parser().parse_args(['plan','spec-review']))
        self.assertEqual(cfg['paths']['agents'],self.home/'agents')
        self.assertEqual(cfg['paths']['skills'],Path.home()/'.agents/skills')
        self.assertEqual(cfg['paths']['state'],Path.home()/'.agent-frameworks/state/codex/default')

    def test_invalid_root_protected_path_and_symlink(self):
        self.home.write_text('not a directory')
        self.call('plan','spec-review',expected=2)
        self.home.unlink();self.home.mkdir()
        self.call('install','spec-review',extra=['--instructions-path',str(self.home/'config.toml')],expected=2)
        victim=self.base/'real-config';victim.write_text('untouched')
        (self.home/'AGENTS.md').symlink_to(victim)
        self.call('install','spec-review',expected=2)
        self.assertEqual(victim.read_text(),'untouched')
        self.assertFalse((self.home/'agents').exists())
