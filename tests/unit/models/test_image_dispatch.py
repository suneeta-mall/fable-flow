"""EnhancedImageModel dispatch: FLUX 2 vs FLUX 1 vs SDXL paths.

These tests don't actually load the diffusion models — they verify our
dispatch logic and kwargs construction by patching `_load_pipeline` and the
pipeline call.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image


def _build_model(model_name: str):
    """Construct EnhancedImageModel with `_load_pipeline` patched out."""
    from fable_flow.models.image import EnhancedImageModel

    with (
        patch("fable_flow.models.image.config") as mock_cfg,
        patch.object(EnhancedImageModel, "_load_pipeline", return_value=None),
    ):
        mock_cfg.model.image_generation.model = model_name
        m = EnhancedImageModel()
    m.pipeline = MagicMock()
    fake_output = MagicMock()
    fake_output.images = [Image.new("RGB", (32, 32), color="white")]
    m.pipeline.return_value = fake_output
    return m


def _drive_generate(model, *, reference: Image.Image | None = None):
    """Call _generate_sync and return the kwargs the pipeline was invoked with."""
    model._generate_sync("a prompt", 1024, 1024, 42, "negative", reference)
    return model.pipeline.call_args.kwargs


def test_flux2_uses_native_image_param():
    m = _build_model("black-forest-labs/FLUX.2-dev")
    assert m._is_flux2 and not m._is_flux1
    ref = Image.new("RGB", (64, 64), color="red")
    kw = _drive_generate(m, reference=ref)
    assert "image" in kw  # native FLUX 2 conditioning
    assert "ip_adapter_image" not in kw
    assert kw["num_inference_steps"] == 50
    assert kw["guidance_scale"] == 4.0


def test_flux2_klein_also_uses_native_path():
    m = _build_model("black-forest-labs/FLUX.2-klein-9B")
    assert m._is_flux2
    ref = Image.new("RGB", (64, 64), color="red")
    kw = _drive_generate(m, reference=ref)
    assert "image" in kw
    assert "ip_adapter_image" not in kw


def test_flux2_without_ref_skips_image_param():
    m = _build_model("black-forest-labs/FLUX.2-dev")
    kw = _drive_generate(m, reference=None)
    assert "image" not in kw


def test_flux1_legacy_uses_ip_adapter():
    m = _build_model("black-forest-labs/FLUX.1-dev")
    assert m._is_flux1 and not m._is_flux2
    # Pretend IP-Adapter loaded successfully so the ref is wired in.
    m._ip_adapter_loaded = True
    ref = Image.new("RGB", (64, 64), color="red")
    kw = _drive_generate(m, reference=ref)
    assert "ip_adapter_image" in kw
    assert "image" not in kw
    assert kw["num_inference_steps"] == 28
    assert kw["guidance_scale"] == 3.5


def test_sdxl_negative_prompt_passes_through():
    m = _build_model("stabilityai/stable-diffusion-xl-base-1.0")
    assert not m._is_flux1 and not m._is_flux2 and not m._is_sd3
    m._ip_adapter_loaded = True
    kw = _drive_generate(m, reference=Image.new("RGB", (64, 64)))
    assert kw["negative_prompt"] == "negative"
    assert "ip_adapter_image" in kw


def test_flux2_does_not_attempt_ip_adapter():
    """FLUX 2's _ensure_ip_adapter should be a no-op."""
    m = _build_model("black-forest-labs/FLUX.2-dev")
    assert m._ensure_ip_adapter() is False
    # And shouldn't get marked as attempted (no failed download to remember)
    assert m._ip_adapter_attempted is False


@pytest.mark.parametrize(
    "name,expected_flux2,expected_flux1",
    [
        ("black-forest-labs/FLUX.2-dev", True, False),
        ("black-forest-labs/FLUX.2-klein-9B", True, False),
        ("black-forest-labs/Flux2-something", True, False),
        ("black-forest-labs/FLUX.1-dev", False, True),
        ("black-forest-labs/FLUX.1-schnell", False, True),
        ("stabilityai/stable-diffusion-xl-base-1.0", False, False),
        ("stabilityai/stable-diffusion-3.5-large", False, False),
    ],
)
def test_model_family_detection(name, expected_flux2, expected_flux1):
    m = _build_model(name)
    assert m._is_flux2 is expected_flux2
    assert m._is_flux1 is expected_flux1


