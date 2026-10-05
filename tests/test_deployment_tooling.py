import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.gcp import control


def deployment(tmp_path: Path, execute: bool = False):
    with patch.object(control, "ROOT", tmp_path):
        return control.Deployment(argparse.Namespace(project_id="test-project", region="us-central1", environment="production", execute=execute))


def test_mutation_requires_execute_and_deletion_is_never_auto_applied(tmp_path: Path) -> None:
    item = deployment(tmp_path)
    item.plan = MagicMock()
    item.tf = MagicMock()
    with pytest.raises(RuntimeError, match="authorization"):
        item.apply()
    item.tf.assert_not_called()
    item.args.execute = True
    item.tf.return_value = json.dumps({"resource_changes":[{"change":{"actions":["delete","create"]}}]})
    with pytest.raises(RuntimeError, match="deletion"):
        item.apply()
    assert item.tf.call_count == 1


def test_bootstrap_preserves_existing_runtimes(tmp_path: Path) -> None:
    item = deployment(tmp_path, execute=True)
    item.output = MagicMock(return_value={"api_url":"https://api.run.app"})
    item.apply = MagicMock()
    with pytest.raises(RuntimeError, match="already exist"):
        item.bootstrap()
    item.apply.assert_not_called()


def test_invalid_project_cannot_reach_subprocess(tmp_path: Path) -> None:
    with patch.object(control, "ROOT", tmp_path), pytest.raises(ValueError):
        control.Deployment(argparse.Namespace(project_id="x; rm -rf", region="us-central1", environment="production"))
