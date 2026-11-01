import shutil
from pathlib import Path

from alembic.config import Config

from alembic import command


def test_next_developer_can_generate_a_revision(tmp_path):
    scripts = tmp_path / "alembic"
    source = Path(__file__).resolve().parents[1] / "alembic"
    shutil.copytree(source, scripts)
    config = Config()
    config.set_main_option("script_location", str(scripts))
    revision = command.revision(config, message="handoff probe")
    assert revision is not None
    generated = Path(revision.path).read_text()
    compile(generated, revision.path, "exec")
