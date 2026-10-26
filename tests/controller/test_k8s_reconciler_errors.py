# Copyright (c) Microsoft. All rights reserved.

"""Error handling tests for K8s Job creation."""

from unittest.mock import AsyncMock

import pytest
from omegaconf import OmegaConf

from agentlightning.client import AgentLightningAsyncClient
from agentlightning.controller.k8s_reconciler import K8sReconciler
from agentlightning.schemas import (
    Rollout,
    RolloutConfig,
    RolloutK8sConfig,
    RolloutLifecycleStatus,
    RolloutState,
)


def _reconciler() -> K8sReconciler:
    config = OmegaConf.create(
        {
            "agl_server": {"url": "http://server:8080", "key": ""},
            "k8s_runner": {
                "namespace": "default",
                "ttl_after_finished": 60,
                "max_jobs_per_minute": 100,
                "poll_interval": 5,
            },
        }
    )
    return K8sReconciler(AsyncMock(spec=AgentLightningAsyncClient), config)


def _rollout(job_template: str) -> Rollout:
    return Rollout(
        rollout_id="rollout-1",
        input={},
        config=RolloutConfig(k8s=RolloutK8sConfig(job_template=job_template)),
        status=RolloutLifecycleStatus(created_at=1.0, updated_at=1.0),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "job_template",
    [
        # Jinja syntax error: rendering fails before any Kubernetes request.
        "{% if %}",
        # Structural template error: the parsed document is not a usable Job.
        "apiVersion: batch/v1\nkind: Job\nmetadata: null\nspec: {}",
    ],
    ids=["jinja-syntax-error", "null-metadata"],
)
async def test_create_job_marks_template_errors_failed(
    monkeypatch: pytest.MonkeyPatch,
    job_template: str,
) -> None:
    """Deterministic manifest errors must fail the rollout instead of retrying forever."""
    reconciler = _reconciler()
    patch_status = AsyncMock(return_value=True)
    monkeypatch.setattr(reconciler, "_patch_status", patch_status)

    await reconciler._create_job(_rollout(job_template))

    patch_status.assert_awaited_once()
    status = patch_status.await_args.kwargs
    assert status["state"] == RolloutState.FAILED
    assert status["error_message"].startswith("Invalid Job spec:")
