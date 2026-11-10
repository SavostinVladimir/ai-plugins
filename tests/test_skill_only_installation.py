import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from manager.cli import main, ROOT


class SkillOnlyInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base/'codex-home'
        self.catalog = self.base/'catalog'
        self.name = 'code-review-journal'
        self.package = self.catalog/'frameworks'/self.name
        shutil.copytree(ROOT/'frameworks'/self.name, self.package)

    def call(self, *args, expected=0):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([*args, '--codex-home', str(self.home), '--json'], root=self.catalog)
        result = json.loads(output.getvalue())
        self.assertEqual(code, expected, result)
        return result

    def test_list_and_plan_without_roles_have_no_side_effects(self):
        self.assertEqual([row['id'] for row in self.call('list')['frameworks']], [self.name])
        self.assertFalse((self.package/'agents').exists())

        plan = self.call('plan', self.name)
        self.assertEqual(plan['operations'][0]['models'], {})
        self.assertFalse(self.home.exists())

    def test_complete_lifecycle_preserves_foreign_files(self):
        self.home.mkdir()
        config = self.home/'config.toml'
        config.write_bytes(b'# native settings\r\nmodel="existing"\r\n')
        instructions = self.home/'AGENTS.md'
        instructions.write_bytes(b'Existing user rules.\n')
        role = self.home/'agents/foreign.toml'
        role.parent.mkdir()
        role.write_bytes(b'name="foreign"\nmodel="existing"\n')
        originals = {path: path.read_bytes() for path in (config, instructions, role)}

        installed = self.call('install', self.name)
        self.assertEqual(installed['operations'][0]['models'], {})
        skill = self.home/'skills'/self.name/'SKILL.md'
        source = self.package/'skills'/self.name/'SKILL.md'
        self.assertEqual(skill.read_bytes(), source.read_bytes())
        self.assertEqual(self.call('install', self.name)['changes'], [])
        checked = self.call('check')['packages'][0]
        self.assertEqual(checked['issues'], [])
        self.assertEqual(checked['models'], {})
        self.assertFalse(checked['update_available'])
        self.assertIn('agent-frameworks:'+self.name+':begin', instructions.read_text())
        for path in (config, role):
            self.assertEqual(path.read_bytes(), originals[path])

        source.write_text(source.read_text()+'\nДополнение исходного навыка.\n')
        self.assertTrue(self.call('check')['packages'][0]['update_available'])
        self.call('update', '--installed')
        self.assertEqual(skill.read_bytes(), source.read_bytes())
        self.assertEqual(self.call('update', self.name)['changes'], [])
        self.assertEqual(self.call('check')['packages'][0]['issues'], [])
        self.assertEqual(list(role.parent.glob('*.toml')), [role])
        self.assertTrue(instructions.read_bytes().startswith(originals[instructions]))

        self.call('uninstall', self.name)
        self.assertFalse(any((self.home/'skills'/self.name).rglob('*.*')))
        for path, original in originals.items():
            self.assertEqual(path.read_bytes(), original)

    def test_missing_skill_is_still_rejected(self):
        (self.package/'skills'/self.name/'SKILL.md').unlink()

        result = self.call('plan', self.name, expected=2)
        self.assertIn('Package requires skills/'+self.name+'/SKILL.md', result['error'])
        self.assertFalse(self.home.exists())
