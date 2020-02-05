# -*- coding: utf-8 -*-
import os

import subprocess
from solariat_bottle.scripts.data_load.generate_demos import run_scripts
import unittest


class BaseCase(unittest.TestCase):

    def test_script(self):
        project_root = os.path.dirname(__import__('solariat_bottle').__file__)
        script_path = os.path.join(project_root, 'scripts', 'data_load', 'generate_gforce_demo.py')
        script = ['python', script_path, '--password', 'password', '--n_journeys', '2', '--mode=test']
        status = subprocess.call(script)
        self.assertEqual(status, 0)