# ----- GPU placement strategy -----
#
# The OOM we're protecting against: calling pipeline.to("cuda") AND
# enable_*_cpu_offload() in sequence dumps the whole model to GPU first,
# which OOMs on large models like FLUX.2-dev. These tests verify the loader
# picks exactly one path based on `cpu_offload`.


def _build_model_with_offload(model_name: str, cpu_offload: str):
    """EnhancedImageModel with both `_load_pipeline` and config patched."""
    from fable_flow.models.image import EnhancedImageModel

    with (
        patch("fable_flow.models.image.config") as mock_cfg,
        patch.object(EnhancedImageModel, "_load_pipeline", return_value=None),
    ):
        mock_cfg.model.image_generation.model = model_name
        mock_cfg.model.image_generation.cpu_offload = cpu_offload
        m = EnhancedImageModel()
    # Pretend a pipeline is loaded so _place_on_device can drive it.
    m.pipeline = MagicMock()
    m.device = "cuda"
    return m


def test_placement_model_offload_does_not_call_to_device():
    """`cpu_offload="model"` must invoke enable_model_cpu_offload and NOT .to()."""
    m = _build_model_with_offload("black-forest-labs/FLUX.2-dev", "model")
    with patch("fable_flow.models.image.config") as mock_cfg:
        mock_cfg.model.image_generation.cpu_offload = "model"
        m._place_on_device()
    m.pipeline.enable_model_cpu_offload.assert_called_once()
    m.pipeline.enable_sequential_cpu_offload.assert_not_called()
    m.pipeline.to.assert_not_called()


def test_placement_sequential_offload_does_not_call_to_device():
    m = _build_model_with_offload("black-forest-labs/FLUX.2-dev", "sequential")
    with patch("fable_flow.models.image.config") as mock_cfg:
        mock_cfg.model.image_generation.cpu_offload = "sequential"
        m._place_on_device()
    m.pipeline.enable_sequential_cpu_offload.assert_called_once()
    m.pipeline.enable_model_cpu_offload.assert_not_called()
    m.pipeline.to.assert_not_called()


def test_placement_none_calls_to_device_only():
    m = _build_model_with_offload("black-forest-labs/FLUX.2-klein-9b-fp8", "none")
    original_pipe = m.pipeline
    # `.to()` on a Mock returns a fresh Mock by default; route it back to self
    # so we can still inspect `original_pipe.to` after the assignment.
    original_pipe.to.return_value = original_pipe
    with patch("fable_flow.models.image.config") as mock_cfg:
        mock_cfg.model.image_generation.cpu_offload = "none"
        m._place_on_device()
    original_pipe.to.assert_called_once_with("cuda")
    original_pipe.enable_model_cpu_offload.assert_not_called()
    original_pipe.enable_sequential_cpu_offload.assert_not_called()


def test_placement_unknown_value_falls_back_to_model_offload():
    m = _build_model_with_offload("black-forest-labs/FLUX.2-dev", "garbage")
    with patch("fable_flow.models.image.config") as mock_cfg:
        mock_cfg.model.image_generation.cpu_offload = "garbage"
        m._place_on_device()
    m.pipeline.enable_model_cpu_offload.assert_called_once()
    m.pipeline.to.assert_not_called()


def test_placement_on_cpu_is_a_noop():
    """Without CUDA, no placement calls should happen — pipeline already on CPU."""
    m = _build_model_with_offload("black-forest-labs/FLUX.2-dev", "model")
    m.device = "cpu"
    with patch("fable_flow.models.image.config") as mock_cfg:
        mock_cfg.model.image_generation.cpu_offload = "model"
        m._place_on_device()
    m.pipeline.enable_model_cpu_offload.assert_not_called()
    m.pipeline.enable_sequential_cpu_offload.assert_not_called()
    m.pipeline.to.assert_not_called()
