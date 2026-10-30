import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from manager.cli import main, ROOT
from manager.configuration import configure, FrameworkError
from manager.cli import parser
from manager import state

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.catalog=self.base/'catalog'
        for folder in ('frameworks',):
            shutil.copytree(ROOT/folder,self.catalog/folder)
        self.dest=self.base/'destination'
        self.env=patch.dict(os.environ,{'CODEX_HOME':str(self.base/'codex-home')})
        self.env.start(); self.addCleanup(self.env.stop)
    def flags(self):
        return ['--json',
                '--agents-path',str(self.dest/'agents'), '--skills-path',str(self.dest/'skills'),
                '--instructions-path',str(self.dest/'instructions.md'),
                '--config-path',str(self.dest/'native.conf'), '--state-path',str(self.dest/'state')]

    def run_cli(self,*args,extra=(),expected=0):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            code=main([*args,*self.flags(),*extra],root=self.catalog)
        data=json.loads(out.getvalue())
        self.assertEqual(code,expected,data)
        return data

    def instructions(self):
        return self.dest/'instructions.md'

    def test_plan_has_no_side_effects(self):
        result=self.run_cli('plan','spec-review')
        self.assertFalse(self.dest.exists())
        self.assertEqual(len(result['operations'][0]['models']),5)
        self.assertIn('NOT VERIFIED',result['runtime_verification'])

    def test_code_review_lifecycle_preserves_spec_review(self):
        self.run_cli('install','spec-review')
        spec_role=self.dest/'agents/spec-cuj.toml'
        spec_original=spec_role.read_bytes()
        plan=self.run_cli('plan','code-review')
        self.assertEqual(len(plan['operations'][0]['models']),6)
        self.assertFalse((self.dest/'skills/code-review').exists())
        self.run_cli('install','code-review')
        sources=self.catalog/'frameworks/code-review/agents'
        self.assertEqual(len(list(sources.glob('*.toml'))),6)
        for source in sources.glob('*.toml'):
            self.assertEqual((self.dest/'agents'/source.name).read_bytes(),source.read_bytes())
        installed_skill=(self.dest/'skills/code-review/SKILL.md').read_text()
        self.assertIn(str((self.dest/'agents').resolve()),installed_skill)
        self.assertNotIn('{{agents_path}}',installed_skill)
        self.assertEqual(self.run_cli('install','code-review')['changes'],[])
        self.run_cli('update',extra=['--installed'])
        for package in self.run_cli('check')['packages']:
            self.assertEqual(package['issues'],[])
        self.run_cli('uninstall','code-review')
        self.assertFalse(any((self.dest/'skills/code-review').rglob('*.*')))
        self.assertFalse((self.dest/'agents/code-style.toml').exists())
        self.assertEqual(spec_role.read_bytes(),spec_original)
        self.assertIn('agent-frameworks:spec-review:begin',self.instructions().read_text())
        self.assertNotIn('agent-frameworks:code-review:begin',self.instructions().read_text())

    def test_codex_install_idempotent_check_and_remove(self):
        self.dest.mkdir(); self.instructions().write_text('Existing user rules.\n')
        original=self.instructions().read_bytes()
        result=self.run_cli('install','spec-review')
        self.assertTrue(result['completed'])
        for path in (self.dest/'agents').glob('*.toml'):
            cfg=tomllib.loads(path.read_text())
            self.assertEqual(cfg['model'],'gpt-6-luna')
            self.assertIn('developer_instructions',cfg)
        skill=(self.dest/'skills/spec-review/SKILL.md').read_text()
        self.assertIn('fork_turns="none"',skill)
        self.assertIn(str((self.dest/'agents').resolve()),skill)
        self.assertIn('spec-cuj.toml',skill)
        self.assertNotIn('{{agents_path}}',skill)
        self.assertIn('5 агентов',(self.dest/'skills/spec-review/agents/openai.yaml').read_text())
        self.assertEqual(self.run_cli('install','spec-review')['changes'],[])
        self.assertEqual(self.run_cli('check')['packages'][0]['issues'],[])
        self.run_cli('uninstall','spec-review')
        self.assertEqual(self.instructions().read_bytes(),original)
        self.assertFalse((self.dest/'agents/spec-cuj.toml').exists())

    def test_conflict_is_preflight_and_drift_not_forceable(self):
        role=self.dest/'agents/spec-excess.toml'; role.parent.mkdir(parents=True)
        role.write_text('foreign')
        self.run_cli('install','spec-review',expected=2)
        self.assertFalse((self.dest/'agents/spec-alignment.toml').exists())
        self.assertEqual(role.read_text(),'foreign')
        self.run_cli('install','spec-review',extra=['--adopt'])
        role.write_text('manual edit')
        self.run_cli('update','spec-review',extra=['--adopt'],expected=2)
        self.run_cli('uninstall','spec-review',expected=2)
        self.assertEqual(role.read_text(),'manual edit')

    def test_adoption_restores_originals(self):
        role=self.dest/'agents/spec-excess.toml'; role.parent.mkdir(parents=True)
        role.write_bytes(b'original\x00bytes')
        self.run_cli('install','spec-review',extra=['--adopt'])
        self.run_cli('uninstall','spec-review')
        self.assertEqual(role.read_bytes(),b'original\x00bytes')

    def test_external_instruction_edits_survive(self):
        self.run_cli('install','spec-review')
        self.instructions().write_text(self.instructions().read_text()+'\nAdditional rules\n')
        self.run_cli('update','spec-review')
        self.run_cli('uninstall','spec-review')
        self.assertIn('Additional rules',self.instructions().read_text())

    def test_instruction_drift_blocks_all_changes(self):
        self.run_cli('install','spec-review')
        self.instructions().write_text(self.instructions().read_text().replace('CUJ','CHANGED'))
        # Rule contains Critical User Journeys rather than CUJ; edit its exact body.
        self.instructions().write_text(self.instructions().read_text().replace('OpenSpec','ChangedSpec'))
        result=self.run_cli('check',expected=2)
        self.assertTrue(result['packages'][0]['issues'])
        self.run_cli('update','spec-review',expected=2)

    def test_cli_overrides_persist_but_role_instance_can_override(self):
        self.run_cli('install','spec-review',extra=['--model','custom-small','--effort','medium'])
        self.run_cli('update','spec-review')
        source=tomllib.loads((self.dest/'agents/spec-cuj.toml').read_text())
        self.assertEqual((source['model'],source['model_reasoning_effort']),('custom-small','medium'))
        cfg=self.base/'machine.toml'
        cfg.write_text('[instances.default.roles.spec-cuj]\nmodel="company-small"\n')
        self.run_cli('update','spec-review',extra=['--config',str(cfg)])
        source=tomllib.loads((self.dest/'agents/spec-cuj.toml').read_text())
        self.assertEqual(source['model'],'company-small')

    def test_update_installed_and_changed_sources(self):
        self.run_cli('install','spec-review')
        package=self.catalog/'frameworks/spec-review'
        manifest=package/'manifest.toml'
        manifest.write_text(manifest.read_text().replace('1.0.0','1.1.0'))
        self.assertTrue(self.run_cli('status')['packages'][0]['update_available'])
        self.run_cli('update',extra=['--installed'])
        self.assertEqual(self.run_cli('status')['packages'][0]['version'],'1.1.0')
        # New catalog package is available but must not become installed.
        extra=self.catalog/'frameworks/other'; shutil.copytree(package,extra)
        m=extra/'manifest.toml';m.write_text(m.read_text().replace('id = "spec-review"','id = "other"').replace('spec-','other-'))
        self.run_cli('update',extra=['--installed'])
        self.assertEqual([p['package'] for p in self.run_cli('status')['packages']],['spec-review'])

    def test_multiple_packages_share_instructions(self):
        package=self.catalog/'frameworks/spec-review'
        extra=self.catalog/'frameworks/other';shutil.copytree(package,extra)
        m=extra/'manifest.toml'
        m.write_text(m.read_text().replace('id = "spec-review"','id = "other"').replace('name = "spec-','name = "other-'))
        for agent in list((extra/'agents').glob('*.toml')):
            data=agent.read_text().replace('name = "spec-','name = "other-')
            agent.unlink();(agent.parent/agent.name.replace('spec-','other-')).write_text(data)
        (extra/'skills/spec-review').rename(extra/'skills/other')
        self.run_cli('install','spec-review')
        self.run_cli('install','other')
        self.run_cli('update',extra=['--installed'])
        self.run_cli('uninstall','spec-review')
        self.assertIn('agent-frameworks:other:begin',self.instructions().read_text())
        self.assertTrue((self.dest/'agents/other-cuj.toml').exists())

    def test_binding_collision_and_unknown(self):
        self.run_cli('install','spec-review')
        self.run_cli('update','spec-review',extra=['--skills-path',str(self.base/'elsewhere')],expected=2)
        self.run_cli('install','missing',expected=2)
        self.run_cli('plan','../spec-review',expected=2)
        self.run_cli('plan','spec-review',extra=['--instance','unknown'],expected=2)
        self.run_cli('plan','spec-review',extra=['--instructions-path',str(self.dest/'native.conf')],expected=2)

    def test_lock_and_failed_write_rollback(self):
        with state.locked(self.dest/'state'):
            self.run_cli('install','spec-review',expected=2)
        real=state.atomic_write
        failed=False
        def fail_once(path,data):
            nonlocal failed
            if str(path).endswith('spec-excess.toml') and not failed:
                failed=True
                raise PermissionError('simulated read-only mount')
            return real(path,data)
        with patch.object(state,'atomic_write',side_effect=fail_once):
            result=self.run_cli('install','spec-review',expected=2)
        self.assertIn('restored',result['error'])
        self.assertFalse((self.dest/'agents/spec-alignment.toml').exists())
        self.assertFalse((self.dest/'state/installed.json').exists())
        self.assertTrue(list((self.dest/'state/backups').glob('*.json')))

    def test_relative_paths_precedence_environment_and_override(self):
        machine=self.base/'machine.toml'
        machine.write_text('[instances.corp]\ntarget="codex"\n[instances.corp.paths]\nagents="mount/agents"\nskills="mount/skills"\ninstructions="mount/rules.md"\nstate="mount/state"\n')
        args=parser().parse_args(['plan','spec-review','--config',str(machine),'--instance','corp'])
        cfg=configure(args)
        self.assertEqual(cfg['paths']['agents'],(self.base/'mount/agents').resolve())
        override=Path(os.environ['CODEX_HOME'])/'AGENTS.override.md'
        override.parent.mkdir();override.write_text('corporate')
        defaults=configure(parser().parse_args(['plan','spec-review']))
        self.assertEqual(defaults['paths']['instructions'],override.resolve())
        with self.assertRaises(FrameworkError):
            configure(parser().parse_args(['plan','spec-review','--agents-path','$NO_SUCH_AF_VAR/path']))

    def test_symlink_file_and_source_traversal(self):
        agents=self.dest/'agents';agents.mkdir(parents=True)
        other=self.base/'foreign';other.write_text('unchanged')
        (agents/'spec-cuj.toml').symlink_to(other)
        self.run_cli('install','spec-review',expected=2)
        self.assertEqual(other.read_text(),'unchanged')
        (agents/'spec-cuj.toml').unlink()
        source=self.catalog/'frameworks/spec-review/agents/spec-cuj.toml'
        source.unlink();source.symlink_to(other)
        self.run_cli('plan','spec-review',expected=2)

    def test_native_model_source_change_updates_installation(self):
        source=self.catalog/'frameworks/spec-review/agents/spec-cuj.toml'
        original=source.read_bytes()
        self.run_cli('install','spec-review')
        installed=self.dest/'agents/spec-cuj.toml'
        self.assertEqual(installed.read_bytes(),original)
        source.write_text(source.read_text().replace('gpt-6-luna','custom-native-model'))
        self.assertTrue(self.run_cli('status')['packages'][0]['update_available'])
        self.run_cli('update','spec-review')
        self.assertEqual(installed.read_bytes(),source.read_bytes())
        self.assertEqual(tomllib.loads(installed.read_text())['model'],'custom-native-model')

    def test_legacy_rule_is_not_duplicated(self):
        self.dest.mkdir();self.instructions().write_text('Always use $spec-review before coding.\n')
        self.run_cli('install','spec-review',extra=['--adopt'],expected=2)
        self.assertEqual(self.instructions().read_text(),'Always use $spec-review before coding.\n')

if __name__=='__main__':
    unittest.main()
