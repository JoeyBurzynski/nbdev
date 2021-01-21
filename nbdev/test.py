# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/04_test.ipynb (unless otherwise specified).

__all__ = ['get_all_flags', 'get_cell_flags', 'NoExportPreprocessor', 'test_nb', 'nbdev_test_nbs', 'nbdev_read_nbs']

# Cell
from .imports import *
from .sync import *
from .export import *
from .export import _mk_flag_re
from .export2html import _re_notebook2script
from fastcore.script import *

from nbconvert.preprocessors import ExecutePreprocessor
import nbformat

# Cell
class _ReTstFlags():
    "Test flag matching regular expressions"
    def __init__(self, all_flag):
        "match flags applied to all cells?"
        self.all_flag = all_flag

    def _deferred_init(self):
        "Compile at first use but not before since patterns need `Config().tst_flags`"
        if hasattr(self, '_re'): return
        tst_flags = Config().get('tst_flags', '')
        tst_flags += f'|skip' if tst_flags else 'skip'
        _re_all = 'all_' if self.all_flag else ''
        self._re = _mk_flag_re(f"{_re_all}({tst_flags})", 0, "Any line with a test flag")

    def findall(self, source):
        self._deferred_init()
        return self._re.findall(source)

    def search(self, source):
        self._deferred_init()
        return self._re.search(source)

# Cell
_re_all_flag = _ReTstFlags(True)

# Cell
def get_all_flags(cells):
    "Check for all test flags in `cells`"
    result = []
    for cell in cells:
        if cell['cell_type'] == 'code': result.extend(_re_all_flag.findall(cell['source']))
    return set(result)

# Cell
_re_flags = _ReTstFlags(False)

# Cell
def get_cell_flags(cell):
    "Check for any special test flag in `cell`"
    if cell['cell_type'] != 'code' or len(Config().get('tst_flags',''))==0: return []
    return _re_flags.findall(cell['source'])

# Cell
class NoExportPreprocessor(ExecutePreprocessor):
    "An `ExecutePreprocessor` that executes cells that don't have a flag in `flags`"
    def __init__(self, flags, **kwargs):
        self.flags = flags
        super().__init__(**kwargs)

    def preprocess_cell(self, cell, resources, index):
        if 'source' not in cell or cell['cell_type'] != "code": return cell, resources
        for f in get_cell_flags(cell):
            if f not in self.flags: return cell, resources
        if check_re(cell, _re_notebook2script): return cell, resources
        return super().preprocess_cell(cell, resources, index)

# Cell
def test_nb(fn, flags=None):
    "Execute tests in notebook in `fn` with `flags`"
    os.environ["IN_TEST"] = '1'
    if flags is None: flags = []
    try:
        nb = read_nb(fn)
        for f in get_all_flags(nb['cells']):
            if f not in flags: return
        ep = NoExportPreprocessor(flags, timeout=600, kernel_name='python3')
        pnb = nbformat.from_dict(nb)
        ep.preprocess(pnb)
    finally: os.environ.pop("IN_TEST")

# Cell
def _test_one(fname, flags=None, verbose=True):
    print(f"testing {fname}")
    start = time.time()
    try:
        test_nb(fname, flags=flags)
        return True,time.time()-start
    except Exception as e:
        if "ZMQError" in str(e): _test_one(item, flags=flags, verbose=verbose)
        if verbose: print(f'Error in {fname}:\n{e}')
        return False,time.time()-start

# Cell
@call_parse
def nbdev_test_nbs(fname:Param("A notebook name or glob to convert", str)=None,
                   flags:Param("Space separated list of flags", str)=None,
                   n_workers:Param("Number of workers to use", int)=None,
                   verbose:Param("Print errors along the way", bool)=True,
                   timing:Param("Timing each notebook to see the ones are slow", bool)=False,
                   pause:Param("Pause time (in secs) between notebooks to avoid race conditions", float)=0.5):
    "Test in parallel the notebooks matching `fname`, passing along `flags`"
    if flags is not None: flags = flags.split(' ')
    files = nbglob(fname)
    files = [Path(f).absolute() for f in sorted(files)]
    assert len(files) > 0, "No files to test found."
    if n_workers is None: n_workers = 0 if len(files)==1 else min(num_cpus(), 8)
    # make sure we are inside the notebook folder of the project
    os.chdir(Config().path("nbs_path"))
    results = parallel(_test_one, files, flags=flags, verbose=verbose, n_workers=n_workers, pause=pause)
    passed,times = [r[0] for r in results],[r[1] for r in results]
    if all(passed): print("All tests are passing!")
    else:
        msg = "The following notebooks failed:\n"
        raise Exception(msg + '\n'.join([f.name for p,f in zip(passed,files) if not p]))
    if timing:
        for i,t in sorted(enumerate(times), key=lambda o:o[1], reverse=True):
            print(f"Notebook {files[i].name} took {int(t)} seconds")

# Cell
@call_parse
def nbdev_read_nbs(fname:Param("A notebook name or glob to convert", str)=None):
    "Check all notebooks matching `fname` can be opened"
    files = nbglob(fname, recursive=True if fname is None else False)
    for nb in files:
        try: _ = read_nb(nb)
        except Exception as e:
            print(f"{nb} is corrupted and can't be opened.")
            raise e