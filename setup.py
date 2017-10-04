import json
import os
import shutil
import sys
import pkg_resources
from setuptools import Command, find_packages, setup

ROOT_MODULE = 'n4s'


def fpath(name):
    '''
    Return path relative to the directory of setup.py.
    '''
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_build_json():
    '''
    Load the build json from the root directory of this repo.
    It should previously been copied there by "python setup.py prepare_build"
    '''
    fn = fpath('build.json')
    if os.path.exists(fn):
        return load_json(fn)
    else:
        return {'package_name': 'unnamed-package'}


def listdir(d, exclude=['__pycache__']):
    lst = os.listdir(d)
    lst = [os.path.join(d, e) for e in lst if e not in exclude]
    files = [e for e in lst if os.path.isfile(e)]
    dirs = [e for e in lst if os.path.isdir(e)]
    return dirs, files


def copy(src, dst):
    print('Copy "{}" to "{}"'.format(src, dst))
    assert os.path.exists(src), "'{}' not found.".format(src)
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    if os.path.isdir(src):
        shutil.copytree(src, dst)
    elif os.path.isfile(src):
        shutil.copyfile(src, dst)


def get_store_directory():
    storage_folder = os.path.join(fpath(ROOT_MODULE), '_store')
    return storage_folder


def recreate_store_directory():
    storage_folder = get_store_directory()
    # print('Clearing directory {}'.format(storage_folder))
    # shutil.rmtree(storage_folder, ignore_errors=True)
    os.makedirs(storage_folder, exist_ok=True)
    return storage_folder


def all_models_are_in_store():
    build_json = load_build_json()
    storage_folder = get_store_directory()
    for model_name in build_json['models']:
        dst = os.path.join(storage_folder, model_name)
        if not os.path.exists(dst):
            sys.stderr.write('File "{}" missing.\n'.format(dst))
            return False
    return True


def get_version_filename():
    return pkg_resources.resource_filename(ROOT_MODULE, 'version.txt')


def write_version(version):
    fn = get_version_filename()
    print('Writing version {} to {}'.format(version, fn))
    with open(fn, 'w') as f:
        f.write(str(version))


def read_version():
    fn = get_version_filename()
    if os.path.exists(fn):
        with open(fn, 'r') as f:
            return f.read()
    else:
        return '0.0.0-unknown-version'


def is_init_missing(root):
    dirs, files = listdir(root)
    has_init = '__init__.py' in {os.path.basename(file) for file in files}
    has_pyfiles = '.py' in {os.path.splitext(file)[1] for file in files}
    init_missing_in_subpackage = False
    for d in dirs:
        init_missing_in_subpackage = (is_init_missing(d) or
                                      init_missing_in_subpackage)
    init_needed = has_pyfiles or init_missing_in_subpackage
    if init_needed and not has_init:
        sys.stderr.write('__init__.py missing in {}\n'.format(root))
        return True
    if init_missing_in_subpackage:
        return True
    return False


class VerifyPackage(Command):
    description = 'Verify package'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if is_init_missing(fpath(ROOT_MODULE)):
            sys.exit(1)


class PrepareBuild(Command):
    '''
    Copy a project's build.json to
        - the root directory, so it can be used by this script as the reference

    Check if all models are present in the store.
    '''
    description = 'Prepare build'
    user_options = [
        ('build-json=', 'b', 'relative path to build.json'),
    ]

    def initialize_options(self):
        self.build_json = None

    def finalize_options(self):
        pass

    def run(self):
        assert self.build_json is not None, '--build-json not specified'
        # only as info to build script
        #copy(self.build_json, fpath('build.json'))
        # for scripts/start_service.sh
        copy(self.build_json, fpath(os.path.join(ROOT_MODULE, 'build.json')))
        import plumbum
        retcode, stdout, stderr = plumbum.local['git']['describe', '--tags'].run()
        version = stdout.strip()

        write_version(version)

        if not all_models_are_in_store():
            sys.exit(1)


class CopyModels(Command):
    description = ('Recreate the model directory and '
                   'copy models specified in build config')
    user_options = [
        ('build-json=', 'b', 'relative path to build.json'),
    ]

    def initialize_options(self):
        self.build_json = None
        pass

    def finalize_options(self):
        pass

    def run(self):
        assert self.build_json is not None, '--build-json not specified'
        storage_folder = recreate_store_directory()
        models_folder = os.environ['MODELS_FOLDER']
        build_json = load_json(self.build_json)
        for model_name in build_json['models']:
            src = os.path.join(models_folder, model_name)
            dst = os.path.join(storage_folder, model_name)
            copy(src, dst)

PACKAGES = ["numpy==1.13.0",
            "scipy==0.19.0",
            "pandas==0.20.2",
            "matplotlib==2.0.2",
            "seaborn==0.7.1",
            "bokeh==0.12.5",
            "statsmodels==0.8.0",
            "SQLAlchemy==1.1.10",
            "pyaml==16.12.2",
            "voluptuous==0.10.5",
            "plumbum==1.6.3"]

setup(
    name=load_build_json()['package_name'],
    version=read_version(),
    packages=find_packages(),
    # miminal dependencies for production app
    install_requires=PACKAGES,
    cmdclass={
        'verify': VerifyPackage,
        'prepare_build': PrepareBuild,
        'copy_models': CopyModels
    },

    extras_require={
        'dev': ['ipdb==0.10.2',
                'ipython==5.3.0',
                'jupyter==1.0.0',
                'plumbum==1.6.3']
    },

    scripts=[
    ],

    # run `python3 setup.py prepare_build`
    # followed by `python3 setup.py bdist`
    # then you can check the `build` folder to see if your package data is included in
    # the binary distribution (which is used to build the docker image)
    package_data={
        '': [
            '{}'.format('build.json'),
            '{}'.format('version.txt'),
            'config/*',
            'resources/*',
            '{}/*'.format('_store'),
            '{}/**/*'.format('_store')
        ]
    }
)
