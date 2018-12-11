'''
    Tool wrapper for git-annex
'''

import logging
import os
import os.path
import subprocess
import shutil
import random
import shlex
import tempfile
import pipes
import time

import tools
import util.file
import util.misc

TOOL_NAME = 'git-annex'
TOOL_VERSION = '7.20181105'

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)


def _noquote(s):
    return '_noquote:' + str(s)

def _quote(s):
    s = str(s)
    if s.startswith('_noquote:'): return s[len('_noquote:'):]
    return pipes.quote(s) if hasattr(pipes, 'quote') else shlex.quote(s)

def _make_cmd(cmd, *args):
    _log.debug('ARGS=%s', args)
    return ' '.join([cmd] + [_quote(str(arg)) for arg in args if arg not in (None, '')])

def _run(cmd, *args):
    cmd = _make_cmd(cmd, *args)
    _log.info('running command: %s cwd=%s', cmd, os.getcwd())
    beg_time = time.time()
    subprocess.check_call(cmd, shell=True)
    _log.info('command succeeded in {}s: {}'.format(time.time()-beg_time, cmd))

class GitAnnexTool(tools.Tool):

    '''Tool wrapper for git-annex'''

    def __init__(self, install_methods=None):
        if install_methods is None:
            install_methods = [tools.CondaPackage(TOOL_NAME, version=TOOL_VERSION, channel='conda-forge',
                                                  executable='git-annex',
                                                  env='vngs-git-annex-env',
                                                  verifycmd='git-annex version')]
        tools.Tool.__init__(self, install_methods=install_methods)

    def version(self):
        return TOOL_VERSION

    def execute(self, args):    # pylint: disable=W0221
        tool_cmd = [self.install_and_get_path()] + list(map(str, args))
        _log.debug(' '.join(tool_cmd))
        subprocess.check_call(tool_cmd)

    def init_repo(self):
        _run('git', 'init')
        self.execute(['init'])

    def add(self, fname):
        self.execute(['add', fname])

    def commit(self, msg):
        _run('git', 'commit', '-m', '"{}"'.format(msg))

    def initremote(self, name, remote_type, **kw):
        remote_attrs = dict(kw)
        if 'encryption' not in remote_attrs: remote_attrs['encryption'] = 'none'
        self.execute(['initremote', name, 'type='+remote_type]+['='.join((k,v)) for k, v in remote_attrs.items()])

    def move(self, fname, to_remote_name):
        self.execute(['move', fname, '--to', to_remote_name])

    def _get_link_into_annex(self, f):
        """Follow symlinks as needed, to find the final symlink pointing into the annex"""
        link_target = None
        while os.path.islink(f):
            link_target = os.readlink(f)
            if '.git/annex/objects/' in link_target:
                break
            if os.path.isabs(link_target):
                f = link_target
            else:
                f = os.path.join(os.path.dirname(f), link_target)
        return f, link_target

    def get(self, f):
        """Ensure the file exists in the local annex.  Unlike git-annex-get, follows symlinks and 
        will get the file regardless of what the current dir is."""

        # TODO: what if f is a dir, or list of dirs?  including symlinks?
        # then, to preserve git-annex-get semantics, need to 

        assert os.path.islink(f)
        f, link_target = self._get_link_into_annex(f)
        if not os.path.isfile(f):
            with util.file.pushd_popd(os.path.dirname(os.path.abspath(f))):
                self.execute(['get', os.path.basename(f)])
        assert os.path.isfile(f)

    def drop(self, f):
        """Drop the file from its repo"""
        assert os.path.islink(f)
        f, link_target = self._get_link_into_annex(f)
        if os.path.isfile(f):
            with util.file.pushd_popd(os.path.dirname(os.path.abspath(f))):
                self.execute(['drop', os.path.basename(f)])
        assert os.path.islink(f)
        assert not os.path.isfile(f)



