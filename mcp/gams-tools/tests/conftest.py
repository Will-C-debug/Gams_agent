import os
import shutil
import textwrap
from pathlib import Path

import pytest

from gams_tools.config import load_config

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_text():
    def read(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    return read


def gams_available() -> bool:
    sysdir = os.environ.get("GAMS_SYSDIR")
    if sysdir:
        return (Path(sysdir) / "gams").exists() or (Path(sysdir) / "gams.exe").exists()
    return shutil.which("gams") is not None


requires_gams = pytest.mark.skipif(not gams_available(), reason="needs GAMS (set GAMS_SYSDIR or put gams on PATH)")


DISPATCH_MODEL = textwrap.dedent(
    """\
    $title tiny dispatch
    $if not set peak $set peak 200
    Set t 'periods' / t1*t4 /;
    $include inc/data.inc
    Parameter load(t) 'demand MW' / t1 120, t2 150, t3 %peak%, t4 90 /;
    Positive Variable p(g,t) 'output MW';
    Variable z 'total cost';
    Equation bal(t) 'power balance', lim(g,t) 'capacity', obj 'objective';
    bal(t).. sum(g, p(g,t)) =e= load(t);
    lim(g,t).. p(g,t) =l= cap(g);
    obj.. z =e= sum((g,t), cost(g)*p(g,t));
    Model m / all /;
    m.optFile = 1;
    option lp = cplex;
    solve m using lp minimizing z;
    """
)

DATA_INC = textwrap.dedent(
    """\
    Set g 'units' / g1*g3 /;
    Parameter cap(g) 'capacity MW' / g1 100, g2 80, g3 50 /;
    Parameter cost(g) 'cost $/MWh' / g1 20, g2 30, g3 50 /;
    """
)


@pytest.fixture
def repo(tmp_path: Path):
    """A small GAMS repository with a .gams-agent.yaml."""
    (tmp_path / "models" / "dispatch" / "inc").mkdir(parents=True)
    (tmp_path / "models" / "dispatch" / "main.gms").write_text(DISPATCH_MODEL)
    (tmp_path / "models" / "dispatch" / "inc" / "data.inc").write_text(DATA_INC)
    (tmp_path / "models" / "dispatch" / "cplex.opt").write_text("lpmethod 2\nthreads 1\n")
    (tmp_path / "data" / "prod").mkdir(parents=True)
    (tmp_path / "data" / "prod" / "secret.gdx").write_text("not really gdx")
    sysdir = os.environ.get("GAMS_SYSDIR")
    cfg_text = textwrap.dedent(
        f"""\
        gams:
          version: "{os.environ.get('GAMS_TOOLS_TEST_VERSION', '53')}"
          exec_mode: 2
          {'sysdir: ' + repr(sysdir) if sysdir else ''}
        limits:
          reslim: 60
          threads: 2
          wallclock: 120
        entry_points:
          - path: models/dispatch/main.gms
        test_cases:
          - name: dispatch-base
            entry: models/dispatch/main.gms
            limits: {{ reslim: 30, threads: 8 }}
          - name: dispatch-peak
            entry: models/dispatch/main.gms
            defines: {{ peak: "300" }}
        protected_paths:
          - data/prod/**
        option_files:
          - models/dispatch/cplex.opt
        """
    )
    (tmp_path / ".gams-agent.yaml").write_text(cfg_text)
    return load_config(tmp_path / ".gams-agent.yaml")
